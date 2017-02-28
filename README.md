# pirate-get
[![Circle CI](https://img.shields.io/circleci/project/vikstrous/pirate-get/master.svg)](https://circleci.com/gh/vikstrous/pirate-get/tree/master) [![Coverage Status](https://img.shields.io/coveralls/vikstrous/pirate-get/master.svg)](https://coveralls.io/github/vikstrous/pirate-get?branch=master) [![Code Climate](https://img.shields.io/codeclimate/github/vikstrous/pirate-get.svg)](https://codeclimate.com/github/vikstrous/pirate-get) [![Codacy Badge](https://api.codacy.com/project/badge/8e5fc16afd23496dbcf74db710d1ef2c)](https://www.codacy.com/app/me_29/pirate-get) [![Gemnasium](https://img.shields.io/gemnasium/vikstrous/pirate-get.svg)](https://gemnasium.com/vikstrous/pirate-get)  [![License](https://img.shields.io/pypi/l/pirate-get.svg)](https://raw.githubusercontent.com/vikstrous/pirate-get/master/LICENSE) [![Version](https://img.shields.io/pypi/v/pirate-get.svg)](https://pypi.python.org/pypi/pirate-get/) [![Downloads](https://img.shields.io/pypi/dm/pirate-get.svg)](https://pypi.python.org/pypi/pirate-get/)

pirate-get is a convenient command line tool (inspired by APT) to speed up your trip to the Pirate Bay and get your completely legal torrents more quickly.

## Installation
Make sure you have python 3.4 and pip installed. On Ubuntu 14.04 you may also need to install the libxslt1-dev and libxml2-dev packages.

Run `pip3 install pirate-get`

## Usage

To search use `pirate-get [search term]`.

See `pirate-get -h` for more options.

Watch [this](http://showterm.io/d6f7a0c2a5de1da9ea317) for an example usage.


## Configuration file
You can use a file to override pirate-get's default settings.  
Default is `$XDG_CONFIG_HOME/pirate-get`.
If it does not exist then `$HOME/.config/pirate-get`.

### Default config file
Here the available options and their behaviors are when unset:

```INI
[Save]
; directory where to save files
directory = $PWD

; save each selected magnet link in a .magnet file
magnets = false

; save each selected torrent in a .torrent file
torrents = false                     

[LocalDB]
; use a local copy of the pirate bay database
enabled = false                 

; path of the database     
path = ~/downloads/pirate-get/db

[Misc]
; specify a custom command for opening the magnet
; ex. myprogram --open %s
; %s represent the magnet uri
openCommand = 

; open magnets with transmission-remote client
transmission = false

; use colored output
colors = true

; the pirate bay mirror(s) to use:
; one or more space separated URLs
mirror = http://thepiratebay.org
```

Note:  
Any command line option will override its respective setting in the config file.  


## Local Database
If you want to use a local copy of the Pirate Bay database download a copy here (or wherever the latest version is currently):

http://thepiratebay.se/torrent/8156416

## License
pirate-get is licensed under the GNU Affero General Public License version 3 or later.  
See the accompanying file LICENSE or http://www.gnu.org/licenses/agpl.html.
