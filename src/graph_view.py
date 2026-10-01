"""Recommendation path narrative and topology drawing."""

from __future__ import annotations

from typing import Any

USER = "#60a5fa"
PEER = "#2dd4bf"
MOVIE = "#fb923c"
REC = "#f87171"
GENRE = "#4ade80"
TAG = "#e879f9"

LEGEND = (
    (USER, "Target user"),
    (PEER, "Similar user"),
    (MOVIE, "Watched movie"),
    (REC, "Recommendation"),
    (GENRE, "Genre"),
    (TAG, "Tag"),
)


def clip(text: Any, limit: int = 32) -> str:
    value = "" if text is None else str(text)
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _add_node(nodes: list[dict[str, Any]], index: dict[str, dict[str, Any]], node: dict[str, Any]) -> None:
    if node["id"] in index:
        return
    index[node["id"]] = node
    nodes.append(node)


def _add_edge(edges: list[dict[str, Any]], seen: set[tuple[str, str, str]], edge: dict[str, Any]) -> None:
    key = (edge["source"], edge["target"], edge.get("label", ""))
    if key in seen:
        return
    seen.add(key)
    edges.append(edge)


def narrate_cf(rows: list[dict[str, Any]], target_id: int) -> str:
    if not rows:
        return "No similar-user path was found inside the current traversal bounds."
    title = rows[0].get("recTitle") or "this movie"
    peers = sorted({int(row["peerId"]) for row in rows})
    evidence: list[str] = []
    seen: set[tuple[Any, Any]] = set()
    for row in rows:
        key = (row["peerId"], row["sharedId"])
        if key in seen:
            continue
        seen.add(key)
        evidence.append(
            f"user {row['peerId']} also rated {row['sharedTitle']} {row['peerSharedRating']}"
        )
    preview = "; ".join(evidence[:4])
    peer_text = ", ".join(str(peer) for peer in peers)
    return (
        f"Users {peer_text} rated the same movies as user {target_id} above the peer threshold "
        f"and also rated {title}, which user {target_id} has not rated. Shared evidence: {preview}."
    )


def narrate_content(rows: list[dict[str, Any]], target_id: int) -> str:
    if not rows:
        return "No genre or tag path was found inside the current traversal bounds."
    title = rows[0].get("recTitle") or "this movie"
    genres = sorted({row["genre"] for row in rows if row.get("genre")})
    tags = sorted({row["tag"] for row in rows if row.get("tag")})
    liked = sorted({row["likedTitle"] for row in rows if row.get("likedTitle")})
    genre_text = ", ".join(genres) if genres else "no shared genres"
    tag_text = ", ".join(tags) if tags else "no shared tags"
    liked_text = ", ".join(liked[:4]) if liked else "the user's highly rated movies"
    return (
        f"User {target_id} rated {liked_text} highly. {title} shares {genre_text} "
        f"and {tag_text} with that cluster."
    )


def cf_elements(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        target_id = f"user-{row['targetId']}"
        peer_id = f"user-{row['peerId']}"
        shared_id = f"movie-{row['sharedId']}"
        rec_id = f"movie-{row['recId']}"
        _add_node(
            nodes,
            index,
            {
                "id": target_id,
                "label": f"User {row['targetId']}",
                "title": f"Target user {row['targetId']}",
                "color": USER,
                "size": 28,
            },
        )
        _add_node(
            nodes,
            index,
            {
                "id": rec_id,
                "label": clip(row.get("recTitle")),
                "title": str(row.get("recTitle") or rec_id),
                "color": REC,
                "size": 26,
            },
        )
        _add_node(
            nodes,
            index,
            {
                "id": peer_id,
                "label": f"User {row['peerId']}",
                "title": f"Similar user {row['peerId']}",
                "color": PEER,
                "size": 20,
            },
        )
        _add_node(
            nodes,
            index,
            {
                "id": shared_id,
                "label": clip(row.get("sharedTitle")),
                "title": str(row.get("sharedTitle") or shared_id),
                "color": MOVIE,
                "size": 16,
            },
        )
        _add_edge(
            edges,
            seen,
            {
                "source": target_id,
                "target": shared_id,
                "label": str(row.get("myRating")),
                "title": "RATED",
                "color": "#93c5fd",
            },
        )
        _add_edge(
            edges,
            seen,
            {
                "source": peer_id,
                "target": shared_id,
                "label": str(row.get("peerSharedRating")),
                "title": "RATED",
                "color": "#99f6e4",
            },
        )
        _add_edge(
            edges,
            seen,
            {
                "source": peer_id,
                "target": rec_id,
                "label": str(row.get("recRating")),
                "title": "RATED",
                "color": "#fecaca",
            },
        )
    return nodes, edges


def content_elements(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        target_id = f"user-{row['targetId']}"
        liked_id = f"movie-{row['likedId']}"
        rec_id = f"movie-{row['recId']}"
        genre_name = row.get("genre")
        tag_name = row.get("tag")
        _add_node(
            nodes,
            index,
            {
                "id": target_id,
                "label": f"User {row['targetId']}",
                "title": f"Target user {row['targetId']}",
                "color": USER,
                "size": 28,
            },
        )
        _add_node(
            nodes,
            index,
            {
                "id": rec_id,
                "label": clip(row.get("recTitle")),
                "title": str(row.get("recTitle") or rec_id),
                "color": REC,
                "size": 26,
            },
        )
        _add_node(
            nodes,
            index,
            {
                "id": liked_id,
                "label": clip(row.get("likedTitle")),
                "title": str(row.get("likedTitle") or liked_id),
                "color": MOVIE,
                "size": 16,
            },
        )
        _add_edge(
            edges,
            seen,
            {
                "source": target_id,
                "target": liked_id,
                "label": str(row.get("myRating")),
                "title": "RATED",
                "color": "#93c5fd",
            },
        )
        if genre_name:
            genre_id = f"genre-{genre_name}"
            _add_node(
                nodes,
                index,
                {
                    "id": genre_id,
                    "label": clip(genre_name, 24),
                    "title": str(genre_name),
                    "color": GENRE,
                    "size": 18,
                },
            )
            _add_edge(
                edges,
                seen,
                {"source": liked_id, "target": genre_id, "label": "", "title": "IN_GENRE", "color": "#86efac"},
            )
            _add_edge(
                edges,
                seen,
                {"source": rec_id, "target": genre_id, "label": "", "title": "IN_GENRE", "color": "#86efac"},
            )
        if tag_name:
            tag_id = f"tag-{tag_name}"
            _add_node(
                nodes,
                index,
                {
                    "id": tag_id,
                    "label": clip(tag_name, 24),
                    "title": str(tag_name),
                    "color": TAG,
                    "size": 16,
                },
            )
            _add_edge(
                edges,
                seen,
                {"source": liked_id, "target": tag_id, "label": "", "title": "HAS_TAG", "color": "#f0abfc"},
            )
            _add_edge(
                edges,
                seen,
                {"source": rec_id, "target": tag_id, "label": "", "title": "HAS_TAG", "color": "#f0abfc"},
            )
    return nodes, edges


def render_html(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    if not nodes:
        return ""
    from pyvis.network import Network

    net = Network(
        height="560px",
        width="100%",
        directed=True,
        bgcolor="#0f172a",
        font_color="#e5e7eb",
        cdn_resources="in_line",
    )
    for node in nodes:
        net.add_node(
            node["id"],
            label=node["label"],
            title=node.get("title") or node["label"],
            color=node["color"],
            size=node.get("size", 16),
        )
    for edge in edges:
        net.add_edge(
            edge["source"],
            edge["target"],
            label=edge.get("label") or "",
            title=edge.get("title") or "",
            color=edge.get("color") or "#9ca3af",
        )
    net.set_options(
        """
        {
          "nodes": {"font": {"size": 14, "color": "#e5e7eb"}},
          "edges": {
            "arrows": {"to": {"enabled": true}},
            "font": {"size": 11, "align": "middle", "color": "#cbd5e1"},
            "smooth": {"type": "dynamic"}
          },
          "physics": {"stabilization": {"iterations": 120}}
        }
        """
    )
    return net.generate_html(notebook=False)
