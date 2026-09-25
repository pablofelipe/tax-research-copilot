#!/usr/bin/env bash
# Generates a new demo credential and reloads Caddy with it (ADR-0007).
# Run this on the host, not committed anywhere — the generated password is
# handed out manually, on request, never embedded automatically.
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=".env"
touch "$ENV_FILE"

USERNAME="demo"
PASSWORD=$(openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | cut -c1-20)
HASH=$(docker run --rm caddy:2 caddy hash-password --plaintext "$PASSWORD")
# docker compose expands unescaped '$' in .env values as variable references,
# which would corrupt a bcrypt hash (it's full of '$' delimiters) — escape
# every '$' as '$$' so it round-trips through .env literally.
HASH_ESCAPED=${HASH//\$/\$\$}

upsert() {
	local key="$1" value="$2"
	if grep -q "^${key}=" "$ENV_FILE"; then
		sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
	else
		echo "${key}=${value}" >>"$ENV_FILE"
	fi
}

upsert CADDY_USER "$USERNAME"
upsert CADDY_HASH "$HASH_ESCAPED"

docker compose -f docker-compose.yml -f docker-compose.hosted.yml up -d caddy

echo "New credential (send manually, do not commit or log this):"
echo "  username: $USERNAME"
echo "  password: $PASSWORD"
