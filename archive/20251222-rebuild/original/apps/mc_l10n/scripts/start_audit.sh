#!/bin/bash

echo "========================================"
echo "  MC L10n Database Audit Tool"
echo "========================================"
echo ""

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo "Working directory: $(pwd)"
echo ""

echo "Starting database audit server..."
poetry run python scripts/db_audit.py