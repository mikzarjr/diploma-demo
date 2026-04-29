cd ../../infra/storage/s3/ || exit
docker compose -f docker-compose.prod.yml up -d --build
