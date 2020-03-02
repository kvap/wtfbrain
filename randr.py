#!/usr/bin/env python3
import subprocess


def get_outputs():
	outputs = {}
	oname = None
	state = 'none'
	for line in subprocess.check_output(["xrandr", "--prop"]).decode().splitlines()[1:]:
		if line.startswith(' '):
			# ignore
			continue

		if not line.startswith(' ') and not line.startswith('\t'):
			state = 'output'
			oname, status, rest = line.split(' ', 2)
			if oname not in outputs:
				outputs[oname] = {
					'name': oname,
					'status': status,
					'edid': bytes(),
				}
			continue

		if state == 'edid':
			if line.startswith('\t\t'):
				outputs[oname]['edid'] += bytes.fromhex(line.strip())
				continue
			else:
				state = 'output'
				continue
		elif state == 'output':
			if line.startswith('\tEDID:'):
				state = 'edid'
				continue
	return outputs


def parse_edid(edid):
	name = None
	serial = None
	text = None
	for descr in edid[54:72],edid[72:90],edid[90:108],edid[108:126]:
		if descr[:3] == b'\x00\x00\x00':
			if descr[3] == 0xff: # serial
				serial = descr[5:].decode(errors='ignore').strip()
			elif descr[3] == 0xfe: # text
				text = descr[5:].decode(errors='ignore').strip()
			elif descr[3] == 0xfc: # name
				name = descr[5:].decode(errors='ignore').strip()

	return name, serial, text


def unnonify(*args):
        return list(filter(None, args))

def output_id(info):
	name, serial, text = parse_edid(info['edid'])
	return ":".join(unnonify(name, serial, text)).replace(' ','-')

def get_signature(outputs):
        return [(name, output_id(info)) for (name, info) in outputs.items() if info['status'] == 'connected']

def match(config, signature):
    if len(config) != len(signature):
        return None

    result = []
    for (candidate, settings), (output_name, output_id) in zip(config.items(), signature):
        if "=" in candidate:
            name, id = candidate.split("=", 1)
        else:
            name, id = None, candidate

        if name and name != output_name or id != output_id:
            return None

        result.append((output_name, settings))

    return result

def main():
	for name, info in sorted(get_outputs().items()):
		if info['status'] != 'connected':
			continue
		print("%s=%s" % (name, output_id(info)))

if __name__ == '__main__':
	main()
