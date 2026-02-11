# Redis - Configuração para VPS

## Início rápido (Produção)

### 1. Pré-requisitos
- Docker e Docker Compose instalados na VPS
- Portas abertas: 6379 (ou a porta que escolher)

### 2. Configuração
Edite o arquivo `.env` antes de subir:

```bash
# Altere a senha padrão!
REDIS_PASSWORD=SUA_SENHA_FORTE_AQUI

# Ajuste a memória conforme sua VPS
REDIS_MAXMEMORY=256mb

# Porta (padrão: 6379)
REDIS_PORT=6379
```

### 3. Subir o Redis
```bash
cd backend/redis
docker compose up -d
```

### 4. Verificar status
```bash
docker compose ps
docker compose logs redis
```

### 5. Testar conexão
```bash
docker exec -it downloadfiles-redis redis-cli -a SUA_SENHA ping
# Deve retornar: PONG
```

### 6. Conectar o App
Configure as variáveis de ambiente no backend Python:

```env
REDIS_HOST=ip-da-vps   # ou localhost se estiver na mesma máquina
REDIS_PORT=6379
REDIS_PASSWORD=SUA_SENHA_FORTE_AQUI
```

## Persistência
- **RDB**: Snapshots a cada 60s (se 1000+ chaves mudaram) e 300s (se 100+ mudaram)
- **AOF**: Append-only file sincronizado a cada segundo

Os dados ficam salvos no volume Docker `redis-data`.

## Comandos úteis
```bash
# Parar
docker compose down

# Parar e apagar dados
docker compose down -v

# Ver uso de memória
docker exec -it downloadfiles-redis redis-cli -a SUA_SENHA info memory

# Monitorar em tempo real
docker exec -it downloadfiles-redis redis-cli -a SUA_SENHA monitor

# Backup manual
docker exec downloadfiles-redis redis-cli -a SUA_SENHA BGSAVE
```

## Segurança em Produção
1. **Troque a senha padrão** no `.env`
2. **Use firewall** para limitar acesso à porta 6379
3. **Não exponha** a porta do Redis para a internet pública
4. Para acesso externo, use **VPN** ou **SSH tunnel**
