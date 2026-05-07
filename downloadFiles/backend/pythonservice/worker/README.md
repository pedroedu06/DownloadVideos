### WORKER

O worker usa `yt_dlp` para processar os downloads e SQLite para coordenar o fluxo.

- Busca jobs `queued` diretamente na tabela `downloads`.
- Faz claim atomico do job antes de iniciar o download.
- Atualiza `status`, `progress`, `error` e metadados no mesmo banco.
- Respeita cancelamento marcando o job como `cancelled`.
- Reenfileira jobs com `next_attempt_at` quando ocorre retry.
- Salva o historico final (`title`, `path`, `size`, `thumbnail`) na propria linha do download.

O front recebe o progresso em tempo real pelo WebSocket da API, que observa as alteracoes gravadas pelo worker no SQLite.
