#!/usr/bin/env python
#
# Copyright 2015, Viktor Stanchev and contributors
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
import sys
import re
import string
import gzip
import configparser
import argparse
import builtins
import subprocess

import webbrowser
import urllib.request as request
import urllib.parse as parse

from html.parser import HTMLParser
from urllib.error import URLError, HTTPError
from socket import timeout
from io import BytesIO
from os.path import expanduser, expandvars

colored_output = True

default_timeout = 10

headers = {'User-Agent': 'pirate get'}

categories = {
    'All': 0,
    'Applications': 300,
    'Applications/Android': 306,
    'Applications/Handheld': 304,
    'Applications/IOS (iPad/iPhone)': 305,
    'Applications/Mac': 302,
    'Applications/Other OS': 399,
    'Applications/UNIX': 303,
    'Applications/Windows': 301,
    'Audio': 100,
    'Audio/Audio books': 102,
    'Audio/FLAC': 104,
    'Audio/Music': 101,
    'Audio/Other': 199,
    'Audio/Sound clips': 103,
    'Games': 400,
    'Games/Android': 408,
    'Games/Handheld': 406,
    'Games/IOS (iPad/iPhone)': 407,
    'Games/Mac': 402,
    'Games/Other': 499,
    'Games/PC': 401,
    'Games/PSx': 403,
    'Games/Wii': 405,
    'Games/XBOX360': 404,
    'Other': 600,
    'Other/Comics': 602,
    'Other/Covers': 604,
    'Other/E-books': 601,
    'Other/Other': 699,
    'Other/Physibles': 605,
    'Other/Pictures': 603,
    'Porn': 500,
    'Porn/Games': 504,
    'Porn/HD - Movies': 505,
    'Porn/Movie clips': 506,
    'Porn/Movies': 501,
    'Porn/Movies DVDR': 502,
    'Porn/Other': 599,
    'Porn/Pictures': 503,
    'Video': 200,
    'Video/3D': 209,
    'Video/HD - Movies': 207,
    'Video/HD - TV shows': 208,
    'Video/Handheld': 206,
    'Video/Movie clips': 204,
    'Video/Movies': 201,
    'Video/Movies DVDR': 202,
    'Video/Music videos': 203,
    'Video/Other': 299,
    'Video/TV shows': 205}

sorts = {
    'TitleDsc': 1, 'TitleAsc': 2,
    'DateDsc': 3, 'DateAsc': 4,
    'SizeDsc': 5, 'SizeAsc': 6,
    'SeedersDsc': 7, 'SeedersAsc': 8,
    'LeechersDsc': 9, 'LeechersAsc': 10,
    'CategoryDsc': 13, 'CategoryAsc': 14,
    'Default': 99}


class NoRedirection(request.HTTPErrorProcessor):
    def http_response(self, _, res):
        return res

    https_response = http_response


# create a subclass and override the handler methods
class BayParser(HTMLParser):
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


def print(*args, **kwargs):
    if kwargs.get('color', False) and colored_output:
        try:
            import colorama
            colorama.init()
            color_dict = {
                'default': '',
                'header':  colorama.Back.BLACK + colorama.Fore.WHITE,
                'alt':     colorama.Fore.YELLOW,
                'zebra_0': '',
                'zebra_1': colorama.Fore.BLUE,
                'WARN':    colorama.Fore.MAGENTA,
                'ERROR':   colorama.Fore.RED}

            c = color_dict[kwargs.pop('color')]
            args = (c + args[0],) + args[1:] + (colorama.Style.RESET_ALL,)
        except (KeyError, IndexError, ImportError):
            pass
        kwargs.pop('color', None)
        return builtins.print(*args, **kwargs)
    else:
        kwargs.pop('color', None)
        return builtins.print(*args, **kwargs)


#todo: redo this with html parser instead of regex
def remote(args, mirror):
    res_l = []
    pages = int(args.pages)
    if pages < 1:
        raise ValueError('Please provide an integer greater than 0 '
                         'for the number of pages to fetch.')

    if str(args.category) in categories.values():
        category = args.category
    elif args.category in categories.keys():
        category = categories[args.category]
    else:
        category = '0'
        print('Invalid category ignored', color='WARN')

    if str(args.sort) in sorts.values():
        sort = args.sort
    elif args.sort in sorts.keys():
        sort = sorts[args.sort]
    else:
        sort = '99'
        print('Invalid sort ignored', color='WARN')
    # Catch the Ctrl-C exception and exit cleanly
    try:
        sizes = []
        uploaded = []
        identifiers = []
        for page in range(pages):
            if args.browse:
                path = '/browse/'
                if(category == 0):
                    category = 100
                path = '/browse/' + '/'.join(str(i) for i in (
                                            category, page, sort))
            elif len(args.search) == 0:
                path = '/top/48h' if args.recent else '/top/'
                if(category == 0):
                    path += 'all'
                else:
                    path += str(category)
            else:
                path = '/search/' + '/'.join(str(i) for i in (
                                                '+'.join(args.search),
                                                page, sort,
                                                category))

            req = request.Request(mirror + path, headers=headers)
            req.add_header('Accept-encoding', 'gzip')
            f = request.urlopen(req, timeout=default_timeout)
            if f.info().get('Content-Encoding') == 'gzip':
                f = gzip.GzipFile(fileobj=BytesIO(f.read()))
            res = f.read().decode('utf-8')
            found = re.findall(r'"(magnet\:\?xt=[^"]*)|<td align="right">'
                                                     r'([^<]+)</td>', res)

            # check for a blocked mirror
            no_results = re.search(r'"No hits\.', res)
            if found == [] and no_results is None:
                # Contradiction - we found no results,
                # but the page didn't say there were no results.
                # The page is probably not actually the pirate bay,
                # so let's try another mirror
                raise IOError('Blocked mirror detected.')

            # get sizes as well and substitute the &nbsp; character
            sizes.extend([match.replace('&nbsp;', ' ').split()
                         for match in re.findall(r'(?<=Size )[0-9.]'
                         r'+\&nbsp\;[KMGT]*[i ]*B', res)])

            uploaded.extend([match.replace('&nbsp;', ' ')
                            for match in re.findall(r'(?<=Uploaded )'
                            r'.+(?=\, Size)',res)])

            identifiers.extend([match.replace('&nbsp;', ' ')
                            for match in re.findall('(?<=/torrent/)'
                            '[0-9]+(?=/)',res)])

            state = 'seeds'
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
        print('\nCancelled.')
        sys.exit(0)

    # return the sizes in a spearate list
    return res_l, sizes, uploaded, identifiers


def local(db, search):
    xml = open(db).readlines()
    parser = BayParser(' '.join(search))
    parser.feed(''.join(xml))
    return parser.results


def load_config():
    config = configparser.ConfigParser()

    # default options
    config.add_section('Save')
    config.set('Save', 'magnets', 'false')
    config.set('Save', 'torrents', 'false')
    config.set('Save', 'directory', expanduser('~/downloads/pirate-get'))

    config.add_section('LocalDB')
    config.set('LocalDB', 'enabled', 'false')
    config.set('LocalDB', 'path', expanduser('~/downloads/pirate-get/db'))

    config.add_section('Misc')    
    config.set('Misc', 'openCommand', '')
    config.set('Misc', 'transmission', 'false')
    config.set('Misc', 'colors', 'true')

    # user-defined config files
    main = expandvars('$XDG_CONFIG_HOME/pirate-get')
    alt = expanduser('~/.config/pirate-get')

    # read config file
    config.read([main] if os.path.isfile(main) else [alt])

    # expand env variables
    directory = expanduser(expandvars(config.get('Save', 'Directory')))
    path = expanduser(expandvars(config.get('LocalDB', 'path')))

    config.set('Save', 'Directory', directory)
    config.set('LocalDB', 'path', path)

    return config


def get_torrent(info_hash):
    url = 'http://torcache.net/torrent/{:X}.torrent'
    req = request.Request(url.format(info_hash))
    req.add_header('Accept-encoding', 'gzip')
    
    torrent = request.urlopen(req, timeout=default_timeout)
    if torrent.info().get('Content-Encoding') == 'gzip':
        torrent = gzip.GzipFile(fileobj=BytesIO(torrent.read()))

    return torrent.read()


# enhanced print output with column titles
def print_search_results(mags, sizes, uploaded):
    columns = int(os.popen('stty size', 'r').read().split()[1]) - 52
    cur_color = 'zebra_0'

    print('{:>4}  {:>5}  {:>5}  {:>5}  {:9}  {:11}  {:{length}}'.format(
          'LINK', 'SEED', 'LEECH', 'RATIO',
          'SIZE', 'UPLOAD', 'NAME', length=columns),
          color='header')

    for m, magnet in enumerate(mags):
        no_seeders = int(magnet[1])
        no_leechers = int(magnet[2])
        name = re.search(r'dn=([^\&]*)', magnet[0])

        # compute the S/L ratio (Higher is better)
        try:
            ratio = no_seeders / no_leechers
        except ZeroDivisionError:
            ratio = float('inf')

        # Alternate between colors
        cur_color = 'zebra_0' if (cur_color == 'zebra_1') else 'zebra_1'

        torrent_name = parse.unquote(name.group(1)).replace('+', ' ')
        # enhanced print output with justified columns
        print('{:4}  {:5}  {:5}  {:5.1f}  {:5.1f} {:3}  '
              '{:<11}  {:{length}}'.format(m, no_seeders, no_leechers,
                                           ratio, float(sizes[m][0]),
                                           sizes[m][1], uploaded[m],
                                           torrent_name[:columns],
                                           length=columns),
               color=cur_color)


def print_descriptions(chosen_links, mags, site, identifiers):
    for link in chosen_links:
        link = int(link)
        path = '/torrent/%s/' % identifiers[link]
        req = request.Request(site + path, headers=headers)
        req.add_header('Accept-encoding', 'gzip')
        f = request.urlopen(req, timeout=default_timeout)

        if f.info().get('Content-Encoding') == 'gzip':
            f = gzip.GzipFile(fileobj=BytesIO(f.read()))

        res = f.read().decode('utf-8')
        name = re.search(r'dn=([^\&]*)', mags[link][0])
        torrent_name = parse.unquote(name.group(1)).replace('+', ' ')
        desc = re.search(r'<div class="nfo">\s*<pre>(.+?)(?=</pre>)',
                         res, re.DOTALL).group(1)

        # Replace HTML links with markdown style versions
        desc = re.sub(r'<a href="\s*([^"]+?)\s*"[^>]*>(\s*)([^<]+?)(\s*'
                      r')</a>', r'\2[\3](\1)\4', desc)

        print('Description for "%s":' % torrent_name, color='zebra_1')
        print(desc, color='zebra_0')


def print_file_lists(chosen_links, mags, site, identifiers):
    for link in chosen_links:
        path = '/ajax_details_filelist.php'
        query = '?id=' + identifiers[int(link)]
        req = request.Request(site + path + query, headers=headers)
        req.add_header('Accept-encoding', 'gzip')
        f = request.urlopen(req, timeout=default_timeout)

        if f.info().get('Content-Encoding') == 'gzip':
            f = gzip.GzipFile(fileobj=BytesIO(f.read()))

        res = f.read().decode('utf-8').replace('&nbsp;', ' ')
        files = re.findall(r'<td align="left">\s*([^<]+?)\s*</td><td ali'
                           r'gn="right">\s*([^<]+?)\s*</tr>', res)
        name = re.search(r'dn=([^\&]*)', mags[int(link)][0])
        torrent_name = parse.unquote(name.group(1)).replace('+', ' ')

        print('Files in "%s":' % torrent_name, color='zebra_1')
        cur_color = 'zebra_0'

        for f in files:
            print('{0[0]:>11}  {0[1]}'.format(f), color=cur_color)
            cur_color = 'zebra_0' if (cur_color == 'zebra_1') else 'zebra_1'


def save_torrents(chosen_links, mags, folder):
    for link in chosen_links:
        magnet = mags[int(link)][0]
        name = re.search(r'dn=([^\&]*)', magnet)
        torrent_name = parse.unquote(name.group(1)).replace('+', ' ')
        info_hash = int(re.search(r'btih:([a-f0-9]{40})', magnet).group(1), 16)
        file = os.path.join(folder, torrent_name + '.torrent')

        try:
            torrent = get_torrent(info_hash)
            open(file,'wb').write(torrent)
            print('Saved {:X} in {}'.format(info_hash, file))
        except HTTPError:
            print('There is no cached file for this torrent :(', color='ERROR')


def save_magnets(chosen_links, mags, folder):
    for link in chosen_links:
        magnet = mags[int(link)][0]
        name = re.search(r'dn=([^\&]*)', magnet)
        torrent_name = parse.unquote(name.group(1)).replace('+', ' ')
        info_hash = int(re.search(r'btih:([a-f0-9]{40})', magnet).group(1), 16)
        file = os.path.join(folder,  torrent_name + '.magnet')

        print('Saved {:X} in {}'.format(info_hash, file))
        with open(file, 'w') as f:
            f.write(magnet + '\n')


def main():
    config = load_config()

    parser = argparse.ArgumentParser(
                description='finds and downloads torrents from the Pirate Bay')
    parser.add_argument('-b', dest='browse',
                        action='store_true',
                        help='display in Browse mode')
    parser.add_argument('search', metavar='search',
                        nargs='*', help='term to search for')
    parser.add_argument('-c', dest='category', metavar='category',
                        help='specify a category to search', default='All')
    parser.add_argument('-s', dest='sort', metavar='sort',
                        help='specify a sort option', default='SeedersDsc')
    parser.add_argument('-R', dest='recent',  action='store_true',
                        help='torrents uploaded in the last 48hours.'
                                                '*ignored in searches*')
    parser.add_argument('-l', dest='list_categories',
                        action='store_true',
                        help='list categories')
    parser.add_argument('--list_sorts', dest='list_sorts',
                        action='store_true',
                        help='list Sortable Types')
    parser.add_argument('--custom', dest='command',
                        help='call custom command, %%s will be replaced with'
                                                                    'the url')
    parser.add_argument('-L', '--local', dest='database',
                        help='an xml file containing the Pirate Bay database')
    parser.add_argument('-p', dest='pages', default=1,
                        help="the number of pages to fetch (doesn't work with"
                                                                    '--local)')
    parser.add_argument('-0', dest='first',
                        action='store_true',
                        help='choose the top result')
    parser.add_argument('-a', dest='download_all',
                        action='store_true',
                        help='download all results')
    parser.add_argument('-t', '--transmission',
                         action='store_true',
                         help='open magnets with transmission-remote')
    parser.add_argument('-M', '--save-magnets',
                        action='store_true', default=False,
                        help='save magnets links as files')
    parser.add_argument('-T', '--save-torrents',
                        action='store_true', default=False,
                        help='save torrent files')
    parser.add_argument('--color', dest='color',
                        action='store_false', default=True,
                        help='disable colored output')
    args = parser.parse_args()

    if (config.getboolean('Misc', 'colors') and not args.color
        or not config.getboolean('Misc', 'colors')):
        global colored_output
        colored_output = False

    if args.transmission or config.getboolean('Misc', 'transmission'):
        ret = subprocess.call(['transmission-remote', '-l'],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        if ret != 0:
            print('Transmission is not running.')
            return

    if args.list_categories:
        cur_color = 'zebra_0'
        for key, value in sorted(categories.items()) :
            cur_color = 'zebra_0' if cur_color == 'zebra_1' else 'zebra_1'
            print(str(value), '\t', key, sep='', color=cur_color)
        return

    if args.list_sorts:
        cur_color = 'zebra_0'
        for key, value in sorted(sorts.items()):
            cur_color = 'zebra_0' if cur_color == 'zebra_1' else 'zebra_1'
            print(str(value), '\t', key, sep='', color=cur_color)
        return

    if args.database or config.getboolean('LocalDB', 'enabled'):
        if args.database:
            path = args.database
        else:
            path = config.get('LocalDB', 'path')
        mags = local(path, args.search)

    else:
        mags, mirrors = [], []
        try:
            opener = request.build_opener(NoRedirection)
            f = opener.open('https://proxybay.info/list.txt',
                            timeout=default_timeout)
            if f.getcode() != 200:
                raise IOError('The pirate bay responded with an error.')
            mirrors.extend([i.decode('utf-8').strip()
                            for i in f.readlines()][3:])
        except IOError:
            print('Could not fetch additional mirrors', color='WARN')
        for mirror in mirrors:
            try:
                print('Trying', mirror, end='... ')
                mags, sizes, uploaded, identifiers = remote(args, mirror)
                site = mirror
                print('Ok', color='alt')
                break
            except (URLError, IOError, ValueError, timeout) as e:
                print('Failed', color='WARN')
        else:
          print('No available mirrors :(', color='WARN')
          return

    if not mags:
        print('No results')
        return

    print_search_results(mags, sizes, uploaded)

    if args.first:
        print('Choosing first result')
        choices = [0]
    elif args.download_all:
        print('Downloading all results')
        choices = range(len(mags))
    else:
        # New input loop to support different link options
        while True:
            try:
                print("\nSelect links (Type 'h' for more options"
                      ", 'q' to quit)", end='\b', color='alt')
                l=input(': ')
            except KeyboardInterrupt :
                print('\nCancelled.')
                return

            try:
                # Very permissive handling
                # Check for any occurances or d, f, p, t, m, or q
                cmd_code_match = re.search(r'([hdfpmtq])', l,
                                           flags=re.IGNORECASE)
                if cmd_code_match:
                    code = cmd_code_match.group(0).lower()
                else:
                    code = None

                # Clean up command codes
                # Substitute multiple consecutive spaces/commas for single comma
                # Remove anything that isn't an integer or comma.
                # Turn into list
                l = re.sub(r'^[hdfp, ]*|[hdfp, ]*$', '', l)
                l = re.sub('[ ,]+', ',', l)
                l = re.sub('[^0-9,]', '', l)
                choices = l.split(',')

                # Act on option, if supplied
                print('')
                if code == 'h':
                    print('Options:',
                          '<links>: Download selected torrents',
                          '[m<links>]: Save magnets as files',
                          '[t<links>]: Save .torrent files',
                          '[d<links>]: Get descriptions',
                          '[f<links>]: Get files',
                          '[p] Print search results',
                          '[q] Quit', sep='\n')
                elif code == 'q':
                    print('Bye.', color='alt')
                    return
                elif code == 'd':
                    print_descriptions(choices, mags, site, identifiers)
                elif code == 'f':
                    print_file_lists(choices, mags, site, identifiers)
                elif code == 'p':
                    print_search_results(mags, sizes, uploaded)
                elif code == 'm':
                    save_magnets(choices, mags,
                                  config.get('Save', 'directory'))
                elif code == 't':
                    save_torrents(choices, mags,
                                  config.get('Save', 'directory'))
                elif not l:
                    print('No links entered!', color='WARN')
                else:
                    break
            except Exception as e:
                print('Exception:', e, color='ERROR')
                choices = ()

    save_to_file = False

    if args.save_magnets or config.getboolean('Save', 'magnets'):
        print('Saving selected magnets...')
        save_magnets(choices, mags, config.get('Save', 'directory'))
        save_to_file = True

    if args.save_torrents or config.getboolean('Save', 'torrents'):
        print('Saving selected torrents...')
        save_torrents(choices, mags, config.get('Save', 'directory'))
        save_to_file = True

    if save_to_file:
        return

    for choice in choices:
        url = mags[int(choice)][0]

        if args.transmission or config.getboolean('Misc', 'transmission'):
            os.system('transmission-remote --add "%s" ' % url)
            os.system('transmission-remote -l')

        elif args.command or config.get('Misc', 'openCommand'):
            command = config.get('Misc', 'openCommand')
            if args.command:
                command = args.command
            os.system(command % url)

        else:
            webbrowser.open(url)


if __name__ == '__main__':
    main()
