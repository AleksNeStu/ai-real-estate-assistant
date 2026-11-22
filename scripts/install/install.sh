#!/bin/sh
# One command from nothing to a running demo.
#
# The README quick start is eight lines: clone, copy the .env, make the data
# directories, bring the compose stack up, wait. This script is those eight
# lines, with the two things a person gets wrong handled for them - the
# secrets in the .env are generated rather than left as placeholders, and the
# script waits for the health check instead of telling you to.
#
# It needs Docker and Git, and it needs no API key: the stack starts in demo
# mode and the assistant answers with the built-in demo model until you put a
# provider key in the .env.
#
# It is reachable before the repository is cloned:
#
#   curl -fsSL https://raw.githubusercontent.com/AleksNeStu/ai-real-estate-assistant/main/scripts/install/install.sh | sh
#
# Optional environment variables:
#   AIRE_HOME       where the checkout goes (default: ./ai-real-estate-assistant)
#   AIRE_TIMEOUT    seconds to wait for the health check (default: 300)
#
set -eu

REPO_URL="https://github.com/AleksNeStu/ai-real-estate-assistant.git"
REPO_NAME="ai-real-estate-assistant"
TARGET_DIR="${AIRE_HOME:-$PWD/$REPO_NAME}"
TIMEOUT="${AIRE_TIMEOUT:-300}"
COMPOSE_FILE="deploy/compose/docker-compose.yml"
ENV_FILE="deploy/compose/.env"
ENV_EXAMPLE="deploy/compose/.env.example"
DATA_DIRS="chroma_db data/audit .preferences .notifications .sessions"

log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info() { printf '    %s\n' "$*"; }
die() {
    printf '\n\033[31mInstallation failed: %s\033[0m\n\n' "$*" >&2
    printf 'To finish it by hand, from the checkout:\n' >&2
    printf '  cd %s\n' "$TARGET_DIR" >&2
    printf '  cp %s %s      # only if the .env is missing\n' "$ENV_EXAMPLE" "$ENV_FILE" >&2
    printf '  mkdir -p deploy/compose/{chroma_db,data/audit,.preferences,.notifications,.sessions}\n' >&2
    printf '  docker compose -f %s up --build -d\n' "$COMPOSE_FILE" >&2
    exit 1
}

need() {
    command -v "$1" >/dev/null 2>&1 || die "$1 is required and was not found on the PATH."
}

random_hex() {
    # 32 hex characters, from the tools that are actually present.
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 16
    elif [ -r /dev/urandom ]; then
        od -An -tx1 -N16 /dev/urandom | tr -d ' \n'
    else
        die "No source of randomness found (openssl or /dev/urandom)."
    fi
}

log "Checking the tools"
need docker
need git
if ! docker info >/dev/null 2>&1; then
    die "Docker is installed but not running. Start Docker Desktop (or the daemon) and run this again."
fi
info "docker $(docker --version | head -n1)"

# ---------------------------------------------------------------- the checkout
log "Preparing the checkout"
if [ -d "$TARGET_DIR/.git" ]; then
    info "reusing $TARGET_DIR"
elif [ -e "$TARGET_DIR" ]; then
    die "$TARGET_DIR exists and is not a checkout. Move it aside, or set AIRE_HOME to another directory."
else
    info "cloning into $TARGET_DIR"
    git clone --depth 1 "$REPO_URL" "$TARGET_DIR" || die "the clone failed - check the network and try again."
fi
cd "$TARGET_DIR"
[ -f "$COMPOSE_FILE" ] || die "$COMPOSE_FILE is missing from the checkout."

# -------------------------------------------------------------------- the .env
log "Preparing the environment file"
if [ -f "$ENV_FILE" ]; then
    BACKUP="$ENV_FILE.backup-$(date +%Y%m%d%H%M%S)"
    cp "$ENV_FILE" "$BACKUP"
    info "an .env already existed - it was kept, and a copy is at $BACKUP"
else
    [ -f "$ENV_EXAMPLE" ] || die "$ENV_EXAMPLE is missing from the checkout."
    # Written to a temporary file and moved into place, so an interrupted run
    # never leaves a half-written .env behind.
    TMP_ENV="$ENV_FILE.tmp.$$"
    cp "$ENV_EXAMPLE" "$TMP_ENV"

    API_KEY="$(random_hex)"
    PG_PASSWORD="$(random_hex)"
    JWT_SECRET="$(random_hex)"
    SEARXNG_SECRET="$(random_hex)"
    # The placeholders in the example are literal - a stack started with them
    # would carry a public secret and a public database password. The JWT one
    # is commented out in the example; it is filled in anyway, so uncommenting
    # the line does not expose a published secret.
    sed -i.bak \
        -e "s|^API_ACCESS_KEY=.*|API_ACCESS_KEY=$API_KEY|" \
        -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$PG_PASSWORD|" \
        -e "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://sprav_dev:$PG_PASSWORD@postgres:5432/realestate_db|" \
        -e "s|^SEARXNG_SECRET=.*|SEARXNG_SECRET=$SEARXNG_SECRET|" \
        -e "s|REPLACE_WITH_SECURE_JWT_SECRET_32_CHARS|$JWT_SECRET|" \
        "$TMP_ENV"
    rm -f "$TMP_ENV.bak"
    # The demo answers with the built-in model, so the stack starts with no
    # provider key at all.
    if ! grep -q '^DEMO_LLM_MODE=' "$TMP_ENV"; then
        printf '\n# Set by the installer: the assistant answers with the built-in demo\n# model, so no provider key is needed. Put a key in MINIMAX_API_KEY and set\n# this to false to use a real model.\nDEMO_LLM_MODE=true\n' >> "$TMP_ENV"
    fi
    mv "$TMP_ENV" "$ENV_FILE"
    info "wrote $ENV_FILE with a generated API key and database password"
fi

# ------------------------------------------------------------- the data dirs
log "Creating the data directories"
for dir in $DATA_DIRS; do
    mkdir -p "deploy/compose/$dir"
done
# The backend runs as uid 999 and writes its state into these directories. On
# Linux Docker creates them as root, so they need write access for that user;
# on macOS and Windows Docker's own permissions already allow it.
if [ "$(uname -s)" = "Linux" ]; then
    chmod -R a+rwX deploy/compose/chroma_db deploy/compose/data/audit \
        deploy/compose/.preferences deploy/compose/.notifications deploy/compose/.sessions 2>/dev/null || true
fi
info "the state directories are in place"

# ---------------------------------------------------------------- the stack
log "Starting the stack (the first build takes a few minutes)"
docker compose -f "$COMPOSE_FILE" up --build -d || die "docker compose failed - the output above says why."

BACKEND_PORT="$(grep -E '^BACKEND_HOST_PORT=' "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '[:space:]')"
FRONTEND_PORT="$(grep -E '^FRONTEND_HOST_PORT=' "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '[:space:]')"
BACKEND_PORT="${BACKEND_PORT:-8082}"
FRONTEND_PORT="${FRONTEND_PORT:-3082}"

log "Waiting for the backend to answer"
ELAPSED=0
while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
    if curl -fsS "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1; then
        break
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    if [ $((ELAPSED % 30)) -eq 0 ]; then
        info "still starting ($ELAPSED s)..."
    fi
done
[ "$ELAPSED" -lt "$TIMEOUT" ] || die "the backend did not answer /health within $TIMEOUT s. Check the logs with: docker compose -f $COMPOSE_FILE logs -f backend"

log "It is running"
printf '\n    Frontend   http://localhost:%s\n' "$FRONTEND_PORT"
printf '    API docs   http://localhost:%s/docs\n' "$BACKEND_PORT"
printf '    Health     http://localhost:%s/health\n\n' "$BACKEND_PORT"
printf '    The assistant answers with the built-in demo model. To use a real one,\n'
printf '    put a provider key in %s and set DEMO_LLM_MODE=false.\n\n' "$ENV_FILE"
printf '    Stop it with: docker compose -f %s down\n\n' "$COMPOSE_FILE"
