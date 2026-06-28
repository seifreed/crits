#!/bin/sh
set -e

DB_CONFIG=crits/config/database.py

# Generate config/database.py on first boot, pointed at the linked mongo service.
if [ ! -f "$DB_CONFIG" ]; then
    if [ -z "$CRITS_SECRET_KEY" ]; then
        CRITS_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
    fi
    cat > "$DB_CONFIG" <<EOF
MONGO_HOST = '${MONGO_HOST:-mongo}'
MONGO_PORT = ${MONGO_PORT:-27017}
MONGO_DATABASE = '${MONGO_DATABASE:-crits}'
MONGO_SSL = False
MONGO_USER = '${MONGO_USER:-}'
MONGO_PASSWORD = '${MONGO_PASSWORD:-}'
MONGO_REPLICASET = None
SECRET_KEY = '${CRITS_SECRET_KEY}'
FILE_DB = GRIDFS
EOF
fi

# Wait for MongoDB to accept connections.
echo "Waiting for MongoDB at ${MONGO_HOST:-mongo}:${MONGO_PORT:-27017} ..."
python - <<'PY'
import os, time
from pymongo import MongoClient
host = os.environ.get('MONGO_HOST', 'mongo')
port = int(os.environ.get('MONGO_PORT', '27017'))
for _ in range(60):
    try:
        MongoClient(host, port, serverSelectionTimeoutMS=1000).admin.command('ping')
        print("MongoDB is up.")
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("MongoDB did not become available in time")
PY

# Idempotent first-run bootstrap: config, roles, default dashboard, indexes.
# create_default_collections has drop protection and skips anything that exists.
if [ "${CRITS_BOOTSTRAP:-1}" = "1" ]; then
    echo "Bootstrapping CRITs collections/roles/indexes ..."
    python manage.py create_default_collections || true
    python manage.py create_indexes || true
fi

# Optionally create an admin user when credentials are provided via env.
if [ -n "$CRITS_ADMIN_USER" ] && [ -n "$CRITS_ADMIN_PASS" ]; then
    python manage.py users -R UberAdmin -s -i -a \
        -u "$CRITS_ADMIN_USER" -p "$CRITS_ADMIN_PASS" \
        -e "${CRITS_ADMIN_EMAIL:-admin@example.com}" \
        -f "${CRITS_ADMIN_FIRST:-Admin}" -l "${CRITS_ADMIN_LAST:-User}" \
        -o "${CRITS_ADMIN_ORG:-CRITs}" || true
fi

exec "$@"
