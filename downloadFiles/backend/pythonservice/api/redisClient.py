import redis
import os

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASS = os.getenv('REDIS_PASSWORD')
if REDIS_PASS and not REDIS_PASS.strip():
    REDIS_PASS = None
elif not REDIS_PASS:
    REDIS_PASS = None

# Pool de conexões: reutiliza conexões TCP, evita overhead de reconexão
_redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASS,
    decode_responses=True,
    max_connections=20,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
)

def get_redis():
    try:
        r = redis.Redis(connection_pool=_redis_pool)
        r.ping()
        return r
    except redis.ConnectionError as e:
        print(f"falha ao conectar ao redis", e)
        return None
 
redisClient = get_redis()
