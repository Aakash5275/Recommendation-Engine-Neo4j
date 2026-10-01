MATCH (u:User {userId: $userId})
USING INDEX u:User(userId)
MATCH (u)-[r:RATED]->(:Movie)-[:IN_GENRE]->(g:Genre)
WHERE r.rating >= $minRating
RETURN g.name AS genre, count(*) AS n
ORDER BY n DESC, genre ASC
LIMIT 5;
