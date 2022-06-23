#!/usr/bin/env bash
set -ex
cd $(dirname $0)
docker-compose pull
docker-compose up -d --no-deps django celeryworker
docker system prune -f
