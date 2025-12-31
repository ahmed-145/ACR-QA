#!/bin/bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=acrqa
export DB_USER=postgres
export DB_PASSWORD=postgres

python3 CORE/main.py --limit 3
