// Strategy B
// (Target User)-[:RATED]->(Liked Movie)-[:IN_GENRE]->(Genre)<-[:IN_GENRE]-(Recommended Movie)
// Tag nodes join the same shortlist through (Liked Movie)-[:HAS_TAG]->(Tag)<-[:HAS_TAG]-(Recommended Movie).
MATCH (target:User {userId: $userId})
USING INDEX target:User(userId)
MATCH (target)-[my:RATED]->(:Movie)-[:IN_GENRE]->(g:Genre)
WHERE my.rating >= $minRating
WITH target, g, count(*) AS weight
ORDER BY weight DESC, g.name ASC
LIMIT $topGenres
MATCH (rec:Movie)-[:IN_GENRE]->(g)
WHERE NOT (target)-[:RATED]->(rec)
WITH rec,
     count(DISTINCT g) AS genreOverlap,
     sum(weight) AS genreWeight,
     collect(DISTINCT g.name) AS genreNames
WHERE genreOverlap >= $minGenreOverlap
ORDER BY genreOverlap DESC, genreWeight DESC, rec.movieId ASC
LIMIT $candidateLimit
OPTIONAL MATCH (target)-[tagRating:RATED]->(:Movie)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(rec)
WHERE tagRating.rating >= $minRating
WITH rec, genreOverlap, genreWeight, genreNames, count(DISTINCT t) AS tagOverlap
RETURN rec.movieId AS movieId,
       coalesce(rec.title, 'Movie ' + toString(rec.movieId)) AS title,
       genreOverlap,
       genreNames[0..8] AS genres,
       tagOverlap,
       round(genreOverlap * 5.0 + genreWeight + tagOverlap * $tagBoost, 2) AS matchScore
ORDER BY matchScore DESC, genreOverlap DESC, movieId ASC
LIMIT $limit;
