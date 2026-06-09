#!/bin/bash
set -e

WORKSPACE_DIR="/home/ahmeed/Documents/KSIU/GRAD/SOLO"
PGDATA="$WORKSPACE_DIR/tempy/pgdata"
PGBIN="/usr/lib/postgresql/18/bin"

# Check if PostgreSQL 18 bin exists, fallback to 14 if needed
if [ ! -d "$PGBIN" ]; then
    PGBIN="/usr/lib/postgresql/14/bin"
fi

if [ ! -d "$PGBIN" ]; then
    echo "Error: PostgreSQL binary directory not found."
    exit 1
fi

if [ ! -d "$PGDATA" ]; then
    echo "Initializing PostgreSQL database cluster..."
    mkdir -p "$PGDATA"
    "$PGBIN/initdb" -D "$PGDATA"

    # Configure postgresql.conf
    echo "listen_addresses = '127.0.0.1'" >> "$PGDATA/postgresql.conf"
    echo "port = 5434" >> "$PGDATA/postgresql.conf"
    echo "unix_socket_directories = '$PGDATA'" >> "$PGDATA/postgresql.conf"
fi

# Check if postgres is already running
if "$PGBIN/pg_isready" -h localhost -p 5434 >/dev/null 2>&1; then
    echo "PostgreSQL is already running on port 5434."
else
    echo "Starting PostgreSQL on port 5434..."
    "$PGBIN/pg_ctl" -D "$PGDATA" -l "$PGDATA/logfile" start
    # Wait for server to start up
    for i in {1..10}; do
        if "$PGBIN/pg_isready" -h localhost -p 5434 >/dev/null 2>&1; then
            echo "PostgreSQL started successfully."
            break
        fi
        sleep 1
    done
fi

# Verify connection
if ! "$PGBIN/pg_isready" -h localhost -p 5434 >/dev/null 2>&1; then
    echo "Error: PostgreSQL did not start or is not responding on port 5434."
    exit 1
fi

# Create postgres superuser role if it doesn't exist
if ! "$PGBIN/psql" -h localhost -p 5434 -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='postgres'" | grep -q 1; then
    echo "Creating 'postgres' superuser role..."
    "$PGBIN/createuser" -h localhost -p 5434 -s postgres
fi

# Set password for postgres user
echo "Setting password for 'postgres' user..."
"$PGBIN/psql" -h localhost -p 5434 -d postgres -c "ALTER USER postgres WITH PASSWORD 'AhmedAbbass@1';"

# Create database 'acrqa' owned by postgres if it doesn't exist
if ! "$PGBIN/psql" -h localhost -p 5434 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='acrqa'" | grep -q 1; then
    echo "Creating database 'acrqa'..."
    "$PGBIN/createdb" -h localhost -p 5434 -O postgres acrqa
else
    echo "Database 'acrqa' already exists."
fi


# Run Alembic migrations from repo root
echo "Running database migrations..."
cd "$WORKSPACE_DIR"
if [ -f .env ]; then
    echo "Loading .env file..."
    export $(grep -v '^#' .env | xargs)
fi
.venv/bin/alembic upgrade head

echo "PostgreSQL setup completed successfully."
