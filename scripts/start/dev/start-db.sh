cd ../../../infra/storage/db/ || exit
docker compose -f docker-compose.dev.yml up -d --build
