docker network create traefik-net 2>/dev/null || true
bash start-gateway.sh
bash start-redis.sh
bash start-db.sh
bash start-s3.sh
bash start-main.sh
