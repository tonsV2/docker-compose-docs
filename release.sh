#!/usr/bin/env bash

VERSION=$(yq '.project.version' pyproject.toml)
IMAGE_BASE=$(yq '.services.app.image' docker-compose.yml | sed 's/:latest$//')

docker compose build
docker tag "$IMAGE_BASE":latest "$IMAGE_BASE:$VERSION"
docker push "$IMAGE_BASE:latest"
docker push "$IMAGE_BASE:$VERSION"
