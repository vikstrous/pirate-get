#!/usr/bin/env python
import webbrowser
import urllib
import urllib2
import re
from HTMLParser import HTMLParser
import argparse


# create a subclass and override the handler methods
class MyHTMLParser(HTMLParser):
    title = ''
    q = ''
    state = 'looking'
    results = []

    def __init__(self, q):
        HTMLParser.__init__(self)
        self.q = q.lower()

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.state = 'title'
        if tag == 'magnet' and self.state == 'matched':
            self.state = 'magnet'

    def handle_data(self, data):
        if self.state == 'title':
            if data.lower().find(self.q) != -1:
                self.title = data
                self.state = 'matched'
            else:
                self.state = 'looking'
        if self.state == 'magnet':
            self.results.append('magnet:?xt=urn:btih:' + urllib.quote(data) + '&dn=' + urllib.quote(self.title))
            self.state = 'looking'


def main():

    parser = argparse.ArgumentParser(description='Finds and downloads torrents from the Pirate Bay')

    def local(args):
        xml_str = ''
        with open(args.database, 'r') as f:
            xml_str += f.read()
        htmlparser = MyHTMLParser(args.q)
        htmlparser.feed(xml_str)
        return htmlparser.results

    def remote(args):
        f = urllib2.urlopen('http://thepiratebay.se/search/' + args.q.replace(" ", "+") + '/0/7/0')
        return re.findall(""""(magnet\:\?xt=[^"]*)""", f.read())

    parser.add_argument('q', metavar='search_term', help="The term to search for")
    parser.add_argument('--local', dest='database', help="An xml file containing the Pirate Bay database")

    args = parser.parse_args()
    if args.database:
        mags = local(args)
    else:
        mags = remote(args)

    if mags:
        for m in range(len(mags)):
            name = re.search("dn=([^\&]*)", mags[m])
            print str(m) + ".", urllib.unquote(name.group(1).encode('ascii')).decode('utf-8').replace("+", " ")
        l = raw_input("Select a link: ")
        webbrowser.open(mags[int(l)])
    else:
        print "no results"

if __name__ == "__main__":
    main()
