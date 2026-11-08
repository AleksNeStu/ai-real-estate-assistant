#!/bin/bash
# Convenience script for starting Docker containers for the AI Real Estate Assistant
# This is a wrapper around docker compose with the correct compose file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
COMPOSE_FILE="$PROJECT_ROOT/deploy/compose/docker-compose.yml"

echo "Starting AI Real Estate Assistant with Docker..."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not on PATH."
    echo "Please install Docker Desktop from https://docker.com"
    exit 1
fi

echo "Using compose file: $COMPOSE_FILE"
echo ""

# Run docker compose with the correct compose file
docker compose -f "$COMPOSE_FILE" up --build
