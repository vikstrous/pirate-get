#!/usr/bin/env python
from __future__ import print_function
import __builtin__
import webbrowser
import urllib
import urllib2
import re
import os
import ConfigParser
import string
import random
from HTMLParser import HTMLParser
import argparse
from pprint import pprint
from StringIO import StringIO
import gzip

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

    # new ConfigParser
    config = ConfigParser.ConfigParser()

    # default options so we dont die later
    config.add_section('SaveToFile')
    config.set('SaveToFile', 'enabled', False)
    config.set('SaveToFile', 'directory', '~/Dropbox/pirate-get/')

    # load user options, to override default ones
    config.read([os.path.expanduser('~/.config/pirate-get/pirate.cfg')])

    parser = argparse.ArgumentParser(description='Finds and downloads torrents from the Pirate Bay')
    parser.add_argument('search', metavar='search', nargs="*", help="Term to search for")
    parser.add_argument('-c', dest='category', metavar='category', help="Specify a category to search", default="All")
    parser.add_argument('-R', dest='recent',  action='store_true', help="Torrents uploaded in the last 48hours. *ignored in searches*", default=False)
    parser.add_argument('-l', dest='list_categories',  action='store_true', help="List categories", default=False)
    parser.add_argument('-t',dest='transmission',action='store_true', help="call transmission-remote to start the download", default=False)
    parser.add_argument('--custom',dest='command', help="call custom command, %%s will be replaced with the url")
    parser.add_argument('--local', dest='database', help="An xml file containing the Pirate Bay database")
    parser.add_argument('-p', dest='pages', help="The number of pages to fetch (doesn't work with --local)", default=1)
    parser.add_argument('-0', dest='first', action='store_true', help="choose the top result", default=False)
    parser.add_argument('--color', dest='color', action='store_true', help="use colored output", default=False)

    categories = {"All":"0","Audio":"100","Audio/Music":"101","Audio/Audio books":"102","Audio/Sound clips":"103","Audio/FLAC":"104","Audio/Other":"199","Video":"200","Video/Movies":"201","Video/Movies DVDR":"202","Video/Music videos":"203","Video/Movie clips":"204","Video/TV shows":"205","Video/Handheld":"206","Video/HD - Movies":"207","Video/HD - TV shows":"208","Video/3D":"209","Video/Other":"299","Applications":"300","Applications/Windows":"301","Applications/Mac":"302","Applications/UNIX":"303","Applications/Handheld":"304","Applications/IOS (iPad/iPhone)":"305","Applications/Android":"306","Applications/Other OS":"399","Games":"400","Games/PC":"401","Games/Mac":"402","Games/PSx":"403","Games/XBOX360":"404","Games/Wii":"405","Games/Handheld":"406","Games/IOS (iPad/iPhone)":"407","Games/Android":"408","Games/Other":"499","Porn":"500","Porn/Movies":"501","Porn/Movies DVDR":"502","Porn/Pictures":"503","Porn/Games":"504","Porn/HD - Movies":"505","Porn/Movie clips":"506","Porn/Other":"599","Other":"600","Other/E-books":"601","Other/Comics":"602","Other/Pictures":"603","Other/Covers":"604","Other/Physibles":"605","Other/Other":"699"}

    #todo: redo this with html parser instead of regex
    def remote(args, mirror):
        res_l = []
        try:
            pages = int(args.pages)
            if pages < 1:
                raise Exception('')
        except Exception:
            raise Exception("Please provide an integer greater than 0 for the number of pages to fetch.")

        if str(args.category) in categories.values():
            category = args.category;
        elif args.category in categories.keys():
            category = categories[args.category]
        else:
            category = "0";
            print ("Invalid category ignored", color="WARN")

        # Catch the Ctrl-C exception and exit cleanly
        try:
            sizes = []
            uploaded = []
            for page in xrange(pages):

                #
                if len(args.search) == 0:
                    path = "/top/48h" if args.recent else "/top/"
                    if(category == "0"):
                        path += 'all'
                    else:
                        path += category
                else:
                    path = '/search/' + "+".join(args.search) + '/' + str(page) + '/7/' + category

                request = urllib2.Request(mirror + path)
                request.add_header('Accept-encoding', 'gzip')
                f = urllib2.urlopen(request)
                if f.info().get('Content-Encoding') == 'gzip':
                    buf = StringIO(f.read())
                    f = gzip.GzipFile(fileobj=buf)
                res = f.read()
                found = re.findall(""""(magnet\:\?xt=[^"]*)|<td align="right">([^<]+)</td>""", res)

                # check for a blocked mirror
                no_results = re.search(""""No hits\.""", res)
                if found == [] and not no_results is None:
                    # Contradiction - we found no results, but the page didn't say there were no results
                    # the page is probably not actually the pirate bay, so let's try another mirror
                    raise Exception("Blocked mirror detected.")

                # get sizes as well and substitute the &nbsp; character
                # print res
                sizes.extend([match.replace("&nbsp;", " ") for match in re.findall("(?<=Size )[0-9.]+\&nbsp\;[KMGT]*[i ]*B",res)])
                uploaded.extend([match.replace("&nbsp;", " ") for match in re.findall("(?<=Uploaded ).+(?=\, Size)",res)])
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
            print("\nCancelled.")
            exit()

        # return the sizes in a spearate list
        return res_l, sizes, uploaded

    args = parser.parse_args()

    def make_print():
        if(args.color):
            import colorama
            colorama.init()
            color_dict = {"default": "",
            "header": colorama.Back.WHITE + colorama.Fore.BLACK,
            "zebra_0": "",
            "zebra_1": colorama.Style.DIM,
            "WARN": colorama.Fore.YELLOW,
            "ERROR": colorama.Fore.RED}
            def n_print(*args, **kwargs):
                """Print with colors"""
                try:
                    c = color_dict[kwargs.pop("color")]
                    args = (c + str(args[0]),) + args[1:] + (colorama.Style.RESET_ALL,)
                except KeyError as e:
                    pass
                except IndexError as e:
                    pass
                return __builtin__.print(*args, **kwargs)
        else:
            def n_print(*args, **kwargs):
                if("color" in kwargs):
                    kwargs.pop('color')
                return __builtin__.print(*args, **kwargs)
        return n_print

    print=make_print()

    def local(args):
        xml_str = ''
        with open(args.database, 'r') as f:
            xml_str += f.read()
        htmlparser = MyHTMLParser(args.q)
        htmlparser.feed(xml_str)
        return htmlparser.results


    if args.list_categories:

        cur_color = "zebra_0"
        for key, value in sorted(categories.iteritems()) :

            cur_color = "zebra_0" if (cur_color == "zebra_1") else "zebra_1"
            print(str(value) +"\t" + key, color=cur_color)

        return
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
            print("Could not fetch additional mirrors", color="WARN")
        for mirror in mirrors:
            try:
                print("Trying " + mirror)
                mags, sizes, uploaded = remote(args, mirror)
                break
            except Exception, e:
                print(format(e))
                print("Could not contact " + mirror, color="WARN")

    if not mags or len(mags) == 0:
        print("no results")
        return
    # enhanced print output with column titles
    print("%5s %6s %6s %-5s %-11s %-11s  %s" \
        % ( "LINK", "SEED", "LEECH", "RATIO", "SIZE", "UPLOAD", "NAME"),
        color="header")
    cur_color = "zebra_0"
    for m in range(len(mags)):
        magnet = mags[m]
        no_seeders = int(magnet[1])
        no_leechers = int(magnet[2])
        name = re.search("dn=([^\&]*)", magnet[0])

        # compute the S/L ratio (Higher is better)
        try:
            ratio = no_seeders/no_leechers
        except ZeroDivisionError:
            ratio = -1

        # Alternate between colors
        cur_color = "zebra_0" if (cur_color == "zebra_1") else "zebra_1"

        torrent_name = urllib.unquote(name.group(1).encode('ascii')) \
            .decode('utf-8').replace("+", " ")
        # enhanced print output with justified columns
        print ("%5d %6d %6d %5.1f %-11s %-11s  %s" % (
            m, no_seeders, no_leechers, ratio ,sizes[m],
            uploaded[m], torrent_name), color=cur_color)

    if args.first:
        print("Choosing first result");
        choices = [0]
    else:
        try:
            l = raw_input("Select link(s): ")
        except KeyboardInterrupt :
            print("\nCancelled.")
            exit()

        try:
            # Very permissive handling
            # Substitute multiple consecutive spaces or commas for single comma
            l = re.sub("[ ,]+", ",", l)
            # Remove anything that isn't an integer or comma.
            l = re.sub("[^0-9,]", "", l)
            # Turn into list
            choices = l.split(",")
        except Exception:
            choices = ()

    if config.get('SaveToFile', 'enabled'):
        # Save to file is enabled
        fileName = os.path.expanduser(config.get('SaveToFile', 'directory')) + id_generator() + '.magnet'
        print ("Saving to File: " + fileName)
        f = open(fileName, 'w')
        for choice in choices:
            choice = int(choice)
            url = mags[choice][0]
            f.write(url + '\n')

        f.close()

    else:
        # use transmission as default
        for choice in choices:
            choice = int(choice)
            url = mags[choice][0]
            print(url)
            if args.transmission:
                os.system("""transmission-remote --add "%s" """ % (url))
                os.system("transmission-remote -l")
            elif args.command:
 		          os.system(args.command % (url))
            else:
                webbrowser.open(url)

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

if __name__ == "__main__":
    main()
