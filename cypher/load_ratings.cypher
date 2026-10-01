UNWIND $rows AS row
MERGE (u:User {userId: row.userId})
MERGE (m:Movie {movieId: row.movieId})
MERGE (u)-[r:RATED]->(m)
SET r.rating = row.rating, r.timestamp = row.timestamp;
