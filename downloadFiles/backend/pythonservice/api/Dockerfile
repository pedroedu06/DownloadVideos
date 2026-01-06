FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
ENV APP_ENV=production
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]