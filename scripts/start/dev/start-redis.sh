cd ../../../infra/storage/redis/ || exit
docker compose -f docker-compose.dev.yml up -d --build
