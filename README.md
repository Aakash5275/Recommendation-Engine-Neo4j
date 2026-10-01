# Graph Analytics and Collaborative Recommendation Engine

MovieLens is loaded into Neo4j as users, movies, genres, and tags. Recommendations are Cypher traversals: similar users through shared high ratings, and unwatched movies that sit in the same genre and tag cluster. A Streamlit app runs both strategies for a chosen `userId` and shows the match metrics, the path, and the query plan.

```
[ MovieLens CSV ] -> [ constraints + batched MERGE ] -> [ Neo4j ] -> [ Streamlit ]
```

## Graph model

```
(:User)-[:RATED {rating, timestamp}]->(:Movie)-[:IN_GENRE]->(:Genre)
(:User)-[:TAGGED {tag, timestamp}]->(:Movie)-[:HAS_TAG]->(:Tag)
```

| Node | Identity | Source |
| --- | --- | --- |
| User | `userId` | created from `ratings.csv` and `tags.csv` |
| Movie | `movieId`, `title` | `movies.csv` |
| Genre | `name` | pipe-separated `genres` column |
| Tag | `name` | `tags.csv` |

`TAGGED` keeps the original tag string and timestamp on the edge. `HAS_TAG` points the movie at a `Tag` node so the content traversal can enter that node. Uniqueness constraints on `User.userId`, `Movie.movieId`, `Genre.name`, and `Tag.name` are created before the load. The user and movie constraints are the property indexes the recommendation queries anchor on (`USING INDEX`).

## Strategies

**A. User-based collaborative filtering.** From the target user's highly rated movies, find other users who rated those same movies higher than 4.0, keep the neighbors with the largest overlap, then step out to highly rated movies the target user has not rated.

```
(Target User)-[:RATED]->(Shared Movie)<-[:RATED]-(Similar User)-[:RATED]->(Recommendation)
```

Match score is the sum of `shared movies × that neighbor's rating` for the candidate. The result also reports the similar-user count and the average of those ratings as the predicted rating.

**B. Content hybrid.** Take the genres that dominate the target user's high ratings, cross to movies in those genres that the user has not rated, then add overlap on `Tag` nodes reached from the same high ratings.

```
(Target User)-[:RATED]->(Liked Movie)-[:IN_GENRE]->(Genre)<-[:IN_GENRE]-(Recommendation)
```

Match score is `5 × shared genres + genre strength + tag boost × shared tags`.

Seed, neighbor, and candidate limits are part of the query so a live traversal stays bounded on the 32M graph. They do not change the path, they cap how much of it is expanded per request.

## Project layout

| Piece | File |
| --- | --- |
| Uniqueness constraints | `cypher/constraints.cypher`, `src/schema.py` |
| Batch load | `src/ingest.py`, `cypher/load_*.cypher` |
| CSV cleaning | `src/transform.py` |
| Strategy A | `cypher/user_based_cf.cypher` |
| Strategy B | `cypher/content_hybrid.cypher` |
| Plan check | `src/plan.py`, `src/profile.py` |
| Dashboard | `app.py` |

## Setup

Python 3.10+ and Docker.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
docker compose up -d
```

Neo4j Browser is at <http://localhost:7474> (`neo4j` / `movielens32m`). The Bolt port is `7687`. If you use Neo4j Desktop instead of Docker, point `.env` at that instance. The password in `.env` and `NEO4J_AUTH` in `docker-compose.yml` must match.

For the full 32M graph, give Docker enough memory and raise the heap and page cache in `docker-compose.yml` (4G / 4G is a practical starting point).

## Check the pipeline on the sample

The sample is a 10-movie fixture, not MovieLens. User 1 loves four sci-fi titles. Users 2 and 3 share those ratings and also love movies 6 and 7, which user 1 has not seen.

```powershell
python -m src.sample_data --out data/sample
python -m src.ingest --data-dir data/sample --reset --yes
python -m src.smoke_test --sample
streamlit run app.py
```

In the dashboard, run recommendations for user `1`. Strategy A should surface **Zeta Horizon (2010)** and **Eta Vector (2012)**. Open either title to see the similar users, the shared movies, and the topology view.

`--reset --yes` deletes every node in the database. Use it when switching from the sample to the full export, or the other way around.

## Load MovieLens 32M

GroupLens terms apply to the dataset. It is downloaded into `data/` and is not committed.

```powershell
python -m src.download_dataset
python -m src.ingest --data-dir data/ml-32m
```

Ratings are written in batches (default 20,000) with `UNWIND` and `MERGE`, so a rerun updates properties instead of duplicating nodes. A partial load for a machine that should not take the full file:

```powershell
python -m src.ingest --data-dir data/ml-32m --max-ratings 500000 --max-tags 100000
```

Then:

```powershell
streamlit run app.py
python -m src.profile --user-id 1
python -m src.recommend --user-id 1
```

`src.profile` prints `EXPLAIN` for both strategies and exits with an error if the plan has no index seek or if it scans all nodes. `--mode profile` runs `PROFILE` and prints dbHits. The same plan is available in each dashboard tab. `PROFILE` executes the traversal, so leave it for a chosen user rather than running it on every page load.

## Tests

```powershell
python -m unittest discover -s tests -v
```

These tests cover CSV cleaning, the demo fixture, path drawing, and the Cypher/parameter contract. `src.smoke_test` is the live check against Neo4j.
