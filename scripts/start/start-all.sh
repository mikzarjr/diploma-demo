#!/usr/bin/env bash
set -e

echo "=== Ensuring Docker networks exist ==="
docker network inspect traefik-net  >/dev/null 2>&1 || docker network create traefik-net
docker network inspect app-internal >/dev/null 2>&1 || docker network create app-internal

bash start-gateway.sh
bash start-redis.sh
bash start-db.sh
bash start-s3.sh
bash start-auth.sh
bash start-main.sh
