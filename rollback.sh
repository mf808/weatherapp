#!/usr/bin/env bash
# Roll the running weather container to a specific published image tag.
#
# Usage:
#   ./rollback.sh v1.4.0     # pin and deploy that exact version
#   ./rollback.sh latest     # return to the auto-updating latest tag
#
# Run this on the NAS, from the directory holding the compose file.
# Browse available tags at: https://github.com/mf808/weatherapp/pkgs/container/weatherapp
set -euo pipefail

IMAGE="ghcr.io/mf808/weatherapp"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yaml}"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <tag>   (e.g. v1.4.0, or 'latest')"
  echo "Currently pinned to: $(grep -oE "${IMAGE}:[^\"' ]+" "$COMPOSE_FILE" || echo 'unknown')"
  echo "Tags: https://github.com/mf808/weatherapp/pkgs/container/weatherapp"
  exit 1
fi

TAG="$1"
sed -i.bak -E "s|(image: ${IMAGE}):[^\"' ]+|\1:${TAG}|" "$COMPOSE_FILE"
docker compose -f "$COMPOSE_FILE" pull weather
docker compose -f "$COMPOSE_FILE" up -d weather
echo "weather is now running ${IMAGE}:${TAG}"
echo "(previous compose saved as ${COMPOSE_FILE}.bak)"
