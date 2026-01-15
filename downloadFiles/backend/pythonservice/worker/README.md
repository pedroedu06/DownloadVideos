### WORKER ###

Esse aqui é o worker, talvez o coração do projeto. Aqui funciona o download do vídeo via yt_dlp; o usuário coloca a URL do vídeo no front e o worker trabalha em baixar o vídeo.
Algumas das features do projeto:

- Locks para não baixar vários vídeos de uma vez;
- DLQ para armazenar mensagens de erro do yt-dlp;
- Re-enfileiramento: caso ocorra algum erro no download, ele tenta refazer o download;
- Logs estruturados: melhor forma do worker informar o que está acontecendo;
- Retry automático: caso ocorra erro no download, ele faz retry automático;
- Shutdown: ele faz o desligamento do worker, seja pelo usuário ou pelo próprio app;
- Cancelamento do download;

Além disso, temos o Redis, que é responsável por armazenar as informações principais do download e iniciá-lo no worker. Também retorna as informações dos logs para serem reutilizadas no front-end.

A base do codigo foi via vibe coding, mas features novas, e correcao de bugs, foram eu. 