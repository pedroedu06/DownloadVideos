FROM python:3.11-alpine

RUN apk add --no-cache \
    ffmpeg \
    nodejs \
    && rm -rf /usr/lib/node_modules/npm

WORKDIR /worker

# instalar dependências do sistema necessárias para yt-dlp e ffmpeg e nodejs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV APP_ENV=production
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

# usar -u para saida nao bufferizada 
CMD [ "python", "-u", "worker.py" ]
