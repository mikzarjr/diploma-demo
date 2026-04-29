cd ../../infra/storage/db/ || exit
docker compose -f docker-compose.prod.yml up -d --build
