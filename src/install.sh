#!/bin/bash



if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

echo Trying to stop any existing service...
systemctl stop hddmond

LINK_DIR="/usr/bin/hddmon"
SRC_DIR="/etc/hddmon"

#Install python3.8
apt install python3.8

#put all of the contents that make us a utility in /etc/hddmon/
echo Copying files...
mkdir $SRC_DIR
cp -r ./ $SRC_DIR

#Install packages
cd $SRC_DIR
python3.8 -m pip install --no-cache -r $SRC_DIR/requirements.txt

#make links in /usr/bin to executables in /etc/hddmon 
echo Making links...
ln $SRC_DIR/hddmon.py /usr/bin/hddmon

#put systemd file in its place
echo Copying service file...
cp ./hddmond.service /lib/systemd/system

echo Reloading systemctl daemon list...
systemctl daemon-reload
echo Enabling hddmond service...
systemctl enable hddmond
echo Starting hddmond service...
systemctl start hddmond
sleep 2
systemctl status hddmond
echo All done!
