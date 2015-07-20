# pirate-get
pirate-get is a convenient command line tool (inspired by APT) to speed up your trip to the Pirate Bay and get your completely legal torrents more quickly.

Tested on Arch Linux mostly. It should work on any other Linux too. Let me know if it doesn't.  
Also tested on OSX (works fine on yosemite)

`--local` option hasn't been tested recently.

## Installation
Make sure you have python 3 installed.
Requires `colorama` for colored output.

Run `./install`

## Usage

To search use `pirate get [search term]`.

See `pirate-get -h` for help.

Watch [this](http://showterm.io/d6f7a0c2a5de1da9ea317) for an example usage.


## Configuration file
You can use a file to override pirate-get's default settings.  
Default is `$XDG_CONFIG_HOME/pirate-get`.
If it does not exist then `$HOME/.config/pirate-get`.

### Default config file
If not existing a new config file will be created when you start
pirate-get. Here the available options and their behaviors are when unset:

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
```

Note:  
Any command line option will override its respective setting in the config file.  


## Notes
If you want to use a local copy of the Pirate Bay database download a copy here (or wherever the latest version is currently):

http://thepiratebay.se/torrent/8156416


## License
pirate-get is licensed under the GNU Affero General Public License version 3 or later.  
See the accompanying file COPYING or http://www.gnu.org/licenses/agpl.html.
