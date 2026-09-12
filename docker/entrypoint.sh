#!/bin/sh
# REC Guard backend entrypoint: generate RSA keys + initialise the ledger if
# they do not exist yet (both live on Docker volumes), then exec the server.
set -e
cd /app
python scripts/generate_keys.py
python scripts/init_db.py
exec "$@"
