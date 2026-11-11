#!/usr/bin/env bash
# The local multi-arch build for the 5.3.2 release.
#
# The GitHub publish workflow builds the same images on its own runners; this
# is the fallback for when that pool wedges again, and the verification that
# the image builds at all before a tag is cut.
set -euo pipefail

REPO=ghcr.io/aleksnestu/ai-real-estate-assistant
VERSION=5.3.2
SHA=$(git rev-parse HEAD)
SHORT=${SHA:0:7}
SITE_URL=https://realty.kittray.com
PLATFORMS=linux/amd64,linux/arm64

LABELS=(
  --label "org.opencontainers.image.revision=$SHA"
  --label "org.opencontainers.image.version=$VERSION"
  --label "org.opencontainers.image.created=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  --label "org.opencontainers.image.source=https://github.com/AleksNeStu/ai-real-estate-assistant"
)

echo "==> backend $VERSION ($PLATFORMS) at $SHORT"
docker buildx build \
  --builder desktop-linux \
  --platform "$PLATFORMS" \
  --file deploy/docker/Dockerfile.backend \
  --tag "$REPO/backend:$VERSION" \
  --tag "$REPO/backend:$SHORT" \
  "${LABELS[@]}" \
  --push \
  .

echo "==> frontend $VERSION ($PLATFORMS) at $SHORT"
docker buildx build \
  --builder desktop-linux \
  --platform "$PLATFORMS" \
  --file deploy/docker/Dockerfile.frontend \
  --build-arg "NEXT_PUBLIC_SITE_URL=$SITE_URL" \
  --tag "$REPO/frontend:$VERSION" \
  --tag "$REPO/frontend:$SHORT" \
  "${LABELS[@]}" \
  --push \
  .

echo "==> published"
docker buildx imagetools inspect "$REPO/backend:$VERSION" | head -12
docker buildx imagetools inspect "$REPO/frontend:$VERSION" | head -12
