MATCH (target:User {userId: $userId})
USING INDEX target:User(userId)
MATCH (rec:Movie {movieId: $movieId})
USING INDEX rec:Movie(movieId)
MATCH (target)-[my:RATED]->(liked:Movie)-[:IN_GENRE]->(g:Genre)<-[:IN_GENRE]-(rec)
WHERE my.rating >= $minRating
  AND liked <> rec
OPTIONAL MATCH (liked)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(rec)
RETURN target.userId AS targetId,
       liked.movieId AS likedId,
       coalesce(liked.title, 'Movie ' + toString(liked.movieId)) AS likedTitle,
       my.rating AS myRating,
       g.name AS genre,
       rec.movieId AS recId,
       coalesce(rec.title, 'Movie ' + toString(rec.movieId)) AS recTitle,
       t.name AS tag
LIMIT $pathLimit;
