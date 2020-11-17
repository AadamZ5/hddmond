#!/bin/bash

docker build . -f docker/client/dockerfile --tag registry.repairpc.localdomain/hddmon-client:latest && docker push registry.repairpc.localdomain/hddmon-client:latest
docker build . -f docker/daemon/dockerfile --tag registry.repairpc.localdomain/hddmond:latest && docker push registry.repairpc.localdomain/hddmond:latest

echo "Done"

