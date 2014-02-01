#!/usr/bin/env python
import webbrowser
import urllib
import urllib2
import re
import os
from HTMLParser import HTMLParser
import argparse
from pprint import pprint

class NoRedirection(urllib2.HTTPErrorProcessor):

    def http_response(self, request, response):
        return response

    https_response = http_response

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
    parser.add_argument('-t',dest='transmission',action='store_true', help="call transmission-remote to start the download", default=False)
    parser.add_argument('--local', dest='database', help="An xml file containing the Pirate Bay database")
    parser.add_argument('-p', dest='pages', help="The number of pages to fetch (doesn't work with --local)", default=1)
    parser.add_argument('-0', dest='first', action='store_true', help="choose the top result", default=False)

    def local(args):
        xml_str = ''
        with open(args.database, 'r') as f:
            xml_str += f.read()
        htmlparser = MyHTMLParser(args.q)
        htmlparser.feed(xml_str)
        return htmlparser.results

    #todo: redo this with html parser instead of regex
    def remote(args, mirror):
        res_l = []
        try:
            pages = int(args.pages)
            if pages < 1:
                raise Exception('')
        except Exception:
            raise Exception("Please provide an integer greater than 0 for the number of pages to fetch.")

        # Catch the Ctrl-C exception and exit cleanly
        try:
            for page in xrange(pages):
                f = urllib2.urlopen(mirror + '/search/' + args.q.replace(" ", "+") + '/' + str(page) + '/7/0')
                res = f.read()
                found = re.findall(""""(magnet\:\?xt=[^"]*)|<td align="right">([^<]+)</td>""", res)

                # get sizes as well and substitute the &nbsp; character
                # print res
                sizes = [ match.replace("&nbsp;", " ") for match in re.findall("(?<=Size )[0-9.]+\&nbsp\;[KMGT]*[i ]*B",res) ]
                uploaded = [ match.replace("&nbsp;", " ") for match in re.findall("(?<=Uploaded ).+(?=\, Size)",res) ]
                # pprint(sizes); print len(sizes)
                # pprint(uploaded); print len(uploaded)
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
        except KeyboardInterrupt :
            print "\nCancelled."
            exit()

        # return the sizes in a spearate list
        return res_l, sizes, uploaded

    args = parser.parse_args()
    if args.database:
        mags = local(args)
    else:
        mirrors = ["http://thepiratebay.se"]
        try:
            opener = urllib2.build_opener(NoRedirection)
            f = opener.open("http://proxybay.info/list.txt")
            if f.getcode() != 200:
                raise Exception("The pirate bay responded with an error.")
            res = f.read()
            mirrors += res.split("\n")[3:]
        except:
            print "Could not fetch additional mirrors"
        for mirror in mirrors:
            try:
                print("Trying " + mirror)
                mags, sizes, uploaded = remote(args, mirror)
                break
            except Exception, e:
                print("Could not contact " + mirror)

    if mags and len(mags) > 0:
        # enhanced print output with column titles
        print "\n%-5s %-6s %-6s %-5s %-11s %-11s  %s" % ( "LINK", "SEED", "LEECH", "RATIO", "SIZE", "UPLOAD", "NAME")
        for m in range(len(mags)):
            magnet = mags[m]
            name = re.search("dn=([^\&]*)", magnet[0])

            # compute the S/L ratio (Higher is better)
            try:
                ratio = float(magnet[1])/float(magnet[2])
            except ZeroDivisionError:
                ratio = 0

            # enhanced print output with justified columns
            print "%-5s %-6s %-6s %5.1f %-11s %-11s  %s" % (m, magnet[1], magnet[2], ratio ,sizes[m], uploaded[m],urllib.unquote(name.group(1).encode('ascii')).decode('utf-8').replace("+", " ") )

        if args.first:
            print "Choosing first result";
            choice = 0

        else:
            try:
                l = raw_input("Select a link: ")
            except KeyboardInterrupt :
                print "\nCancelled."
                exit()

            try:
                choice = int(l)
            except Exception:
                choice = None

        if not choice == None:
            url = mags[choice][0]
            print
            print "url:"
            print url
            if args.transmission: 
                os.system("""transmission-remote --add "%s" """ % (url))
                os.system("transmission-remote -l")
            else:
                webbrowser.open(url)
        else:
            print "Cancelled."
    else:
        print "no results"

if __name__ == "__main__":
    main()
