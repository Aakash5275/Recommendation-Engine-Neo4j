MATCH (target:User {userId: $userId})
USING INDEX target:User(userId)
MATCH (rec:Movie {movieId: $movieId})
USING INDEX rec:Movie(movieId)
MATCH (target)-[my:RATED]->(shared:Movie)<-[their:RATED]-(peer:User)-[rr:RATED]->(rec)
WHERE my.rating >= $minRating
  AND their.rating > $peerMinRating
  AND rr.rating >= $minRating
RETURN target.userId AS targetId,
       shared.movieId AS sharedId,
       coalesce(shared.title, 'Movie ' + toString(shared.movieId)) AS sharedTitle,
       my.rating AS myRating,
       peer.userId AS peerId,
       their.rating AS peerSharedRating,
       rec.movieId AS recId,
       coalesce(rec.title, 'Movie ' + toString(rec.movieId)) AS recTitle,
       rr.rating AS recRating
LIMIT $pathLimit;
