#!/bin/bash

docker build . -f docker/client/dockerfile --tag hddmon-client
docker build . -f docker/daemon/dockerfile --tag hddmond

echo "Build 'hddmond' and 'hddmon-client' images."