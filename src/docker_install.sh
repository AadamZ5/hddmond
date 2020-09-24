#!/bin/bash
#This script is meant to be used inside of official docker python:3.8-slim
apt-get update
apt-get install -y git pciutils smartmontools
pip install -r requirements.txt
python ./hddmond.py
