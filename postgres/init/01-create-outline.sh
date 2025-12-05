#!/usr/bin/env bash
set -euo pipefail

: "${OUTLINE_DB_NAME:?OUTLINE_DB_NAME is required}"
: "${OUTLINE_DB_USERNAME:?OUTLINE_DB_USERNAME is required}"
: "${OUTLINE_DB_PASSWORD:?OUTLINE_DB_PASSWORD is required}"

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "postgres" \
  -v outline_db="$OUTLINE_DB_NAME" \
  -v outline_user="$OUTLINE_DB_USERNAME" \
  -v outline_pass="$OUTLINE_DB_PASSWORD" \
<<'SQL'
-- Create role if missing
SELECT format('CREATE USER %I WITH PASSWORD %L', :'outline_user', :'outline_pass')
WHERE NOT EXISTS (
  SELECT 1 FROM pg_roles WHERE rolname = :'outline_user'
)\gexec

-- Create database if missing
SELECT format('CREATE DATABASE %I OWNER %I', :'outline_db', :'outline_user')
WHERE NOT EXISTS (
  SELECT 1 FROM pg_database WHERE datname = :'outline_db'
)\gexec
SQL
