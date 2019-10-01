#!/usr/bin/env python3

import socket
import struct
import os
import sys
import json

class SwayNotFound(Exception):
    pass

class IPC:
    def __init__(self, path=''):
        if path == '':
            path = os.getenv('SWAYSOCK')
        self._socket = socket.socket(family=socket.AF_UNIX)
        try:
            self._socket.connect(path)
        except:
            self._socket = None

        if not self._socket:
            raise SwayNotFound

    def _send_request(self, typ, payload):
        typmap = {
            'command': 0,
            'get_workspaces': 1,
            'subscribe': 2,
            'get_outputs': 3,
            'get_tree': 4,
            'get_marks': 5,
            'get_bar_config': 6,
            'get_version': 7,
            'get_binding_modes': 8,
            'get_config': 9,
            'send_tick': 10,
            'get_inputs': 100,
            'get_seats': 101,
        }
        assert(typ in typmap)
        assert(isinstance(payload, bytes))
        header = struct.pack('=6sII', b'i3-ipc', len(payload), typmap[typ])
        self._socket.sendall(header)
        self._socket.sendall(payload)

    def _recv_exactly(self, toread):
        body = bytes()
        while toread > 0:
            chunk = self._socket.recv(toread)
            if len(chunk) == 0:
                raise "cannot read the ipc response"
            body += chunk
            toread -= len(chunk)
        return body

    def _recv_response(self):
        header = self._recv_exactly(14)

        magic, size, typ = struct.unpack('=6sII', header)
        if magic != b'i3-ipc':
            raise "wrong magic in response"
        payload = self._recv_exactly(size)
        return typ, payload

    def msg(self, typ, payload=b''):
        self._send_request(typ, payload)
        typ, raw = self._recv_response()
        return typ, json.loads(raw)

if __name__ == '__main__':
    ipc = IPC()
    typ, outputs = ipc.msg('get_outputs')

    for o in outputs:
        print('{name}={make}:{model}:{serial}'.format(**o))
