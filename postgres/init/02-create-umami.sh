#!/usr/bin/env bash
set -euo pipefail

: "${UMAMI_DB_NAME:?UMAMI_DB_NAME is required}"
: "${UMAMI_DB_USERNAME:?UMAMI_DB_USERNAME is required}"
: "${UMAMI_DB_PASSWORD:?UMAMI_DB_PASSWORD is required}"

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "postgres" \
  --set umami_db="$UMAMI_DB_NAME" \
  --set umami_user="$UMAMI_DB_USERNAME" \
  --set umami_pass="$UMAMI_DB_PASSWORD" \
<<'SQL'
-- Create role if missing
SELECT format('CREATE USER %I WITH PASSWORD %L', :'umami_user', :'umami_pass')
WHERE NOT EXISTS (
  SELECT 1 FROM pg_roles WHERE rolname = :'umami_user'
)\gexec

-- Create database if missing
SELECT format('CREATE DATABASE %I OWNER %I', :'umami_db', :'umami_user')
WHERE NOT EXISTS (
  SELECT 1 FROM pg_database WHERE datname = :'umami_db'
)\gexec
SQL
