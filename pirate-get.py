#!/usr/bin/env python
import webbrowser
import urllib
import urllib2
import sys
import re

if(len(sys.argv) == 1):
    print "usage: pirate-get <search query>"
    exit()
q = sys.argv[1]
f = urllib2.urlopen('http://thepiratebay.se/search/' + q.replace(" ", "+") + '/0/7/0')

mag = re.findall(""""(magnet\:\?xt=[^"]*)""", f.read())

if mag:
    for m in range(len(mag)):
        name = re.search("dn=([^\&]*)", mag[m])
        print str(m) + ".", urllib.unquote(name.group(1).encode('ascii')).decode('utf-8').replace("+", " ")
    l = raw_input("Select a link: ")
    webbrowser.open(mag[int(l)])
else:
    print "no results"
