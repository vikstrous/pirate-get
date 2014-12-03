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

import os
import random
import re
import string
import gzip
import configparser
import argparse
import builtins

import webbrowser
import urllib.request as request
import urllib.parse as parse

from html.parser import HTMLParser
from pprint import pprint
from io import StringIO, BytesIO


class NoRedirection(request.HTTPErrorProcessor):
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
            self.results.append([
                'magnet:?xt=urn:btih:' +
                parse.quote(data) +
                '&dn=' +
                parse.quote(self.title), '?', '?'])
            self.state = 'looking'


def main():
    # new ConfigParser
    config = configparser.ConfigParser()

    # default options so we dont die later
    config.add_section('SaveToFile')
    config.set('SaveToFile', 'enabled', 'false')
    config.set('SaveToFile', 'directory', '~/downloads/pirate-get/')

    # load user options, to override default ones
    def config_to_load():
        if os.path.isfile(os.path.expandvars('$XDG_CONFIG_HOME/pirate-get')):
            return os.path.expandvars('$XDG_CONFIG_HOME/pirate-get')
        else:
            return os.path.expanduser('~/.config/pirate-get')

    config.read([config_to_load()])

    parser = argparse.ArgumentParser(
                description='finds and downloads torrents from the Pirate Bay')
    parser.add_argument('-b', dest='browse',
                        action='store_true',
                        help="display in Browse mode")
    parser.add_argument('search', metavar='search',
                        nargs="*", help="term to search for")
    parser.add_argument('-c', dest='category', metavar='category',
                        help="specify a category to search", default="All")
    parser.add_argument('-s', dest='sort', metavar='sort',
                        help="specify a sort option", default="SeedersDsc")
    parser.add_argument('-R', dest='recent',  action='store_true',
                        help="torrents uploaded in the last 48hours."
                                                "*ignored in searches*")
    parser.add_argument('-l', dest='list_categories',
                        action='store_true',
                        help="list categories")
    parser.add_argument('--list_sorts', dest='list_sorts',
                        action='store_true',
                        help="list Sortable Types")
    parser.add_argument('-t', dest='transmission',
                         action='store_true',
                         help="call transmission-remote to start the download")
    parser.add_argument('--custom', dest='command',
                        help="call custom command, %%s will be replaced with"
                                                                    "the url")
    parser.add_argument('--local', dest='database',
                        help="an xml file containing the Pirate Bay database")
    parser.add_argument('-p', dest='pages', default=1,
                        help="the number of pages to fetch (doesn't work with"
                                                                    "--local)")
    parser.add_argument('-0', dest='first',
                        action='store_true',
                        help="choose the top result")
    parser.add_argument('-a', dest='download_all',
                        action='store_true',
                        help="download all results")
    parser.add_argument('--color', dest='color',
                        action='store_true',
                        help="use colored output")

    categories = {
        "All":"0",
        "Audio":"100",
        "Audio/Music":"101",
        "Audio/Audio books":"102",
        "Audio/Sound clips":"103",
        "Audio/FLAC":"104",
        "Audio/Other":"199",
        "Video":"200",
        "Video/Movies":"201",
        "Video/Movies DVDR":"202",
        "Video/Music videos":"203",
        "Video/Movie clips":"204",
        "Video/TV shows":"205",
        "Video/Handheld":"206",
        "Video/HD - Movies":"207",
        "Video/HD - TV shows":"208",
        "Video/3D":"209",
        "Video/Other":"299",
        "Applications":"300",
        "Applications/Windows":"301",
        "Applications/Mac":"302",
        "Applications/UNIX":"303",
        "Applications/Handheld":"304",
        "Applications/IOS (iPad/iPhone)":"305",
        "Applications/Android":"306",
        "Applications/Other OS":"399",
        "Games":"400",
        "Games/PC":"401",
        "Games/Mac":"402",
        "Games/PSx":"403",
        "Games/XBOX360":"404",
        "Games/Wii":"405",
        "Games/Handheld":"406",
        "Games/IOS (iPad/iPhone)":"407",
        "Games/Android":"408",
        "Games/Other":"499",
        "Porn":"500",
        "Porn/Movies":"501",
        "Porn/Movies DVDR":"502",
        "Porn/Pictures":"503",
        "Porn/Games":"504",
        "Porn/HD - Movies":"505",
        "Porn/Movie clips":"506",
        "Porn/Other":"599",
        "Other":"600",
        "Other/E-books":"601",
        "Other/Comics":"602",
        "Other/Pictures":"603",
        "Other/Covers":"604",
        "Other/Physibles":"605",
        "Other/Other":"699"}

    sorts = {
           "TitleDsc": "1",     "TitleAsc": "2",
            "DateDsc": "3",      "DateAsc": "4",
            "SizeDsc": "5",      "SizeAsc": "6",
         "SeedersDsc": "7",   "SeedersAsc": "8",
        "LeechersDsc": "9",  "LeechersAsc": "10",
        "CategoryDsc": "13", "CategoryAsc": "14",
            "Default": "99"}

    #todo: redo this with html parser instead of regex
    def remote(args, mirror):
        res_l = []
        try:
            pages = int(args.pages)
            if pages < 1:
                raise Exception('')
        except Exception:
            raise Exception("Please provide an integer greater than 0"
                            "for the number of pages to fetch.")

        if str(args.category) in categories.values():
            category = args.category;
        elif args.category in categories.keys():
            category = categories[args.category]
        else:
            category = "0";
            print("Invalid category ignored", color="WARN")

        if str(args.sort) in sorts.values():
            sort = args.sort;
        elif args.sort in sorts.keys():
            sort = sorts[args.sort]
        else:
            sort = "99";
            print("Invalid sort ignored", color="WARN")

        # Catch the Ctrl-C exception and exit cleanly
        try:
            sizes = []
            uploaded = []
            identifiers = []
            for page in range(pages):
                if args.browse:
                    path = "/browse/"
                    if(category == "0"):
                        category = '100'
                    path = '/browse/' + '/'.join(str(i) for i in (
                                                category, page, sort))
                elif len(args.search) == 0:
                    path = "/top/48h" if args.recent else "/top/"
                    if(category == "0"):
                        path += 'all'
                    else:
                        path += category
                else:
                    path = '/search/' + '/'.join(str(i) for i in (
                                                    "+".join(args.search),
                                                    page, sort,
                                                    category))

                req = request.Request(mirror + path)
                req.add_header('Accept-encoding', 'gzip')
                f = request.urlopen(req)
                if f.info().get('Content-Encoding') == 'gzip':
                    f = gzip.GzipFile(fileobj=BytesIO(f.read()))
                res = f.read().decode('utf-8')
                found = re.findall('"(magnet\:\?xt=[^"]*)|<td align="right">'
                                                         '([^<]+)</td>', res)

                # check for a blocked mirror
                no_results = re.search("\"No hits\.", res)
                if found == [] and not no_results is None:
                    # Contradiction - we found no results,
                    # but the page didn't say there were no results.
                    # The page is probably not actually the pirate bay,
                    # so let's try another mirror
                    raise Exception("Blocked mirror detected.")

                # get sizes as well and substitute the &nbsp; character
                sizes.extend([match.replace("&nbsp;", " ")
                             for match in re.findall("(?<=Size )[0-9.]"
                             "+\&nbsp\;[KMGT]*[i ]*B", res)])

                uploaded.extend([match.replace("&nbsp;", " ")
                                for match in re.findall("(?<=Uploaded )"
                                ".+(?=\, Size)",res)])

                identifiers.extend([match.replace("&nbsp;", " ")
                                for match in re.findall("(?<=/torrent/)"
                                "[0-9]+(?=/)",res)])

                state = "seeds"
                curr = ['', 0, 0] #magnet, seeds, leeches
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
        return res_l, sizes, uploaded, identifiers

    args = parser.parse_args()

    def make_print():
        if(args.color):
            import colorama
            colorama.init()
            color_dict = {
                "default": "",
                "header":  colorama.Back.WHITE + colorama.Fore.BLACK,
                "zebra_0": "",
                "zebra_1": colorama.Style.BRIGHT,
                "WARN":    colorama.Fore.YELLOW,
                "ERROR":   colorama.Fore.RED}

            def n_print(*args, **kwargs):
                """Print with colors"""
                try:
                    c = color_dict[kwargs.pop("color")]
                    args = (c + args[0],) + args[1:] + (colorama.Style.RESET_ALL,)
                except KeyError as e:
                    pass
                except IndexError as e:
                    pass
                return builtins.print(*args, **kwargs)
        else:
            def n_print(*args, **kwargs):
                if("color" in kwargs):
                    kwargs.pop('color')
                return builtins.print(*args, **kwargs)
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
        for key, value in sorted(sorts.iteritems()):
            cur_color = "zebra_0" if (cur_color == "zebra_1") else "zebra_1"
            print(str(value) +"\t" + key, color=cur_color)
        return

    if args.database:
        mags = local(args)
    else:
        mirrors = ["https://pirateproxy.sx"]
        try:
            opener = request.build_opener(NoRedirection)
            f = opener.open("https://proxybay.info/list.txt")
            if f.getcode() != 200:
                raise Exception("The pirate bay responded with an error.")
            res = f.read().decode('utf8')
            mirrors.append(res.split("\n")[3:])
        except:
            print("Could not fetch additional mirrors", color="WARN")
        for mirror in mirrors:
            try:
                print("Trying " + mirror)
                mags, sizes, uploaded, identifiers = remote(args, mirror)
                break
            except Exception as e:
                print(format(e))
                print("Could not contact", mirror, color="WARN")

    if not mags or len(mags) == 0:
        print("no results")
        return

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

            torrent_name = parse.unquote(name.group(1)).replace("+", " ")
            # enhanced print output with justified columns
            print ("%5d %6d %6d %5.1f %-11s %-11s  %s" % (
                m, no_seeders, no_leechers, ratio ,sizes[m],
                uploaded[m], torrent_name), color=cur_color)
    def print_descriptions(chosen_links):
        for link in chosen_links:
            path = '/torrent/%s/' % identifiers[int(link)]
            request = request.Request(mirror + path)
            request.add_header('Accept-encoding', 'gzip')
            f = request.urlopen(request)

            if f.info().get('Content-Encoding') == 'gzip':
                f = gzip.GzipFile(fileobj=BytesIO(f.read()))

            res = f.read()
            name = re.search("dn=([^\&]*)", mags[int(link)][0])
            torrent_name = parse.unquote(name.group(1)).replace("+", " ")
            desc = re.search(r"<div class=\"nfo\">\s*<pre>(.+?)(?=</pre>)",
                             res, re.DOTALL).group(1)

            # Replace HTML links with markdown style versions
            desc = re.sub(r"<a href=\"\s*([^\"]+?)\s*\"[^>]*>(\s*)([^<]+?)(\s*"
                          r")</a>", r"\2[\3](\1)\4", desc)

            print('Description for "' + torrent_name + '":', color="zebra_1")
            print(desc, color="zebra_0")

    def print_fileLists(chosen_links):
        for link in chosen_links:
            path = '/ajax_details_filelist.php'
            query = '?id=' + identifiers[int(link)]
            request = request.Request(mirror + path + query)
            request.add_header('Accept-encoding', 'gzip')
            f = request.urlopen(request)

            if f.info().get('Content-Encoding') == 'gzip':
                f = gzip.GzipFile(fileobj=BytesIO(f.read()))

            res = f.read().replace("&nbsp;", " ")
            files = re.findall(r"<td align=\"left\">\s*([^<]+?)\s*</td><td ali"
                               r"gn=\"right\">\s*([^<]+?)\s*</tr>", res)
            name = re.search("dn=([^\&]*)", mags[int(link)][0])
            torrent_name = parse.unquote(name.group(1)).replace("+", " ")

            print('Files in "' + torrent_name + '":', color="zebra_1")
            cur_color = "zebra_0"

            for f in files:
                print("%-11s  %s" % (f[1], f[0]), color=cur_color)
                cur_color = "zebra_0" if (cur_color == "zebra_1") else "zebra_1"

    print_search_results()

    if args.first:
        print("Choosing first result");
        choices = [0]
    elif args.download_all:
        print("Downloading all results");
        choices = range(len(mags))
    else:
        # New input loop to support different link options
        while True:
            try:
                l = input("Select link(s) (Type 'h' for more options"
                          "['q' to quit]): ")
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
                # Substitute multiple consecutive spaces/commas for single comma
                l = re.sub("[ ,]+", ",", l)
                # Remove anything that isn't an integer or comma.
                l = re.sub("[^0-9,]", "", l)
                # Turn into list
                choices = l.split(",")
                # Act on option, if supplied
                if code == 'h':
                    print("Options:",
                    "<links>: Download selected torrents",
                    "[d<links>]: Get descriptions",
                    "[f<links>]: Get files",
                    "[p] Print search results",
                    "[q] Quit", sep="\n")
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
            except Exception as e:
                print('Exception:')
                print(str(e))
                choices = ()
                break;

    if config.getboolean('SaveToFile', 'enabled'):
        # Save to file is enabled
        fileName = os.path.expanduser(
                        config.get('SaveToFile','directory')
                        ) + id_generator() + '.magnet'

        print("Saving to File: " + fileName)

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
                os.system('transmission-remote --add "%s" ' % (url))
                os.system('transmission-remote -l')
            elif args.command:
                os.system(args.command % (url))
            else:
                webbrowser.open(url)

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

if __name__ == "__main__":
    main()
