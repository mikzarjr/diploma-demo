cd ../../infra/auth/ || exit
docker compose -f docker-compose.prod.yml up -d --build
