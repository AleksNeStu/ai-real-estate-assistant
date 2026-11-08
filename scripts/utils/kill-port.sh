#!/bin/bash
# Kill processes on specified ports and release port allocations.
#
# Usage:
#   ./kill-port.sh 8000 3800
#   ./kill-port.sh --release 8000
#   ./kill-port.sh --force --all

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "$(dirname "$SCRIPT_DIR")")" && pwd)"

RELEASE=false
FORCE=false
ALL=false
PORTS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --release|-r)
            RELEASE=true
            shift
            ;;
        --force|-f)
            FORCE=true
            shift
            ;;
        --all|-a)
            ALL=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [PORTS...]"
            echo ""
            echo "Options:"
            echo "  -r, --release    Release port allocations from registry"
            echo "  -f, --force      Force kill (SIGKILL instead of SIGTERM)"
            echo "  -a, --all        Kill all services managed by this project"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 8000 3800           Kill processes on ports 8000 and 3800"
            echo "  $0 --release 8000      Kill and release port 8000"
            echo "  $0 --all --force       Force kill all managed services"
            exit 0
            ;;
        *)
            PORTS+=("$1")
            shift
            ;;
    esac
done

# Find PID on port (cross-platform)
find_pid_on_port() {
    local port=$1
    local pids=""

    if command -v lsof &> /dev/null; then
        pids=$(lsof -t -i ":$port" 2>/dev/null || true)
    elif command -v ss &> /dev/null; then
        pids=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' || true)
    elif command -v netstat &> /dev/null; then
        pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 || true)
    fi

    echo "$pids"
}

# Kill process tree
kill_process_tree() {
    local pid=$1
    local signal="TERM"

    if [ "$FORCE" = true ]; then
        signal="KILL"
    fi

    # Get child processes
    local children=$(pgrep -P "$pid" 2>/dev/null || true)

    # Kill children first
    for child in $children; do
        kill_process_tree "$child"
    done

    # Kill the process
    kill -"$signal" "$pid" 2>/dev/null || true
    echo "  Killed process $pid"
}

# Release port allocation
release_port_allocation() {
    local port=$1
    local registry_path="$PROJECT_ROOT/docs/PORT_REGISTRY.json"

    if [ ! -f "$registry_path" ]; then
        return
    fi

    # Use Python to update JSON
    python3 - "$port" "$registry_path" << 'PYEOF'
import json
import sys
from datetime import datetime, timezone

port = int(sys.argv[1])
registry_path = sys.argv[2]

try:
    with open(registry_path, 'r') as f:
        registry = json.load(f)

    updated = False
    for alloc in registry.get('allocations', []):
        if alloc.get('port') == port and alloc.get('status') == 'active':
            alloc['status'] = 'inactive'
            alloc['lastUsedAt'] = datetime.now(timezone.utc).isoformat()
            updated = True

    if updated:
        registry['lastUpdated'] = datetime.now(timezone.utc).isoformat()
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        print(f"  Released port allocation for {port}")
except Exception as e:
    print(f"  Warning: Failed to update registry: {e}", file=sys.stderr)
PYEOF
}

# Get all ports if --all specified
if [ "$ALL" = true ]; then
    registry_path="$PROJECT_ROOT/docs/PORT_REGISTRY.json"
    if [ -f "$registry_path" ]; then
        PORTS=$(python3 -c "
import json
with open('$registry_path') as f:
    r = json.load(f)
print(' '.join(str(a['port']) for a in r.get('allocations', []) if a.get('status') == 'active'))
" 2>/dev/null || echo "")
    else
        echo "Error: Port registry not found at $registry_path" >&2
        exit 1
    fi
fi

# Check if we have ports to process
if [ ${#PORTS[@]} -eq 0 ]; then
    echo "Error: No ports specified. Use PORT arguments or --all" >&2
    exit 1
fi

# Process each port
for port in "${PORTS[@]}"; do
    if ! [[ "$port" =~ ^[0-9]+$ ]]; then
        continue
    fi

    echo "Processing port $port..."

    pids=$(find_pid_on_port "$port")

    if [ -z "$pids" ]; then
        echo "  No process found on port $port"
    else
        pid_count=$(echo "$pids" | wc -l)
        echo "  Found $pid_count process(es) on port $port"
        for pid in $pids; do
            if [ -n "$pid" ]; then
                kill_process_tree "$pid"
            fi
        done
    fi

    if [ "$RELEASE" = true ]; then
        release_port_allocation "$port"
    fi
done

echo ""
echo "Done!"
