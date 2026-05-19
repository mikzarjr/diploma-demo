cd ../../../infra/auth/ || exit
docker compose -f docker-compose.dev.yml up -d --build
