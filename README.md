pirate-get
---

pirate-get is a convenient command line tool to speed up your trip to the Pirate Bay and get your completely legal torrents more quickly.

Tested only on Ubuntu. It should work anywhere else too. Let me know if it doesn't.

Installation
---

Make sure you have python installed.

Run install.sh (or install-py3.sh if you use python 3)

Usage
---

```
usage: pirate-get.py [-h] [--local DATABASE] [-p PAGES] search_term

Finds and downloads torrents from the Pirate Bay

positional arguments:
  search_term       The term to search for

optional arguments:
  -h, --help        show this help message and exit
  --local DATABASE  An xml file containing the Pirate Bay database
  -p PAGES          The number of pages to fetch (doesn't work with --local)
```

If you want to use a local copy of the Pirate Bay database download a copy here (or wherever the latest version is currently):

http://thepiratebay.se/torrent/8156416
