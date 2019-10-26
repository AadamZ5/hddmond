#!/bin/bash
#When this script is called from udev, it will posess udev environment variables which are used here.
nohup /home/azocolo/hdd-test/test-hdd.sh $SERIAL $VARIABLE $SOMETHING &
