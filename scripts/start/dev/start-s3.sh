cd ../../../infra/storage/s3/ || exit
docker compose -f docker-compose.dev.yml up -d --build
