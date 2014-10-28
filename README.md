# pirate-get

pirate-get is a convenient command line tool (inspired by APT) to speed up your trip to the Pirate Bay and get your completely legal torrents more quickly.

Tested on Arch Linux mostly. It should work on any other Linux too. Let me know if it doesn't. Also tested on OSX (whatever the latest one is - I don't know; I don't use non-free operating systems.) --local option hasn't been tested recently.


## Installation

Make sure you have python 2 installed.

Run install.sh

If you're using Arch Linux there's a package avalaible at the AUR:
https://aur.archlinux.org/packages/pirate-get-git/

## Usage

```
usage: pirate-get.py [-h] [-c category] [-R] [-l] [-t] [--custom COMMAND]
                     [--local DATABASE] [-p PAGES] [-0] [-a] [--color]
                     [search [search ...]]

Finds and downloads torrents from the Pirate Bay

positional arguments:
  search            Term to search for

optional arguments:
  -h, --help        show this help message and exit
  -c category       Specify a category to search
  -R                Torrents uploaded in the last 48hours. *ignored in
                    searches*
  -l                List categories
  -t                call transmission-remote to start the download
  --custom COMMAND  call custom command, %s will be replaced with the url
  --local DATABASE  An xml file containing the Pirate Bay database
  -p PAGES          The number of pages to fetch (doesn't work with --local)
  -0                choose the top result
  -a                download all results
  --color           use colored output
```

## Configuration file

pirate-get will check to see if `$HOME/.config/pirate-get/pirate.cfg` exists. If it does it will use it as its default configuration settings.

### SaveToFile

**Currently this is the only way to save magnet urls to a file**

A config file would look something like:

```INI
[SaveToFile]
enabled = true
directory = ~/Dropbox/pirate-get/
```

## Notes

If you want to use a local copy of the Pirate Bay database download a copy here (or wherever the latest version is currently):

http://thepiratebay.se/torrent/8156416


# License

pirate-get is licensed under the GNU Affero General Public License version 3 or later. See the accompanying file COPYING or http://www.gnu.org/licenses/agpl.html.
