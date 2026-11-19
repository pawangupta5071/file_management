# Project setup

Use this to bootstrap a new FastAPI service with Postgres, Redis, and Alembic. It covers the app shell, configuration, local services, and migrations. Add models, routes, and business logic after this is running.

Replace these two values everywhere they appear:

| Placeholder | Meaning | Example |
| --- | --- | --- |
| `PROJECT_SLUG` | Package and display name, no spaces | `billing` |
| `DB_NAME` | Postgres database name | `billing` |

`PROJECT_SLUG` and `DB_NAME` can be the same word. Keep `DB_NAME` lowercase.

## Layout

```text
.
├── app/
│   ├── api/
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   ├── services/
│   ├── config.py
│   ├── database.py
│   └── main.py
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── tests/
├── .env
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── flush_services.sh
├── requirements.txt
├── runserver.sh
└── setup.sh
```

`app/api`, `app/schemas`, `app/services`, and `tests` start empty. `app/models/__init__.py` only exists so Alembic can import models later.

## Python dependencies

Create `requirements.txt`:

```text
alembic==1.20.0
fastapi==0.156.0
psycopg==3.3.6
psycopg-binary==3.3.6
pydantic-settings==2.16.1
pytest==9.1.1
python-dotenv==1.2.4
redis==8.1.0
SQLAlchemy==2.1.5
uvicorn==0.54.0
```

## Environment

Create `.env` in the project root:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/DB_NAME
REDIS_URL=redis://localhost:6379/0
BASE_URL=http://localhost:8000
```

Substitute the real database name for `DB_NAME`. `BASE_URL` is available to the app when it needs to build absolute links. Do not commit `.env`.

## Git ignore

Create `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Virtual environments
.venv/
venv/
env/

# Environment variables and secrets
.env
.env.*
!.env.example

# Testing and coverage
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/

# Type checking and linting
.mypy_cache/
.pyright/
.ruff_cache/

# Build and distribution
build/
dist/
*.egg-info/

# IDEs and editors
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Local databases and data
*.db
*.sqlite3
.services/
dump.rdb

# Temporary files
*.tmp
*.bak
```

Keep `alembic.ini` and `alembic/versions/` tracked.

## Application shell

`app/config.py` loads `.env` through pydantic-settings:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
```

`app/database.py` creates the engine, the session factory, and the declarative base. Add tables on `Base` in later work. This file does not define any.

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as session:
        yield session
```

`app/models/__init__.py` is the registration point. Leave it empty until models exist, then import each model module here so Alembic autogenerate can see them:

```python
# from app.models.example import Example
```

`app/main.py` is the process entrypoint. It exposes a health check and nothing else:

```python
from fastapi import FastAPI

app = FastAPI(
    title="PROJECT_SLUG",
    version="1.0.0",
)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
```

Mount routers with `app.include_router(...)` once they exist.

## Alembic

From the project root, with the virtualenv active:

```bash
alembic init alembic
```

That writes `alembic.ini`, `alembic/env.py`, and `alembic/script.py.mako`. Leave `sqlalchemy.url` in `alembic.ini` empty. The connection string comes from `.env`.

Replace `alembic/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  — registers models on Base.metadata
from app.config import settings
from app.database import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("%", "%%"),
)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

`import app.models` is what makes autogenerate notice models. `compare_type=True` includes column type changes in generated revisions.

Generate and apply migrations only after models exist:

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

If `alembic/versions` already has a revision, skip `alembic revision` and run `alembic upgrade head`.

## Docker services

Docker runs Postgres 17 and Redis 7. The FastAPI process stays on the host.

`docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: DB_NAME
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Bring the stack up:

```bash
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
./runserver.sh
```

Check the app:

```bash
curl http://localhost:8000/api/health
```

Stop the containers with `docker compose down`. `docker compose down -v` also deletes the Postgres volume.

Interactive docs are at [http://localhost:8000/docs](http://localhost:8000/docs) while the server is running.

## Local services on a Mac

`setup.sh` is the path that uses [Postgres.app](https://postgresapp.com/) and a Redis build under `.services/`. Install Postgres.app, move it to `/Applications`, then run the script from the project root.

`setup.sh`:

```bash
#!/usr/bin/env bash
# Idempotent local setup:
#   Postgres.app + Redis built from source + Alembic.
# Safe to run again. Uses DATABASE_URL / REDIS_URL from .env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PG_BIN="/Applications/Postgres.app/Contents/Versions/latest/bin"
DB_NAME="DB_NAME"
DB_USER="postgres"
DB_PASSWORD="postgres"

REDIS_VERSION="7.4.7"
REDIS_PREFIX="$ROOT/.services/redis"
REDIS_SRC="$ROOT/.services/src/redis-$REDIS_VERSION"
REDIS_DATA="$REDIS_PREFIX/data"
REDIS_PID="$REDIS_PREFIX/redis.pid"
PREBUILT_REDIS_SRC="/tmp/redis-$REDIS_VERSION"

log() {
  printf '\n==> %s\n' "$1"
}

die() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

if [[ ! -f .env ]]; then
  die ".env is missing. It must define DATABASE_URL and REDIS_URL."
fi

if [[ ! -x "$PG_BIN/psql" ]]; then
  die "Postgres.app was not found. Install it from https://postgresapp.com/downloads and move Postgres.app to /Applications."
fi
export PATH="$PG_BIN:$PATH"

log "Checking Postgres.app on localhost:5432"
if ! pg_isready -h localhost -p 5432 -q; then
  open -a Postgres
  ready=0
  for _ in $(seq 1 30); do
    if pg_isready -h localhost -p 5432 -q; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "$ready" -ne 1 ]]; then
    die "Postgres is not accepting connections. Open Postgres.app and start the server, then rerun ./setup.sh."
  fi
fi

log "Creating role '${DB_USER}' and database '${DB_NAME}' if they do not exist"
role_exists="$(psql -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | tr -d '[:space:]')"
if [[ "$role_exists" != "1" ]]; then
  createuser -s "$DB_USER"
fi
psql -d postgres -c "ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';"

db_exists="$(psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | tr -d '[:space:]')"
if [[ "$db_exists" != "1" ]]; then
  createdb -O "$DB_USER" "$DB_NAME"
fi

log "Installing Redis ${REDIS_VERSION} under .services/redis if needed"
if [[ ! -x "$REDIS_PREFIX/bin/redis-server" ]]; then
  mkdir -p "$ROOT/.services/src"
  if [[ -d "$PREBUILT_REDIS_SRC" ]]; then
    make -C "$PREBUILT_REDIS_SRC" install PREFIX="$REDIS_PREFIX"
  else
    curl -fsSL -o "$ROOT/.services/src/redis.tar.gz" \
      "https://download.redis.io/releases/redis-${REDIS_VERSION}.tar.gz"
    tar -xzf "$ROOT/.services/src/redis.tar.gz" -C "$ROOT/.services/src"
    make -C "$REDIS_SRC" -j4
    make -C "$REDIS_SRC" install PREFIX="$REDIS_PREFIX"
  fi
fi

mkdir -p "$REDIS_DATA"
redis_managed=0
if [[ -f "$REDIS_PID" ]] && kill -0 "$(cat "$REDIS_PID")" 2>/dev/null; then
  redis_managed=1
fi
if [[ "$redis_managed" -ne 1 ]]; then
  if "$REDIS_PREFIX/bin/redis-cli" -h localhost -p 6379 ping 2>/dev/null | grep -q PONG; then
    log "Stopping the Redis already running on port 6379"
    "$REDIS_PREFIX/bin/redis-cli" -h localhost -p 6379 shutdown nosave || true
    for _ in $(seq 1 20); do
      if ! "$REDIS_PREFIX/bin/redis-cli" -h localhost -p 6379 ping >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
  fi
  log "Starting Redis"
  "$REDIS_PREFIX/bin/redis-server" \
    --daemonize yes \
    --bind 127.0.0.1 \
    --port 6379 \
    --dir "$REDIS_DATA" \
    --dbfilename dump.rdb \
    --pidfile "$REDIS_PID" \
    --protected-mode yes
fi

log "Waiting for Redis on localhost:6379"
redis_ready=0
for _ in $(seq 1 30); do
  if "$REDIS_PREFIX/bin/redis-cli" -h localhost -p 6379 ping 2>/dev/null | grep -q PONG; then
    redis_ready=1
    break
  fi
  sleep 1
done
if [[ "$redis_ready" -ne 1 ]]; then
  die "Redis did not respond to PING on localhost:6379"
fi

log "Activating the project virtualenv"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

if [[ -s requirements.txt ]]; then
  log "Installing Python dependencies"
  python -m pip install -r requirements.txt
fi

if ! python -c "import psycopg" >/dev/null 2>&1; then
  log "Installing psycopg with bundled libpq"
  python -m pip install "psycopg[binary]"
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  log "Installing uvicorn"
  python -m pip install uvicorn
fi

if ! python -c "import alembic, sqlalchemy, psycopg" >/dev/null 2>&1; then
  die "alembic, sqlalchemy, and psycopg must be installed in .venv"
fi

log "Generating a migration if alembic/versions is empty"
shopt -s nullglob
migrations=(alembic/versions/*.py)
if (( ${#migrations[@]} == 0 )); then
  alembic revision --autogenerate -m "initial tables"
else
  printf 'Migrations already exist (%s). Skipping autogenerate.\n' "${#migrations[@]}"
fi

log "Applying migrations"
alembic upgrade head

log "Done"
printf 'Postgres: localhost:5432  database=%s  user=%s\n' "$DB_NAME" "$DB_USER"
printf 'Redis:    localhost:6379  data=%s\n' "$REDIS_DATA"
printf 'Start the app with: ./runserver.sh\n'
```

Set `DB_NAME` at the top of the script to the same name used in `.env` and `docker-compose.yml`. `chmod +x setup.sh`, then:

```bash
./setup.sh
./runserver.sh
```

The script creates the `postgres` role and the database, starts Redis, installs dependencies, and applies migrations. With an empty `app/models/__init__.py`, the first autogenerate revision has no tables. That is expected.

## Run the server

`runserver.sh`:

```bash
#!/usr/bin/env bash
# Start the FastAPI app on http://localhost:8000
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  printf 'error: .venv is missing. Run ./setup.sh first.\n' >&2
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if ! command -v uvicorn >/dev/null 2>&1; then
  printf 'error: uvicorn is not installed in .venv. Run ./setup.sh first.\n' >&2
  exit 1
fi

exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`chmod +x runserver.sh`. The app listens on `http://127.0.0.1:8000`.

## Reset local data

`flush_services.sh` drops `DB_NAME` in Postgres.app and deletes the Redis data directory created by `setup.sh`. Postgres.app stays running. Migration files stay on disk.

```bash
#!/usr/bin/env bash
#   ./flush_services.sh          asks for confirmation
#   ./flush_services.sh --yes    skips the prompt
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PG_BIN="/Applications/Postgres.app/Contents/Versions/latest/bin"
DB_NAME="DB_NAME"
REDIS_PREFIX="$ROOT/.services/redis"
REDIS_DATA="$REDIS_PREFIX/data"
REDIS_PID="$REDIS_PREFIX/redis.pid"
ASSUME_YES=0

if [[ "${1:-}" == "--yes" ]]; then
  ASSUME_YES=1
elif [[ $# -gt 0 ]]; then
  printf 'usage: ./flush_services.sh [--yes]\n' >&2
  exit 1
fi

log() {
  printf '\n==> %s\n' "$1"
}

die() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

printf 'This removes local data for this project.\n'
printf '  Postgres database: %s\n' "$DB_NAME"
printf '  Redis data:        %s\n' "$REDIS_DATA"
printf 'Postgres.app stays running. Migration files are kept.\n'

if [[ "$ASSUME_YES" -ne 1 ]]; then
  read -r -p "Type 'flush' to continue: " answer
  [[ "$answer" == "flush" ]] || die "Aborted."
fi

if [[ -x "$PG_BIN/psql" ]]; then
  export PATH="$PG_BIN:$PATH"
  if pg_isready -h localhost -p 5432 -q; then
    log "Dropping database ${DB_NAME}"
    psql -d postgres -v ON_ERROR_STOP=1 -c \
      "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();"
    dropdb --if-exists "$DB_NAME"
  else
    log "Postgres.app is not running. Skipping the database drop."
  fi
else
  log "Postgres.app was not found. Skipping the database drop."
fi

REDIS_CLI=""
if [[ -x "$REDIS_PREFIX/bin/redis-cli" ]]; then
  REDIS_CLI="$REDIS_PREFIX/bin/redis-cli"
fi

if [[ -n "$REDIS_CLI" ]] && "$REDIS_CLI" -h localhost -p 6379 ping >/dev/null 2>&1; then
  log "Stopping Redis"
  "$REDIS_CLI" -h localhost -p 6379 shutdown nosave || true
  stopped=0
  for _ in $(seq 1 20); do
    if ! "$REDIS_CLI" -h localhost -p 6379 ping >/dev/null 2>&1; then
      stopped=1
      break
    fi
    sleep 1
  done
  if [[ "$stopped" -ne 1 ]]; then
    die "Redis is still running on localhost:6379. Data was not deleted."
  fi
elif [[ -f "$REDIS_PID" ]] && kill -0 "$(cat "$REDIS_PID")" 2>/dev/null; then
  log "Stopping Redis from its pid file"
  kill "$(cat "$REDIS_PID")" || true
else
  log "Redis is not running."
fi

if [[ -d "$REDIS_DATA" ]]; then
  log "Removing Redis data"
  rm -rf "$REDIS_DATA"
fi
rm -f "$REDIS_PID"

log "Done"
printf 'Run ./setup.sh to recreate the database and start Redis.\n'
```

`chmod +x flush_services.sh`. Run `./setup.sh` afterward to recreate the database and start Redis.

## Tests

```bash
source .venv/bin/activate
pytest
```

An empty `tests/` directory is enough until there are tests to run.
