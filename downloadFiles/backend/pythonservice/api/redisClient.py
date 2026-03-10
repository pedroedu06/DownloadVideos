import redis
import os
import time
import threading

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6590))
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

# Retry com backoff exponencial para esperar o Redis (Docker) ficar pronto
MAX_RETRIES = 30          # tenta por até ~2 minutos
INITIAL_BACKOFF = 1       # começa com 1 segundo
MAX_BACKOFF = 10          # máximo 10 segundos entre tentativas

_redis_client = None
_redis_lock = threading.Lock()


def _connect_with_retry():
    """Tenta conectar ao Redis com retry e backoff exponencial."""
    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client = redis.Redis(connection_pool=_redis_pool)
            client.ping()
            print(f"[Redis] Conectado com sucesso ao Redis em {REDIS_HOST}:{REDIS_PORT} (tentativa {attempt})")
            return client
        except (redis.ConnectionError, redis.TimeoutError) as e:
            if attempt == MAX_RETRIES:
                print(f"[Redis] ERRO: Não foi possível conectar ao Redis após {MAX_RETRIES} tentativas: {e}")
                return None
            print(f"[Redis] Tentativa {attempt}/{MAX_RETRIES} falhou, aguardando {backoff}s... ({e})")
            time.sleep(backoff)
            backoff = min(backoff * 1.5, MAX_BACKOFF)
    return None


def get_redis():
    """Retorna o cliente Redis, criando conexão com retry se necessário."""
    global _redis_client
    with _redis_lock:
        if _redis_client is not None:
            try:
                _redis_client.ping()
                return _redis_client
            except Exception:
                print("[Redis] Conexão perdida, reconectando...")
                _redis_client = None

        _redis_client = _connect_with_retry()
        return _redis_client


# Conexão inicial com retry (espera o Docker subir)
redisClient = get_redis()
