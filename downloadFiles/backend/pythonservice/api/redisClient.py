import redis
import os

REDIS_CLIENT = os.getenv('REDIS_HOST', 'localhost')

redisClient = redis.Redis(
    host=REDIS_CLIENT,
    port=6379,
    decode_responses=True
)