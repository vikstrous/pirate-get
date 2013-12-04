#!/usr/bin/env python
import webbrowser
import urllib
import urllib2
import re
from HTMLParser import HTMLParser
import argparse
import os 


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
            self.results.append(['magnet:?xt=urn:btih:' + urllib.quote(data) + '&dn=' + urllib.quote(self.title), '?', '?'])
            self.state = 'looking'


def main():
    parser = argparse.ArgumentParser(description='Finds and downloads torrents from the Pirate Bay')
    parser.add_argument('q', metavar='search_term', help="The term to search for")
    parser.add_argument('-d', dest='transmission', help="Should add to transmission", default=False)
    parser.add_argument('--download',dest='transmission',action='store_true', help="call transmission-remote to start the download", default=True)
    parser.add_argument('--auto',dest='auto',action='store_true', help="auto select the url to download", default=False)
    parser.add_argument('--local', dest='database', help="An xml file containing the Pirate Bay database")
    parser.add_argument('-p', dest='pages', help="The number of pages to fetch (doesn't work with --local)", default=1)

    def compare(a,b):
        return -1 * cmp(a['s'], b['s'])
    def local(args):
        xml_str = ''
        with open(args.database, 'r') as f:
            xml_str += f.read()
        htmlparser = MyHTMLParser(args.q)
        htmlparser.feed(xml_str)
        return htmlparser.results

    #todo: redo this with html parser instead of regex
    def remote(args):
        res_l = []
        try:
            pages = int(args.pages)
            if pages < 1:
                raise Exception('')
        except Exception:
            raise Exception("Please provide an integer greater than 0 for the number of pages to fetch.")

        for page in xrange(pages):
            f = urllib2.urlopen('http://thepiratebay.se/search/' + args.q.replace(" ", "+") + '/' + str(page) + '/7/0')
            res = f.read()
            found = re.findall(""""(magnet\:\?xt=[^"]*)|<td align="right">([^<]+)</td>""", res)
            state = "seeds"
            curr = ['',0,0] #magnet, seeds, leeches
            for f in found:
                if f[1] == '':
                    curr[0] = f[0]
                else:
                    if state == 'seeds':
                        curr[1] = f[1]
                        state = 'leeches'
                    else:
                        curr[2] = f[1]
                        state = 'seeds'
                        res_l.append(curr)
                        curr = ['', 0, 0]
        return res_l

    args = parser.parse_args()
    if args.database:
        mags = local(args)
    else:
        mags = remote(args)

    L = []
    if mags and len(mags) > 0:
        print "S=seeders"
        print "L=leechers"
        for m in range(len(mags)):
            magnet = mags[m]
            name = re.search("dn=([^\&]*)", magnet[0])
            d = dict()
            d['i'] = m
            # d['u'] = magnet[0]
            d['s'] = (int(magnet[1]) + int(magnet[2])) 
            L.append(d)
            print str(m) + '. S:' + str(magnet[1]) + ' L:' + str(magnet[2]) + ' ', urllib.unquote(name.group(1).encode('ascii')).decode('utf-8').replace("+", " ")
        L.sort(compare)
        if not args.auto: 
          l = raw_input("Select a link: ")
          try:
              choice = int(l)
          except Exception:
              choice = None
        else: 
          try:
              choice = int(L[0]['i'])
          except Exception:
              choice = None
        url = mags[choice][0]

        if not choice == None:
            print ""
            print "url:"
            print url
            c = """transmission-remote --add "%s" """ % (url)
            if args.transmission: 
                os.system(c)
                os.system("transmission-remote -l")
        else:
            print "Cancelled."
    else:
        print "no results"

if __name__ == "__main__":
    main()
