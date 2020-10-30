#!/usr/bin/python3.8
import os, sys
os.chdir('/etc/hddmon')
sys.path.append('/etc/hddmon')
import subprocess
import multiprocessing.connection as ipc
import re
import urwid as ui
import additional_urwid_widgets as ui_special
import time
import threading
from hddmondtools.hddmon_dataclasses import HddData, TaskData, TaskQueueData

