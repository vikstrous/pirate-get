#!/usr/bin/env python
#
# Copyright 2014, Viktor Stanchev and contributors
#
# This file is part of pirate-get.
#
# pirate-get is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pirate-get is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with pirate-get.  If not, see <http://www.gnu.org/licenses/>.

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

from bs4 import BeautifulSoup

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
    def config_to_load():
        if os.path.isfile(os.path.expandvars('$XDG_CONFIG_HOME/pirate-get/pirate.cfg')):
            return os.path.expandvars('$XDG_CONFIG_HOME/pirate-get/pirate.cfg')
        else:
            return os.path.expanduser('~/.config/pirate-get/pirate.cfg')

    config.read([config_to_load()])

    parser = argparse.ArgumentParser(description='Finds and downloads torrents from the Pirate Bay')
    parser.add_argument('-b', dest='browse',  action='store_true', help="Display in Browse mode", default=False)
    parser.add_argument('search', metavar='search', nargs="*", help="Term to search for")
    parser.add_argument('-c', dest='category', metavar='category', help="Specify a category to search", default="All")
    parser.add_argument('-s', dest='sort', metavar='sort', help="Specify a sort option", default="seeders.desc")
    parser.add_argument('-R', dest='recent',  action='store_true', help="Torrents uploaded in the last two weeks. *ignored in searches*", default=False)
    parser.add_argument('-l', dest='list_categories',  action='store_true', help="List categories", default=False)
    parser.add_argument('--list_sorts', dest='list_sorts',  action='store_true', help="List Sortable Types", default=False)
    parser.add_argument('-t',dest='transmission',action='store_true', help="call transmission-remote to start the download", default=False)
    parser.add_argument('--custom',dest='command', help="call custom command, %%s will be replaced with the url")
    parser.add_argument('--local', dest='database', help="An xml file containing the Pirate Bay database")
    parser.add_argument('-p', dest='pages', help="The number of pages to fetch (doesn't work with --local)", default=1)
    parser.add_argument('-0', dest='first', action='store_true', help="choose the top result", default=False)
    parser.add_argument('-a', dest='download_all', action='store_true', help="download all results", default=False)
    parser.add_argument('--color', dest='color', action='store_true', help="use colored output", default=False)

    categories = {
        "All":"0",
        "Anime":"1",
        "Software":"2",
        "Games":"3",
        "Adult":"4",
        "Movies":"5",
        "Music":"6",
        "Other":"7",
        "Series & TV":"8",
        "Books":"9",
    }

    sorts = {
        "created_at":"0",
        "created_at.desc":"1",
        "size":"2",
        "size.desc":"3",
        "seeders":"4",
        "seeders.desc":"5",
        "leechers":"6",
        "leechers.desc":"7",
    }
    reverse_sorts = {v: k for k, v in sorts.items()}

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

        if args.sort in sorts.keys():
            sort = args.sort;
        elif args.sort in sorts.values():
            sort = reverse_sorts[args.sort]
        else:
            print ("Invalid sort ignored", color="WARN")

        query_parameters = {
            "iht":"0",
            "age":"0",
            "Torrent_sort":"",
            "LTorrent_page":0,
            "q":"",
        }
        # Catch the Ctrl-C exception and exit cleanly
        try:
            sizes = []
            uploaded = []
            identifiers = []
            OPENBAY_PAGE_LEN = 40
            for page in xrange(pages):

                query_parameters["LTorrent_page"] = page * OPENBAY_PAGE_LEN
                query_parameters["Torrent_sort"] = sort
                query_parameters["iht"] = category
                if len(args.search) == 0:
                    query_parameters["age"] = "14" if args.recent else "0"
                else:
                    query_parameters["q"] = "+".join(args.search)

                path = "/search.php?" + '&'.join(k + "=" + str(v) for k, v in query_parameters.items())

                request = urllib2.Request(mirror + path)
                request.add_header('Accept-encoding', 'gzip')
                f = urllib2.urlopen(request)
                if f.info().get('Content-Encoding') == 'gzip':
                    buf = StringIO(f.read())
                    f = gzip.GzipFile(fileobj=buf)
                res = f.read()

                soup = BeautifulSoup(res)
                found = soup.select('table.table-torrents>tbody>tr')

                results_body = soup.table.tbody

                get_text = lambda elements: [element.get_text() for element in elements]
                get_text_by_class = lambda class_: get_text(results_body.find_all(class_=class_))
                get_links = lambda links: [link.get('href') for link in links]

                sizes.extend(get_text_by_class('size-row'))
                uploaded.extend(get_text_by_class('date-row'))
                identifiers.extend([
                    re.search('torrent/(\d+)', link).group(1)
                    for link in
                    get_links(results_body.find_all('a', href=re.compile('/torrent/')))
                ])
                
                links = get_links(results_body.find_all('a', title='MAGNET LINK'))
                seeders = get_text_by_class('seeders-row')
                leechers = get_text_by_class('leechers-row')
                for i in xrange(len(links)):
                    res_l.append([links[i], seeders[i], leechers[i]])

                if len(links) < OPENBAY_PAGE_LEN:
                    break
        except KeyboardInterrupt :
            print("\nCancelled.")
            exit()

        return res_l, sizes, uploaded, identifiers

    args = parser.parse_args()

    def make_print():
        if(args.color):
            import colorama
            colorama.init()
            color_dict = {"default": "",
            "header": colorama.Back.WHITE + colorama.Fore.BLACK,
            "zebra_0": "",
            "zebra_1": colorama.Style.BRIGHT,
            "WARN": colorama.Fore.YELLOW,
            "ERROR": colorama.Fore.RED}
            def n_print(*args, **kwargs):
                """Print with colors"""
                try:
                    c = color_dict[kwargs.pop("color")]
                    args = (c + str(args[0].encode('utf-8')),) + args[1:] + (colorama.Style.RESET_ALL,)
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

    if args.list_sorts:

        cur_color = "zebra_0"
        for key, value in sorted(sorts.iteritems()) :

            cur_color = "zebra_0" if (cur_color == "zebra_1") else "zebra_1"
            print(str(value) +"\t" + key, color=cur_color)

        return

    if args.database:
        mags = local(args)
    else:
        mirrors = ["https://oldpiratebay.org", "http://thepiratebay.se"]
        try:
            opener = urllib2.build_opener(NoRedirection)
            f = opener.open("https://proxybay.info/list.txt")
            if f.getcode() != 200:
                raise Exception("The pirate bay responded with an error.")
            res = f.read()
            mirrors += res.split("\n")[3:]
        except:
            print("Could not fetch additional mirrors", color="WARN")
        for mirror in mirrors:
            try:
                print("Trying " + mirror)
                mags, sizes, uploaded, identifiers = remote(args, mirror)
                if not mags or len(mags) == 0:
                    print("No results from " + mirror)
                else:
                    break
            except Exception, e:
                print(format(e))
                print("Could not contact " + mirror, color="WARN")

    # enhanced print output with column titles
    def print_search_results():
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
    def print_descriptions(chosen_links):
        for link in chosen_links:
            path = '/torrent/' + identifiers[int(link)] + '/pirate-get'
            request = urllib2.Request(mirror + path)
            request.add_header('Accept-encoding', 'gzip')
            f = urllib2.urlopen(request)
            if f.info().get('Content-Encoding') == 'gzip':
                buf = StringIO(f.read())
                f = gzip.GzipFile(fileobj=buf)
            res = f.read()

            name = re.search("dn=([^\&]*)", mags[int(link)][0])
            torrent_name = urllib.unquote(name.group(1).encode('ascii')) \
                .decode('utf-8').replace("+", " ")

            desc = re.search(r"<div class=\"nfo\">\s*<pre>(.*?)(?=</pre>)", res, re.DOTALL).group(1)
            # Replace HTML links with markdown style versions
            desc = re.sub(r"<a href=\"\s*([^\"]+?)\s*\"[^>]*>(\s*)([^<]+?)(\s*)</a>", r"\2[\3](\1)\4", desc).strip()
            if desc == '':
                print ('No description given for "' + torrent_name + '"', color="zebra_1")
            else:
                print ('Description for "' + torrent_name + '":', color="zebra_1")
                print (desc, color="zebra_0")

    def print_fileLists(chosen_links):
        for link in chosen_links:
            path = '/ajax_details_filelist.php'
            query = '?id=' + identifiers[int(link)]
            request = urllib2.Request(mirror + path + query)
            request.add_header('Accept-encoding', 'gzip')
            f = urllib2.urlopen(request)
            if f.info().get('Content-Encoding') == 'gzip':
                buf = StringIO(f.read())
                f = gzip.GzipFile(fileobj=buf)
            res = f.read().replace("&nbsp;", " ")
            files = re.findall(r"<td align=\"left\">\s*([^<]+?)\s*</td><td align=\"right\">\s*([^<]+?)\s*</tr>", res)
            name = re.search("dn=([^\&]*)", mags[int(link)][0])
            torrent_name = urllib.unquote(name.group(1).encode('ascii')) \
                .decode('utf-8').replace("+", " ")
            print ('Files in "' + torrent_name + '":', color="zebra_1")
            cur_color = "zebra_0"
            for f in files:
                print ("%-11s  %s" % (f[1], f[0]), color=cur_color)
                cur_color = "zebra_0" if (cur_color == "zebra_1") else "zebra_1"

    print_search_results()

    if args.first:
        print("Choosing first result");
        choices = [0]
    elif args.download_all:
        print("Downloading all results");
        choices = range(0, len(mags))
    else:
        # New input loop to support different link options
        while True:
            try:
                l = raw_input("Select link(s) (Type 'h' for more options ['q' to quit]): ")
            except KeyboardInterrupt :
                print("\nCancelled.")
                exit()

            try:
                # Very permissive handling
                # Check for any occurances or d, f, p or q
                cmd_code_match = re.search(r'([hdfpq])', l, flags=re.IGNORECASE)
                if cmd_code_match:
                    code = cmd_code_match.group(0).lower()
                else:
                    code = None
                # Clean up command codes
                l = re.sub(r"^[hdfp, ]*|[hdfp, ]*$", "", l)
                # Substitute multiple consecutive spaces or commas for single comma
                l = re.sub("[ ,]+", ",", l)
                # Remove anything that isn't an integer or comma.
                l = re.sub("[^0-9,]", "", l)
                # Turn into list
                choices = l.split(",")
                # Act on option, if supplied
                if code == 'h':
                    print("Options:")
                    print("<links>: Download selected torrents")
                    print("[d<links>]: Get descriptions")
                    print("[f<links>]: Get files")
                    print("[p] Print search results")
                    print("[q] Quit")
                    continue
                elif code == 'q':
                    print("User Cancelled.")
                    exit()
                elif code == 'd':
                    print_descriptions(choices)
                    continue
                elif code == 'f':
                    print_fileLists(choices)
                    continue
                elif code == 'p':
                    print_search_results()
                    continue
                elif not l:
                    print('No links entered!')
                    continue
                else:
                    break
            except Exception, e:
                print('Exception:')
                print(str(e))
                choices = ()
                break;

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
