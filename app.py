"""Streamlit client for MovieLens graph recommendations."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src import __version__
from src.config import Settings
from src.cypher_io import load_query
from src.db import Database
from src.graph_view import (
    LEGEND,
    cf_elements,
    content_elements,
    narrate_cf,
    narrate_content,
    render_html,
)
from src.recommend import (
    RecommendParams,
    cf_paths,
    content_hybrid,
    content_paths,
    explain_query,
    graph_counts,
    user_based,
    user_profile,
)


@st.cache_resource
def get_database() -> Database:
    settings = Settings.from_env()
    database = Database(settings)
    database.verify()
    return database


def _join_genres(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    if value is None:
        return ""
    return str(value)


def _scale_label(counts: dict[str, int]) -> str:
    if counts["movies"] >= 50000:
        return "Large graph loaded. Traversal bounds keep the queries interactive."
    if counts["movies"] == 0:
        return "The graph is empty."
    return "Small or sample graph loaded."


def _controls() -> dict[str, Any]:
    st.sidebar.header("Target")
    user_id = st.sidebar.number_input("userId", min_value=1, step=1, value=1)
    st.sidebar.header("Traversal bounds")
    st.sidebar.caption("These caps keep both strategies responsive on MovieLens 32M.")
    min_rating = st.sidebar.slider("Minimum rating for liked and recommended movies", 0.5, 5.0, 4.0, 0.5)
    peer_min = st.sidebar.slider(
        "Similar users must score a shared movie higher than",
        0.5,
        5.0,
        4.0,
        0.5,
        help="Strategy A keeps a neighbor only when their rating on a shared movie is above this value.",
    )
    seed_limit = st.sidebar.slider("Liked movies used as seeds", 5, 40, 15)
    neighbor_limit = st.sidebar.slider("Similar users kept", 5, 50, 25)
    min_shared = st.sidebar.slider("Minimum shared movies", 1, 20, 3)
    top_genres = st.sidebar.slider("Top genres from the user", 1, 8, 5)
    min_overlap = st.sidebar.slider("Minimum shared genres", 1, 5, 1)
    candidate_limit = st.sidebar.slider("Content candidates before tag scoring", 20, 150, 80)
    tag_boost = st.sidebar.slider("Tag boost", 0.0, 5.0, 2.0, 0.5)
    limit = st.sidebar.slider("Recommendations to show", 5, 20, 10)
    run = st.sidebar.button("Run recommendations", type="primary", width="stretch")
    return {
        "user_id": int(user_id),
        "run": run,
        "params": RecommendParams(
            min_rating=float(min_rating),
            peer_min_rating=float(peer_min),
            seed_limit=int(seed_limit),
            neighbor_limit=int(neighbor_limit),
            min_shared=int(min_shared),
            top_genres=int(top_genres),
            min_genre_overlap=int(min_overlap),
            candidate_limit=int(candidate_limit),
            tag_boost=float(tag_boost),
            limit=int(limit),
        ),
    }


def _signature(user_id: int, params: RecommendParams) -> dict[str, Any]:
    return {"user_id": user_id, **params.__dict__}


def _run_strategy(label: str, func, explain_file: str, parameters: dict[str, Any], db: Database):
    started = time.perf_counter()
    try:
        rows = func()
        plan = explain_query(db, explain_file, parameters)
        error = None
    except Exception as exc:
        rows = []
        plan = None
        error = str(exc)
    return {
        "label": label,
        "rows": rows,
        "plan": plan,
        "error": error,
        "elapsed": time.perf_counter() - started,
        "query": load_query(explain_file),
        "parameters": parameters,
    }


def build_report(db: Database, user_id: int, params: RecommendParams) -> dict[str, Any]:
    params.validate()
    profile = user_profile(db, user_id, params.min_rating)
    cf = _run_strategy(
        "Strategy A",
        lambda: user_based(db, user_id, params),
        "user_based_cf.cypher",
        params.cf_parameters(user_id),
        db,
    )
    content = _run_strategy(
        "Strategy B",
        lambda: content_hybrid(db, user_id, params),
        "content_hybrid.cypher",
        params.content_parameters(user_id),
        db,
    )
    return {
        "profile": profile,
        "cf": cf,
        "content": content,
        "signature": _signature(user_id, params),
        "params": params,
    }


def _table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=[label for _key, label in columns])
    if "genres" in frame.columns:
        frame["genres"] = frame["genres"].map(_join_genres)
    renamed = frame.rename(columns={key: label for key, label in columns})
    ordered = [label for _key, label in columns if label in renamed.columns]
    return renamed[ordered]


def _legend() -> None:
    chips = " &nbsp; ".join(
        f"<span style='color:{color}'>&#9679;</span> {label}" for color, label in LEGEND
    )
    st.markdown(chips, unsafe_allow_html=True)


def _show_graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    _legend()
    if not nodes:
        st.caption("No path rows to draw.")
        return
    try:
        html = render_html(nodes, edges)
    except Exception as exc:
        st.warning(f"Topology view could not be drawn ({exc}). The hop table below is still the path.")
        return
    if html:
        components.html(html, height=580, scrolling=True)


def _plan_block(plan: dict[str, Any] | None, query: str) -> None:
    if plan is None:
        return
    if plan["index_seek"] and not plan["all_nodes_scan"]:
        st.success("Plan uses a property index seek and does not scan every node.")
    elif plan["all_nodes_scan"]:
        st.error("Plan contains AllNodesScan. The anchor is not using the uniqueness index.")
    else:
        st.warning("Plan did not report an index seek.")
    st.code(plan["text"], language="text")
    with st.expander("Cypher"):
        st.code(query, language="cypher")


def _show_profile(db: Database, state_key: str, filename: str, parameters: dict[str, Any], label: str) -> None:
    token = (filename, tuple(sorted(parameters.items())))
    if st.button(f"Run PROFILE for {label}", key=f"button-{state_key}"):
        with st.spinner("Profiling executes the traversal and records dbHits."):
            st.session_state[state_key] = {
                "token": token,
                "plan": explain_query(db, filename, parameters, mode="PROFILE"),
            }
    saved = st.session_state.get(state_key)
    if saved and saved.get("token") == token:
        st.write(f"Total dbHits: {saved['plan']['db_hits']}")
        st.code(saved["plan"]["text"], language="text")


def _render_cf(db: Database, report: dict[str, Any]) -> None:
    result = report["cf"]
    st.caption(
        "Path: (Target User)-[:RATED]->(Shared Movie)<-[:RATED]-(Similar User)-[:RATED]->(Recommendation)"
    )
    st.caption(f"Query time {result['elapsed']:.2f}s")
    if result["error"]:
        st.error(result["error"])
        return
    rows = result["rows"]
    if not rows:
        st.info("No collaborative recommendations. Lower the shared-movie minimum or the rating floor.")
    else:
        top = rows[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Top match score", top["matchScore"])
        c2.metric("Similar users", top["similarityCount"])
        c3.metric("Predicted rating", top["avgRating"])
        st.dataframe(
            _table(
                rows,
                [
                    ("title", "Title"),
                    ("matchScore", "Match score"),
                    ("similarityCount", "Similar users"),
                    ("avgRating", "Predicted rating"),
                    ("genres", "Genres"),
                ],
            ),
            width="stretch",
            hide_index=True,
        )
        labels = {int(row["movieId"]): f"{row['title']} ({row['movieId']})" for row in rows}
        movie_id = st.selectbox("Inspect a collaborative recommendation", list(labels), format_func=labels.get)
        user_id = report["signature"]["user_id"]
        paths = cf_paths(db, user_id, int(movie_id), report["params"])
        st.write(narrate_cf(paths, user_id))
        _show_graph(*cf_elements(paths))
        if paths:
            st.dataframe(
                _table(
                    paths,
                    [
                        ("peerId", "Similar user"),
                        ("sharedTitle", "Shared movie"),
                        ("myRating", "Your rating"),
                        ("peerSharedRating", "Their rating on shared movie"),
                        ("recRating", "Their rating on recommendation"),
                    ],
                ),
                width="stretch",
                hide_index=True,
            )
    with st.expander("Query plan"):
        _plan_block(result["plan"], result["query"])
        _show_profile(db, "profile-cf", "user_based_cf.cypher", result["parameters"], "Strategy A")


def _render_content(db: Database, report: dict[str, Any]) -> None:
    result = report["content"]
    st.caption(
        "Path: (Target User)-[:RATED]->(Liked Movie)-[:IN_GENRE]->(Genre)<-[:IN_GENRE]-(Recommendation), "
        "plus Tag nodes linked by HAS_TAG."
    )
    st.caption(
        "Match score = 5 x shared genres + how often the user rated those genres highly "
        "+ tag boost x shared tags."
    )
    st.caption(f"Query time {result['elapsed']:.2f}s")
    if result["error"]:
        st.error(result["error"])
        return
    rows = result["rows"]
    if not rows:
        st.info("No content recommendations. Lower the rating floor or the shared-genre minimum.")
    else:
        top = rows[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Top match score", top["matchScore"])
        c2.metric("Genre overlap", top["genreOverlap"])
        c3.metric("Tag overlap", top["tagOverlap"])
        st.dataframe(
            _table(
                rows,
                [
                    ("title", "Title"),
                    ("matchScore", "Match score"),
                    ("genreOverlap", "Genre overlap"),
                    ("tagOverlap", "Tag overlap"),
                    ("genres", "Shared genres"),
                ],
            ),
            width="stretch",
            hide_index=True,
        )
        labels = {int(row["movieId"]): f"{row['title']} ({row['movieId']})" for row in rows}
        movie_id = st.selectbox("Inspect a content recommendation", list(labels), format_func=labels.get)
        user_id = report["signature"]["user_id"]
        paths = content_paths(db, user_id, int(movie_id), report["params"])
        st.write(narrate_content(paths, user_id))
        _show_graph(*content_elements(paths))
        if paths:
            st.dataframe(
                _table(
                    paths,
                    [
                        ("likedTitle", "Liked movie"),
                        ("myRating", "Your rating"),
                        ("genre", "Shared genre"),
                        ("tag", "Shared tag"),
                    ],
                ),
                width="stretch",
                hide_index=True,
            )
    with st.expander("Query plan"):
        _plan_block(result["plan"], result["query"])
        _show_profile(
            db, "profile-content", "content_hybrid.cypher", result["parameters"], "Strategy B"
        )


def _render_report(db: Database, report: dict[str, Any]) -> None:
    profile = report["profile"]
    if profile is None:
        st.warning("No User node with that userId. Load the dataset or choose another id.")
        return
    genres = ", ".join(profile["topGenres"]) if profile["topGenres"] else "none at the current rating floor"
    c1, c2, c3 = st.columns(3)
    c1.metric("Ratings", profile["ratingCount"])
    c2.metric("Average rating", profile["avgRating"] if profile["avgRating"] is not None else "n/a")
    c3.metric("Strong genres", len(profile["topGenres"]))
    st.caption(f"Top genres at this rating floor: {genres}")
    if profile["ratingCount"] == 0:
        st.info("This user has no RATED edges yet.")
    tab_a, tab_b = st.tabs(["Strategy A: similar users", "Strategy B: genres and tags"])
    with tab_a:
        _render_cf(db, report)
    with tab_b:
        _render_content(db, report)


def main() -> None:
    st.set_page_config(
        page_title="MovieLens Graph Recommendations",
        page_icon="🎬",
        layout="wide",
    )
    st.title("Graph Analytics and Collaborative Recommendation Engine")
    st.caption(
        f"MovieLens on Neo4j {__version__}. Recommendations come from graph traversals, "
        "not multi-table joins."
    )

    settings = Settings.from_env()
    st.sidebar.caption(f"{settings.uri}  |  {settings.database}")
    if st.sidebar.button("Reconnect"):
        get_database.clear()
        st.rerun()

    try:
        db = get_database()
    except Exception as exc:
        st.error(f"Cannot reach Neo4j at {settings.uri}.")
        st.write(str(exc))
        st.code("docker compose up -d\ncopy .env.example .env", language="powershell")
        st.stop()

    try:
        counts = graph_counts(db)
    except Exception as exc:
        st.error(f"Connected, but the count queries failed: {exc}")
        st.stop()

    metric_cols = st.columns(4)
    metric_cols[0].metric("Users", f"{counts['users']:,}")
    metric_cols[1].metric("Movies", f"{counts['movies']:,}")
    metric_cols[2].metric("Ratings", f"{counts['rated']:,}")
    metric_cols[3].metric("Tags", f"{counts['tagged']:,}")
    st.caption(
        f"Genres {counts['genres']:,} · IN_GENRE {counts['in_genre']:,} · "
        f"Tag nodes {counts['tags']:,} · HAS_TAG {counts['has_tag']:,}. {_scale_label(counts)}"
    )

    if counts["movies"] == 0:
        st.info("Load a graph before requesting recommendations.")
        st.code(
            "python -m src.sample_data --out data/sample\n"
            "python -m src.ingest --data-dir data/sample\n\n"
            "python -m src.download_dataset\n"
            "python -m src.ingest --data-dir data/ml-32m",
            language="powershell",
        )

    with st.expander("Graph model"):
        st.markdown(
            """
            `(:User)-[:RATED {rating, timestamp}]->(:Movie)-[:IN_GENRE]->(:Genre)`

            `(:User)-[:TAGGED {tag, timestamp}]->(:Movie)-[:HAS_TAG]->(:Tag)`

            User and Movie lookups use uniqueness constraints on `userId` and `movieId`.
            `HAS_TAG` is the node projection of a tag so Strategy B can enter Tag nodes;
            the original tag string stays on `TAGGED`.
            """
        )

    controls = _controls()
    if controls["run"]:
        with st.spinner("Running both traversals..."):
            try:
                st.session_state["report"] = build_report(db, controls["user_id"], controls["params"])
            except Exception as exc:
                st.error(str(exc))

    report = st.session_state.get("report")
    if not report:
        st.write("Choose a userId and run the traversals. The sample graph uses user 1.")
        return

    current = _signature(controls["user_id"], controls["params"])
    if current != report["signature"]:
        st.info("Parameters changed. Run recommendations to refresh.")
    stored_user = report["signature"]["user_id"]
    st.subheader(f"Results for user {stored_user}")
    _render_report(db, report)


if __name__ == "__main__":
    main()
