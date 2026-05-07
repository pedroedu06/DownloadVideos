### API

Esta API FastAPI agora usa SQLite como fonte unica de estado.

- `/downloadtask`: cria um job na fila persistida em SQLite.
- `/downloadStatus/{job_id}`: retorna o status atual salvo no banco.
- `/ws/downloads/{job_id}`: envia progresso em tempo real para o front via WebSocket.
- `/downloadCancel/{job_id}`: marca cancelamento no banco para o worker interromper o job.
- `/downloadPath` e `/downloadSettings`: salvam configuracoes persistidas em SQLite.
- `/userDownload/{user_id}/downloads`: retorna o historico concluido do usuario.

O worker le a mesma base SQLite para buscar jobs pendentes, atualizar progresso e salvar o historico final.
