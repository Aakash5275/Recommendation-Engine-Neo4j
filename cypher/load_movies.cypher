UNWIND $rows AS row
MERGE (m:Movie {movieId: row.movieId})
SET m.title = row.title
WITH m, row
UNWIND row.genres AS genreName
MERGE (g:Genre {name: genreName})
MERGE (m)-[:IN_GENRE]->(g);
