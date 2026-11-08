#!/bin/bash
# Auto-detect mode launcher for AI Real Estate Assistant
# Detects Docker availability and runs in appropriate mode

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Help support
show_help() {
    cat << EOF
Usage: run.sh [options]

Auto-detect mode launcher for AI Real Estate Assistant.
Detects Docker availability and runs in appropriate mode.

Options:
  --help, -h        Show this help message
  --dry-run         Show commands without executing
  --no-bootstrap    Skip dependency installation
  --mode            auto | docker | local (default: auto)
  --service         all | backend | frontend (default: all)
  --backend-port    Backend port (default: 8000)
  --frontend-port   Frontend port (default: 3000)

Examples:
  ./scripts/dev/run.sh                        # Auto-detect mode
  ./scripts/dev/run.sh --mode local           # Force local mode
  ./scripts/dev/run.sh --service backend      # Backend only
  ./scripts/dev/run.sh --dry-run              # Show commands

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

echo "Starting AI Real Estate Assistant..."
echo "Project root: $PROJECT_ROOT"

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed or not on PATH."
    echo "Please install Python 3.11+ from https://python.org"
    exit 1
fi

# Run the launcher script with sensible defaults
python3 "$PROJECT_ROOT/scripts/start.py" "$@"
