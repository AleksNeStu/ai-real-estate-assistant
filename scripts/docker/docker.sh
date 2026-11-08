#!/bin/bash
# Docker mode launcher for AI Real Estate Assistant
# Forces Docker mode and runs the application in containers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Help support
show_help() {
    cat << EOF
Usage: docker.sh [options]

Docker mode launcher for AI Real Estate Assistant.
Runs the application in Docker containers.

Options:
  --help, -h        Show this help message
  --dry-run         Show commands without executing
  --docker-mode     auto | cpu | gpu | ask (default: auto)
  --internet        Enable web search (SearXNG)

Docker Profiles:
  (default)         External AI only
  local-llm         + Ollama CPU
  local-llm + gpu   + Ollama GPU
  internet          + SearXNG web search

Examples:
  ./scripts/docker/docker.sh                      # Docker with auto GPU detection
  ./scripts/docker/docker.sh --docker-mode cpu    # CPU-only mode
  ./scripts/docker/docker.sh --docker-mode gpu    # GPU mode
  ./scripts/docker/docker.sh --internet           # With web search

For full options, run: python3 scripts/start.py --help
EOF
    exit 0
}

# Check for help flag
for arg in "$@"; do
    if [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
        show_help
    fi
done

echo "Starting AI Real Estate Assistant in Docker mode..."
echo "Project root: $PROJECT_ROOT"

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed or not on PATH."
    echo "Please install Python 3.11+ from https://python.org"
    exit 1
fi

# Run the launcher script with Docker mode
python3 "$PROJECT_ROOT/scripts/start.py" --mode docker "$@"
