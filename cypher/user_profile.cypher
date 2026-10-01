MATCH (u:User {userId: $userId})
USING INDEX u:User(userId)
OPTIONAL MATCH (u)-[r:RATED]->(:Movie)
RETURN u.userId AS userId,
       count(r) AS ratingCount,
       avg(r.rating) AS avgRating;
