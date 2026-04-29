#!/bin/sh
set -e

/wait-for-it.sh db:5432 --timeout=60 --strict -- echo "Postgres is up"

alembic revision --autogenerate -m "update" 2>&1 | tee /tmp/alembic_output.txt

MIGRATION_FILE=$(grep "Generating" /tmp/alembic_output.txt | sed 's/.*Generating \(.*\) \.\.\.  done/\1/' || true)
if [ -n "$MIGRATION_FILE" ] && [ -f "$MIGRATION_FILE" ]; then
    if grep -q "pass" "$MIGRATION_FILE" && ! grep -qE "op\." "$MIGRATION_FILE"; then
        echo "Empty migration detected, removing: $MIGRATION_FILE"
        rm "$MIGRATION_FILE"
    fi
fi

alembic upgrade head