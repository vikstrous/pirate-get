#!/usr/bin/env python
import webbrowser
import urllib.request, urllib.parse, urllib.error
import re
from html.parser import HTMLParser
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
            self.results.append(['magnet:?xt=urn:btih:' + urllib.parse.quote(data) + '&dn=' + urllib.parse.quote(self.title), '?', '?'])
            self.state = 'looking'


def main():
    parser = argparse.ArgumentParser(description='Finds and downloads torrents from the Pirate Bay')
    parser.add_argument('q', metavar='search_term', help="The term to search for")
    parser.add_argument('--local', dest='database', help="An xml file containing the Pirate Bay database")
    parser.add_argument('-p', dest='pages', help="The number of pages to fetch (doesn't work with --local)", default=1)

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

        for page in range(pages):
            f = urllib.request.urlopen('http://thepiratebay.se/search/' + args.q.replace(" ", "+") + '/' + str(page) + '/7/0')
            res = f.read()
            found = re.findall(b""""(magnet\:\?xt=[^"]*)|<td align="right">([^<]+)</td>""", res)
            state = "seeds"
            curr = ['',0,0] #magnet, seeds, leeches
            for f in found:
                if f[1] == b'':
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

    if mags and len(mags) > 0:
        print("S=seeders")
        print("L=leechers")
        for m in range(len(mags)):
            magnet = mags[m]
            name = re.search(b"dn=([^\&]*)", magnet[0])
            if name == None:
                name = ''
            else:
                name = urllib.parse.unquote(name.group(1).decode("utf-8")).replace("+", " ")
            print(str(m) + '. S:' + magnet[1].decode("utf-8") + ' L:' + magnet[2].decode("utf-8") + ' ', name)
        l = input("Select a link: ")
        try:
            choice = int(l)
        except Exception:
            choice = None
        if not choice == None:
            webbrowser.open(mags[choice][0])
        else:
            print("Cancelled.")
    else:
        print("no results")

if __name__ == "__main__":
    main()
