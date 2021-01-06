#!/bin/bash

docker build . -f docker/client/dockerfile --tag hddmon-client:latest
docker build . -f docker/daemon/dockerfile --tag hddmond:latest

echo "Done"

