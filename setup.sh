#!/bin/bash

DIRECTORY="/usr/bin/hddmon"

#install python packages
pip3 install pySMART pyudev urwid

#put all of the contents that make us a utility in /usr/bin/hddmon/
cp ./auto-hdd-test.py $DIRECTORY/hddmon.py
cp ./hdd.py $DIRECTORY
cp ./ahcidetection.py $DIRECTORY
cp ./pciaddress.py $DIRECTORY
cp ./sasdetection.py $DIRECTORY
cp ./portdetection.py $DIRECTORY
cp -r ./sas2ircu $DIRECTORY

#put systemd file in its place
cp ./hddmon-daemon.service /lib/systemd/system

systemctl daemon-reload
systemctl enable hddmon-daemon
systemctl start hddmon-daemon
systemctl status hddmon-daemon

