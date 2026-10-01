// TAGGED keeps the user-authored tag on the edge.
// HAS_TAG projects that keyword onto a Tag node so content traversal can enter it.
UNWIND $rows AS row
MERGE (u:User {userId: row.userId})
MERGE (m:Movie {movieId: row.movieId})
MERGE (t:Tag {name: row.tag})
MERGE (u)-[rel:TAGGED {tag: row.tag}]->(m)
SET rel.timestamp = row.timestamp
MERGE (m)-[:HAS_TAG]->(t);
