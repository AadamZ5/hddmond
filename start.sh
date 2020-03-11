#!/bin/bash

#stemmed from https://github.com/TeamLinux01/scripts/blob/master/dc_up.sh

DOCKER_COMPOSE_VERSION="$(< `dirname $0`/docker-compose.version)"

# if [ -z $(docker network ls | grep $BRIDGE_NAME) ] 
# then
#   echo "Creating docker bridge $BRIDGE_NAME"
#   docker network create hddmond
# else
#   echo "Docker bridge $BRIDGE_NAME already exists."
#   echo "Skipping bridge creation..."
# fi
echo Running docker-compose...
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "${PWD}":"${PWD}" -w "${PWD}" \
  docker/compose:$DOCKER_COMPOSE_VERSION up -d --build