#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi



LINK_DIR="/usr/bin/hddmon"
SRC_DIR="/etc/hddmon"

#install python packages
pip3 install --force-reinstall --ignore-installed pySMART pyudev urwid additional_urwid_widgets proc

#put all of the contents that make us a utility in /etc/hddmon/
mkdir $SRC_DIR
cp -r ./ $SRC_DIR

#make links in /usr/bin to executables in /etc/hddmon 
ln $SRC_DIR/hddmon.py /usr/bin/hddmon

#put systemd file in its place
cp ./hddmon-daemon.service /lib/systemd/system

systemctl daemon-reload
systemctl enable hddmon-daemon
systemctl start hddmon-daemon
sleep 1
systemctl status hddmon-daemon

