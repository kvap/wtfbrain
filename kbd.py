#!/usr/bin/python3

# -----------------------------------------------------------------------------
# We wrote this file. As long as you retain this notice you can do whatever you
# want with this stuff. If we meet some day, and you think this stuff is worth
# it, you can buy us a bottle of cider in return.
#
#	Constantin S. Pan <kvapen@gmail.com>
#	Ildus Kurbangaliev <i.kurbangaliev@gmail.com>
#	2016
# -----------------------------------------------------------------------------

import pyudev
import shlex
import subprocess
import time
import json

from datetime import datetime
from dateutil.tz import tzlocal
from os.path import expanduser


context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by(subsystem='input')
monitor.filter_by(subsystem='block')


def uniq_keyboard(device):
	return device.get('ID_INPUT_KEYBOARD') == '1' and device.get('UNIQ') == '""'


def isotime():
	return datetime.now(tzlocal()).strftime("%F %T %Z")


def get_config():
	filename = expanduser("~/.wtfbrain.json")
	with open(filename) as f:
		config = json.load(f)
	return config


def notify(summary, body, timeout):
	args = [
		'notify-send', summary, body,
		'-t', str(timeout * 1000),
	]
	subprocess.check_call(args)


def get_mount_source(device):
	if device.get('ID_BUS').upper() == 'USB':
		# standart flash drives
		if device.device_type == 'partition':
			return device.device_path

		# flash players
		if device.device_type == 'disk' and device.get('ID_FS_TYPE'):
			return device['DEVLINKS'].split()[0]


def mount(block):
	args = [
		'udisksctl', 'mount', '--block-device',
		block, '--no-user-interaction'
	]
	subprocess.check_call(args)


def set_xkbmap(xkbmap):
	try:
		args = ['setxkbmap']
		for k, v in xkbmap.items():
			args.append("-" + k)
			args.append(v)
		cmd = ' '.join(shlex.quote(x) for x in args)
		print(cmd)
		subprocess.check_call(args)
		print('xkbmap set')
		return True
	except subprocess.CalledProcessError:
		print('command failed: ' + cmd)
		return False


def set_rate(rate):
	try:
		first_delay, delay = rate
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


def main():
	config = get_config()

	set_rate(config['rate'])
	set_xkbmap(config['xkbmap'])

	while True:
		try:
			for action, device in monitor:
				if action == 'add' and uniq_keyboard(device):
					notify(
						'A keyboard attached',
						'{0}:{1}'.format(
							device.get('ID_VENDOR', 'no-vendor'),
							device.get('ID_MODEL', 'no-model'),
						) + '\nReconfiguring xkbmap and rate',
						2,
					)
					print("[{0}] {1}:{2} {3}'".format(
						isotime(),
						device.get('ID_VENDOR', 'no-vendor'),
						device.get('ID_MODEL', 'no-model'),
						device.sys_path,
					))
					time.sleep(2)
					set_rate(config['rate'])
					set_xkbmap(config['xkbmap'])

				if action == 'add' and device.subsystem == 'block':
					mount_source = get_mount_source(device)
					if mount_source:
						mount(mount_source)

		except KeyboardInterrupt:
			print("dying")
			return
		except:
			print("Recovering from interruption")


if __name__ == '__main__':
	main()
