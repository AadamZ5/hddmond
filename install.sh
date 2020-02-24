#!/bin/bash



if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

echo Trying to stop any existing service...
systemctl stop hddmon-daemon

LINK_DIR="/usr/bin/hddmon"
SRC_DIR="/etc/hddmon"

#install python packages
echo Installing python packages...
python3.8 -m pip install --force-reinstall --ignore-installed git+https://github.com/AadamZ5/py-SMART.git@pickling-fixes pyudev urwid additional_urwid_widgets git+https://github.com/AadamZ5/python-proc.git@dev graphqlclient websockets dataclasses

#put all of the contents that make us a utility in /etc/hddmon/
echo Copying files...
mkdir $SRC_DIR
cp -r ./ $SRC_DIR

#make links in /usr/bin to executables in /etc/hddmon 
echo Making links...
ln $SRC_DIR/hddmon.py /usr/bin/hddmon

#put systemd file in its place
echo Copying service file...
cp ./hddmon-daemon.service /lib/systemd/system

echo Reloading systemctl daemon list...
systemctl daemon-reload
echo Enabling hddmon-daemon service...
systemctl enable hddmon-daemon
echo Starting hddmon-daemon service...
systemctl start hddmon-daemon
sleep 1
systemctl status hddmon-daemon
echo All done!
