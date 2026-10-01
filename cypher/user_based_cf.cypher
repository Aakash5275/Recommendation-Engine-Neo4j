// Strategy A
// (Target User)-[:RATED]->(Shared Movie)<-[:RATED]-(Similar User)-[:RATED]->(Recommendation)
// Similar users must have rated a shared movie higher than $peerMinRating (spec default: 4.0).
MATCH (target:User {userId: $userId})
USING INDEX target:User(userId)
CALL {
  WITH target
  MATCH (target)-[my:RATED]->(shared:Movie)
  WHERE my.rating >= $minRating
  WITH target, shared, my
  ORDER BY my.rating DESC, shared.movieId ASC
  LIMIT $seedLimit
  MATCH (shared)<-[their:RATED]-(peer:User)
  WHERE peer <> target AND their.rating > $peerMinRating
  WITH peer, count(DISTINCT shared) AS sharedCount
  WHERE sharedCount >= $minShared
  ORDER BY sharedCount DESC, peer.userId ASC
  LIMIT $neighborLimit
  RETURN peer, sharedCount
}
MATCH (peer)-[recRating:RATED]->(rec:Movie)
WHERE recRating.rating >= $minRating
  AND NOT (target)-[:RATED]->(rec)
WITH rec,
     count(DISTINCT peer) AS similarityCount,
     avg(recRating.rating) AS avgRating,
     sum(sharedCount * recRating.rating) AS matchScore
ORDER BY matchScore DESC, similarityCount DESC, rec.movieId ASC
LIMIT $limit
OPTIONAL MATCH (rec)-[:IN_GENRE]->(g:Genre)
WITH rec, similarityCount, avgRating, matchScore,
     [name IN collect(DISTINCT g.name) WHERE name IS NOT NULL] AS genres
RETURN rec.movieId AS movieId,
       coalesce(rec.title, 'Movie ' + toString(rec.movieId)) AS title,
       similarityCount,
       round(avgRating, 2) AS avgRating,
       round(matchScore, 2) AS matchScore,
       genres
ORDER BY matchScore DESC, similarityCount DESC, movieId ASC;
