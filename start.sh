#!/bin/bash

#from https://github.com/TeamLinux01/scripts/blob/master/dc_up.sh

DOCKER_COMPOSE_VERSION="$(< `dirname $0`/docker-compose.version)"

echo Running docker-compose...
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "${PWD}":"${PWD}" -w "${PWD}" \
  docker/compose:$DOCKER_COMPOSE_VERSION up -d --build