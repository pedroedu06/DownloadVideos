FROM python:3.11-slim

WORKDIR /worker

# instalar dependências do sistema necessárias para yt-dlp e ffmpeg e nodejs
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       nodejs \
       npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV APP_ENV=production
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

# usar -u para saída não bufferizada (útil para logs em containers)
CMD [ "python", "-u", "worker.py" ]
