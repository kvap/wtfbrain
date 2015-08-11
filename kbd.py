#!/usr/bin/python3

import pyudev
from datetime import datetime
from dateutil.tz import tzlocal
from os.path import expanduser
import shlex
import subprocess
import time

context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by(subsystem='input')

def uniq_keyboard(device):
	return device.get('ID_INPUT_KEYBOARD') == '1' and device.get('UNIQ') == '""'

def isotime():
	return datetime.now(tzlocal()).strftime("%F %T %Z")

def get_xkbmap():
	filename = expanduser("~/.Xkbmap")
	with open(filename) as f:
		lines = f.read()
		xkbmap = shlex.split(lines)
	return xkbmap

def set_xkbmap(xkbmap):
	try:
		args = ['setxkbmap'] + xkbmap
		cmd = ' '.join(shlex.quote(x) for x in args)
		print(cmd)
		subprocess.check_call(args)
		print('xkbmap set')
		return True
	except subprocess.CalledProcessError:
		print('command failed: ' + cmd)
		return False

def set_rate(first_delay=200, delay=30):
	try:
		args = [
			'xset', 'r', 'rate',
			str(first_delay),
			str(delay),
		]
		cmd = ' '.join(shlex.quote(x) for x in args)
		print(cmd)
		subprocess.check_call(args)
		print('rate set')
		return True
	except subprocess.CalledProcessError:
		print('command failed: ' + cmd)
		return False

xkbmap = get_xkbmap()
for action, device in monitor:
	if action == 'add' and uniq_keyboard(device):
		print("[{0}] {1}:{2} {3}'".format(
			isotime(),
			device.get('ID_VENDOR', 'no-vendor'),
			device.get('ID_MODEL', 'no-model'),
			device.sys_path,
		))
		time.sleep(2)
		set_rate(200, 30)
		set_xkbmap(xkbmap)
