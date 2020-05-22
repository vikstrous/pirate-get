import builtins
import re
import gzip
import urllib.request as request
import shutil
import json
import sys

import pirate.data
import pirate.torrent

import colorama
import veryprettytable as pretty

from io import BytesIO


class Printer:
    def __init__(self, enable_color):
        self.enable_color = enable_color

    def print(self, *args, **kwargs):
        if kwargs.get('color', False) and self.enable_color:
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
            kwargs.pop('color', None)
            return builtins.print(*args, file=sys.stderr, **kwargs)
        else:
            kwargs.pop('color', None)
            return builtins.print(*args, file=sys.stderr, **kwargs)

    # TODO: extract the name from the search results
    #       instead of from the magnet link when possible
    def search_results(self, results, local=None):
        columns = shutil.get_terminal_size((80, 20)).columns
        even = True

        if local:
            table = pretty.VeryPrettyTable(['LINK', 'DATE', 'SIZE', 'NAME'])

            table.align['SIZE'] = 'r'
            table.align['NAME'] = 'l'
        else:
            table = pretty.VeryPrettyTable(['LINK', 'SEED', 'LEECH',
                                            'RATIO', 'SIZE',
                                            'UPLOAD', 'NAME'])
            table.align['NAME'] = 'l'
            table.align['SEED'] = 'r'
            table.align['LEECH'] = 'r'
            table.align['RATIO'] = 'r'
            table.align['SIZE'] = 'r'
            table.align['UPLOAD'] = 'l'

        table.max_width = columns
        table.border = False
        table.padding_width = 1

        for n, result in enumerate(results):
            torrent_name = result['name']

            if local:
                content = [n, result['date'], result['size'],
                           torrent_name[:columns - 42]]
            else:
                no_seeders = int(result['seeders'])
                no_leechers = int(result['leechers'])
                size = result['size']
                date = result['uploaded']

                # compute the S/L ratio (Higher is better)
                try:
                    ratio = no_seeders / no_leechers
                except ZeroDivisionError:
                    ratio = float('inf')

                content = [n, no_seeders, no_leechers,
                           '{:.1f}'.format(ratio),
                           size, date, torrent_name[:columns - 50]]

            if even or not self.enable_color:
                table.add_row(content)
            else:
                table.add_row(content, fore_color='blue')

            # Alternate between colors
            even = not even
        self.print(table)

    def descriptions(self, chosen_links, results, site, timeout):
        for link in chosen_links:
            result = results[link]
            req = request.Request(
                site + '/t.php?id=' + str(result['id']),
                headers=pirate.data.default_headers)
            req.add_header('Accept-encoding', 'gzip')
            f = request.urlopen(req, timeout=timeout)

            if f.info().get('Content-Encoding') == 'gzip':
                f = gzip.GzipFile(fileobj=BytesIO(f.read()))

            res = json.load(f)

            # Replace HTML links with markdown style versions
            desc = re.sub(r'<a href="\s*([^"]+?)\s*"[^>]*>(\s*)([^<]+?)(\s*'
                          r')</a>', r'\2[\3](\1)\4', res['descr'])

            self.print('Description for "{}":'.format(result['name']),
                       color='zebra_1')
            self.print(desc, color='zebra_0')

    def file_lists(self, chosen_links, results, site, timeout):
        # the API may returns object instead of list
        def get(obj):
            try:
                return obj[0]
            except KeyError:
                return obj['0']

        for link in chosen_links:
            result = results[link]
            req = request.Request(
                site + '/f.php?id=' + str(result['id']),
                headers=pirate.data.default_headers)
            req.add_header('Accept-encoding', 'gzip')
            f = request.urlopen(req, timeout=timeout)

            if f.info().get('Content-Encoding') == 'gzip':
                f = gzip.GzipFile(fileobj=BytesIO(f.read()))

            res = json.load(f)

            if len(res) == 1 and 'not found' in get(res[0]['name']):
                self.print('File list not available.')
                return

            self.print('Files in {}:'.format(result['name']), color='zebra_1')
            cur_color = 'zebra_0'

            for f in res:
                name = get(f['name'])
                size = pirate.torrent.pretty_size(int(get(f['size'])))
                self.print('{:>11} {}'.format(
                    size, name),
                    color=cur_color)
                cur_color = 'zebra_0' if cur_color == 'zebra_1' else 'zebra_1'
