#!/usr/bin/env python3

# -----------------------------------------------------------------------------
# We wrote this file. As long as you retain this notice you can do whatever you
# want with this stuff. If we meet some day, and you think this stuff is worth
# it, you can buy each of us a bottle of cider in return.
#
#	Constantin S. Pan <kvapen@gmail.com>
#	Ildus Kurbangaliev <i.kurbangaliev@gmail.com>
#	2015-2017
# -----------------------------------------------------------------------------

import pyudev
import shlex
import subprocess
import time
import json
import logging
import randr
import os
import shutil
import tempfile

from datetime import datetime
from dateutil.tz import tzlocal
from os.path import expanduser


context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by(subsystem='input')
monitor.filter_by(subsystem='block')
monitor.filter_by(subsystem='drm')
monitor.filter_by(subsystem='usb')


def uniq_keyboard(device):
	return device.get('ID_INPUT_KEYBOARD') == '1' and 'LIBINPUT_DEVICE_GROUP' in device

def isotime():
	return datetime.now(tzlocal()).strftime("%F %T %Z")


def get_config():
	filename = expanduser("~/.wtfbrain.json")
	with open(filename) as f:
		config = json.load(f, strict=False)
	return config


def notify(summary, body, timeout):
	if timeout > 0:
		args = [
			'notify-send', summary, body,
			'-t', str(int(timeout * 1000)),
		]
		subprocess.check_call(args)


def get_context(device):
	return {key: value for key, value in device.items()}


def get_fs_info(device):
	if device.get('ID_FS_USAGE') == 'filesystem':
		label = device.get('ID_FS_LABEL', 'unlabeled')
		fs = device.get('ID_FS_TYPE')
		devname = device.get('DEVNAME')
		return (label, fs, devname)


def mount(block):
	try:
		args = [
			'udisksctl', 'mount', '--block-device',
			block, '--no-user-interaction'
		]
		cmd = ' '.join(shlex.quote(x) for x in args)
		print(cmd)
		subprocess.check_call(args)
		return True
	except subprocess.CalledProcessError:
		print('command failed: ' + cmd)
		return False


def setup_xkb(xkbmap, xkb_symbols):
	tmpdir = tempfile.mkdtemp()
	symbols_dir = os.path.join(tmpdir, 'symbols')
	os.mkdir(symbols_dir)

	try:
		ftmp = tempfile.NamedTemporaryFile(dir=symbols_dir, mode='w', delete=False)
		if xkb_symbols:
			for k, v in xkb_symbols.items():
				ftmp.write('''xkb_symbols "%s_extra" {
		%s
	};'''% (k, "\n\t".join(v)))
		ftmp.close()

		args = ['setxkbmap']
		for k, v in xkbmap.items():
			if xkb_symbols and k == 'layout':
				layouts = v.split(',')
				for layout in layouts:
					if layout in xkb_symbols:
						v = v.replace(layout, '{0}+{1}({0}_extra)'
								.format(layout, os.path.basename(ftmp.name)))

			if k == 'option':
				# clear any previous config
				args.append("-option")
				args.append('')

			args.append("-" + k)
			args.append(v)

		if xkb_symbols:
			args.append('-print')
			cmd = ' '.join(shlex.quote(x) for x in args)
			p1 = subprocess.Popen(args, stdout=subprocess.PIPE)

			args = ["xkbcomp",
				"-I%s/.." % os.path.dirname(ftmp.name),
				"-",
				":0"]
			cmd += ' | ' + ' '.join(shlex.quote(x) for x in args)
			p2 = subprocess.Popen(args, stdin=p1.stdout)
			p1.stdout.close()
			out, err = p2.communicate()
		else:
			subprocess.check_call(args)
			cmd = ' '.join(shlex.quote(x) for x in args)

		print(cmd)
		print('xkb is up')
	except subprocess.CalledProcessError:
		print("xkb setup failed")
		return False
	finally:
		shutil.rmtree(tmpdir)

	return True


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


def set_randr(outputs, cfg):
	try:
		args = ['xrandr']
		cfgmap = dict(cfg)
		for name, info in outputs.items():
			args.append('--output')
			args.append(name)
			if name in cfgmap:
				args.extend(shlex.split(cfgmap[name]))
			else:
				args.append('--off')

		cmd = ' '.join(shlex.quote(x) for x in args)
		print(cmd)
		subprocess.check_call(args)
		print('xrandr succeeded')
		return True
	except subprocess.CalledProcessError:
		print('command failed: ' + cmd)
		return False


def rerandr(display):
	outputs = randr.get_outputs()
	signature = randr.get_signature(outputs)

	for name, cfg in display.items():
            matched_cfg = randr.match(cfg, signature)
            if matched_cfg:
                print("display mode: %s" % name)

                set_randr(outputs, matched_cfg)

                return True, name

	print("no display mode matched signature %s" % signature)
	return False, signature


def main():
	config = get_config()

	keyboard = config.get('keyboard')
	display = config.get('display')
	usb_devices = config.get('usb')

	if keyboard:
		set_rate(keyboard['rate'])
		setup_xkb(keyboard['xkbmap'], keyboard.get('xkb_symbols'))

	if display:
		rerandr(display)

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
						config.get('notification', 0),
					)
					print("[{0}] {1}:{2} {3}'".format(
						isotime(),
						device.get('ID_VENDOR', 'no-vendor'),
						device.get('ID_MODEL', 'no-model'),
						device.sys_path,
					))
					time.sleep(2)
					if keyboard:
						set_rate(keyboard['rate'])
						setup_xkb(keyboard['xkbmap'], keyboard.get('xkb_symbols'))

				if action == 'add' and device.subsystem == 'block':
					fsinfo = get_fs_info(device)
					if fsinfo:
						(label, fs, devname) = fsinfo
						notify('New usb device', '''A filesystem attached
							{0} ({1}) at {2}\n
							Mounting.'''.format(label, fs, devname),
							config.get('notification', 0))

						print("[{0}] {1}:{2} at {3}'".format(
							isotime(),
							device.get('ID_VENDOR', 'no-vendor'),
							device.get('ID_MODEL', 'no-model'),
							device.get('DEVPATH'),
						))
						mount(devname)

				if action == 'change' and device.subsystem == 'drm':
					if display:
						time.sleep(2)
						ok, mode = rerandr(display)
						if ok:
							notify(
								'display configuration restored',
								mode,
								config.get('notification', 0),
							)
						else:
							notify(
								'Unknown display configuration',
								mode,
								config.get('notification', 0),
							)

				if action == 'add' and device.subsystem == 'usb':
					context = get_context(device)
					parts = device['PRODUCT'].split('/')
					part1 = parts[0].zfill(4)
					part2 = parts[1].zfill(4)
					product_id = '%s:%s' % (part1, part2)
					product_name = '%s %s' % (device.get('ID_VENDOR_FROM_DATABASE', ''),
						device.get('ID_MODEL_FROM_DATABASE', ''))

					print('usb: %s' % product_name)

					if usb_devices and product_id in usb_devices:
						conf = usb_devices[product_id]
						actions = conf.get('actions')
						if actions:
							for name, cmd in actions:
								try:
									cmd = cmd % context
								except KeyError:
									# print("'%s' command can't be completed with %s" % (cmd, context))
									continue

								subprocess.run(cmd, shell=True,
									stdin=None, stdout=None, stderr=None, close_fds=True)
								print('usb:cmd', cmd)

								notify(
									'USB device command',
									"'%s' command executed for %s" % (name, product_id),
									config.get('notification', 0),
								)

		except KeyboardInterrupt:
			print("dying")
			return
		except Exception as e:
			logging.error("Exception is occured", exc_info=1)


if __name__ == '__main__':
	main()
