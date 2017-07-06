# wtfbrain

These daemons will wait for new devices attached and set different things for them.

## what they can do now
  1. Set up `xkbmap` and `rate` for keyboards on plug.
  1. Mount usb storage on plug.
  1. Reconfigure `randr` when you plug/unplug your monitors.
  1. Execute custom commands for usb device on plug

## what we plan to teach them to do
  1. Run custom scripts on events.

## configuration
  1. Copy `.wftbrain.json.example` into `~/.wtfbrain.json`.
  1. Launch `randr.py` to see the list of your currently attached monitors with their signatures.
  1. Change the settings as you wish.
  1. Set "notification" to your preferred timeout in seconds. Zero disables them.

The default configuration doesn't contain keys remapping but `wtfbrain`
supports them. To remap keys you can use `xkb_symbols` syntax. Add block
like this to `keyboard` section:

	"xkb_symbols": {
		"us": [
			"key <BKSP> {[	BackSpace,	Insert	]};",
			"key   <UP> {[	Up,			Prior	]};",
			"key <DOWN> {[	Down,		Next	]};",
		]
	}

## running
  1. Install `pyudev` library.
  1. Launch `brain.py` and have fun.
