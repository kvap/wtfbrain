#!/usr/bin/env python3

# -----------------------------------------------------------------------------
# We wrote this file. As long as you retain this notice you can do whatever you
# want with this stuff. If we meet some day, and you think this stuff is worth
# it, you can buy each of us a bottle of cider in return.
#
#    Constantin S. Pan <kvapen@gmail.com>
#    Ildus Kurbangaliev <i.kurbangaliev@gmail.com>
#    2015-2017
# -----------------------------------------------------------------------------

import pyudev
import subprocess
import time
import logging
import os
import yaml

from os.path import expanduser

import sway

def is_sway_session():
    session = os.getenv('XDG_SESSION_TYPE')
    desktop = os.getenv('XDG_SESSION_DESKTOP')
    return session == 'wayland' and desktop == 'sway'

def get_config():
    config_home = os.getenv('XDG_CONFIG_HOME')
    if config_home:
        filename = os.path.join(config_home, "wtfbrain", "config.yaml")
    else:
        filename = expanduser(os.path.join("~", ".wtfbrain.yaml"))
    with open(filename) as f:
        config = yaml.load(f)
    return config

# FIXME: send notifications directry via dbus
def notify(summary, body, timeout):
    if timeout > 0:
        args = [
            'notify-send', summary, body,
            '-t', str(int(timeout * 1000)),
        ]
        subprocess.check_call(args)

def get_output_basename_number(output):
    return output['name'].rsplit("-", 1)

def get_output_signature(output):
    basename, number = get_output_basename_number(output)
    return '{basename}={make}:{model}:{serial}'.format(basename=basename, **output)

def get_outputs_signature(outputs):
    subsignatures = [get_output_signature(o) for o in outputs]
    signature = ','.join(sorted(subsignatures))
    return signature

def set_sway_outputs(ipc, display_config):
    _, outputs = ipc.msg('get_outputs')
    signature = get_outputs_signature(outputs)

    for mode, outputs_config in display_config.items():
        if ",".join(sorted(outputs_config.keys())) == signature:
            logging.debug("display mode: %s", mode)

            commands = []
            for o in outputs:
                basename, number = get_output_basename_number(o)
                sig = get_output_signature(o)
                output_config = outputs_config[sig]
                command = 'output ' + o['name']
                if output_config == 'disable':
                    command += ' disable'
                else:
                    command += ' enable'
                    for key, value in output_config.items():
                        command += ' ' + key + ' ' + str(value)
                commands.append(command)
            request = ', '.join(commands)
            logging.debug("request = %s", request)
            _, response = ipc.msg('command', request.encode())
            if not response[0]['success']:
                logging.error("sway ipc error: %s", response[0]['error'])

            return True, mode

    logging.debug("no display mode matched signature %s", signature)
    return False, signature

def main():
    logging.root.setLevel('DEBUG')

    if not is_sway_session():
        print("your desktop does not use Sway, wtfbrain is only compatible with Sway environment")
        os.exit(1)

    try:
        swayipc = sway.IPC()
    except sway.SwayNotFound:
        print("sway socket not found, wtfbrain is only compatible with Sway environment")
        os.exit(1)

    config = get_config()

    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)

    display_config = config.get('display')

    if display_config:
        monitor.filter_by(subsystem='drm')
        set_sway_outputs(swayipc, display_config)

    while True:
        try:
            for action, device in monitor:
                if action == 'change' and device.subsystem == 'drm' and display_config:
                    print(action, device)
                    time.sleep(2)
                    ok, mode = set_sway_outputs(swayipc, display_config)
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

        except KeyboardInterrupt:
            logging.debug("dying")
            return
        except Exception as e:
            logging.error("exception", exc_info=1)

if __name__ == '__main__':
    main()
