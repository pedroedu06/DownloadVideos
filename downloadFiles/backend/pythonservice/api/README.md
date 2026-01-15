### API

Aqui e a api que inicia o Worker, a base dela e usando a blibioteca do python FastApi, uma forma leve de iniciar as features e retornar infos pro front-end

algumas infos basicas do main.py

- /downloadTask: Cria a task do download colocando as infos principais no redis e assim baixando o video
- /downloadStatus: Retorna infos de status e progresso
- /downloadCancel: Coloca um gatilho de cancel no Redis assim ele cancela o download.
- /downloadPath: Mapeia o path do usuario para colocar os downloads
- /downloadSettings: Mapeia os formatos e qualidades de videos e audios preferidos do usuario, caso o usuario deixe no automatico ele seguirar com o formato e qualidade padrao. 

alem disso nessa pasta temos os Schemas, importantes para o FastApi, e o redisClient que faz a coneccao do python com Redis.

