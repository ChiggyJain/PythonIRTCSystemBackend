#!/bin/sh

set -e

printf "Waiting for MySQL server to start...\n"
until nc -z mysql 3306; do
  printf "MySQL server not ready...\n"
  sleep 2
done
printf "MySQL server started...\n"

printf "Waiting for Redis server to start...\n"
until nc -z redis 6379; do
    printf "Redis server not ready...\n"
    sleep 2
done
printf "Redis server started...\n"


printf "Waiting for Kafka server to start...\n"
until nc -z kafka 9092; do
  printf "Kafka server not ready...\n"
  sleep 2
done
printf "Kafka server started...\n"


printf "Waiting for Elasticsearch server to start...\n"
until nc -z elasticsearch 9200; do
  printf "Elasticsearch server not ready...\n"
  sleep 2
done
printf "Elasticsearch server started...\n"


printf "Generating Alembic migration...\n"
alembic revision --autogenerate -m "auto migration"
printf "Applying Alembic migration...\n"
alembic upgrade head
printf "Alembic migration completed...\n"

printf "FastAPI server to start...\n"
uvicorn app.main:app --host 0.0.0.0 --port 8000
printf "FastAPI server started...\n"