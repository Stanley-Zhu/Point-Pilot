-- Runs once, when the Postgres volume is first created.
-- Dev-only passwords; the port is bound to localhost in docker-compose.yml.

-- Owns the schema and runs Alembic migrations.
CREATE ROLE pointpilot_owner LOGIN PASSWORD 'owner_dev';

-- What the API connects as. Table permissions are granted in migrations,
-- and it never receives UPDATE or DELETE on ledger_events.
CREATE ROLE pointpilot_admin LOGIN PASSWORD 'admin_dev';

CREATE DATABASE pointpilot OWNER pointpilot_owner;
CREATE DATABASE pointpilot_test OWNER pointpilot_owner;

GRANT CONNECT ON DATABASE pointpilot TO pointpilot_admin;
GRANT CONNECT ON DATABASE pointpilot_test TO pointpilot_admin;
