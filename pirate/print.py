import builtins
import re
import gzip
import urllib.parse as parse
import urllib.request as request
import shutil
from io import BytesIO

import colorama
import veryprettytable

import pirate.data


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
            return builtins.print(*args, **kwargs)
        else:
            kwargs.pop('color', None)
            return builtins.print(*args, **kwargs)

    # TODO: extract the name from the search results
    #       instead of from the magnet link when possible
    def search_results(self, results, local=None):
        columns = shutil.get_terminal_size((80, 20)).columns
        even = True

        if local:
            table = veryprettytable.VeryPrettyTable(['LINK', 'NAME'])
        else:
            table = veryprettytable.VeryPrettyTable(['LINK', 'SEED', 'LEECH',
                                                     'RATIO', 'SIZE', '',
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

            name = re.search(r'dn=([^\&]*)', result['magnet'])
            torrent_name = parse.unquote_plus(name.group(1))

            if local:
                content = [n, torrent_name[:columns - 7]]
            else:
                no_seeders = int(result['seeds'])
                no_leechers = int(result['leechers'])
                if result['size'] != []:
                    size = float(result['size'][0])
                    unit = result['size'][1]
                else:
                    size = 0
                    unit = '???'
                date = result['uploaded']

                # compute the S/L ratio (Higher is better)
                try:
                    ratio = no_seeders / no_leechers
                except ZeroDivisionError:
                    ratio = float('inf')

                content = [n, no_seeders, no_leechers,
                           '{:.1f}'.format(ratio),
                           '{:.1f}'.format(size),
                           unit, date, torrent_name[:columns - 53]]

            if even or not self.enable_color:
                table.add_row(content)
            else:
                table.add_row(content, fore_color='blue')

            # Alternate between colors
            even = not even
        self.print(table)

    def descriptions(self, chosen_links, results, site):
        for link in chosen_links:
            path = '/torrent/%s/' % results[link]['id']
            req = request.Request(site + path,
                                  headers=pirate.data.default_headers)
            req.add_header('Accept-encoding', 'gzip')
            f = request.urlopen(req, timeout=pirate.data.default_timeout)

            if f.info().get('Content-Encoding') == 'gzip':
                f = gzip.GzipFile(fileobj=BytesIO(f.read()))

            res = f.read().decode('utf-8')
            name = re.search(r'dn=([^\&]*)', results[link]['magnet'])
            torrent_name = parse.unquote(name.group(1)).replace('+', ' ')
            desc = re.search(r'<div class="nfo">\s*<pre>(.+?)(?=</pre>)',
                             res, re.DOTALL).group(1)

            # Replace HTML links with markdown style versions
            desc = re.sub(r'<a href="\s*([^"]+?)\s*"[^>]*>(\s*)([^<]+?)(\s*'
                          r')</a>', r'\2[\3](\1)\4', desc)

            self.print('Description for "%s":' % torrent_name, color='zebra_1')
            self.print(desc, color='zebra_0')

    def file_lists(self, chosen_links, results, site):
        for link in chosen_links:
            path = '/ajax_details_filelist.php'
            query = '?id=' + results[link]['id']
            req = request.Request(site + path + query,
                                  headers=pirate.data.default_headers)
            req.add_header('Accept-encoding', 'gzip')
            f = request.urlopen(req, timeout=pirate.data.default_timeout)

            if f.info().get('Content-Encoding') == 'gzip':
                f = gzip.GzipFile(fileobj=BytesIO(f.read()))

            # TODO: proper html decoding/parsing
            res = f.read().decode('utf-8').replace('&nbsp;', ' ')
            if 'File list not available.' in res:
                self.print('File list not available.')
                return
            files = re.findall(r'<td align="left">\s*([^<]+?)\s*</td><td ali'
                               r'gn="right">\s*([^<]+?)\s*</tr>', res)
            name = re.search(r'dn=([^\&]*)', results[link]['magnet'])
            torrent_name = parse.unquote(name.group(1)).replace('+', ' ')

            self.print('Files in "%s":' % torrent_name, color='zebra_1')
            cur_color = 'zebra_0'

            for f in files:
                self.print('{0[0]:>11}  {0[1]}'.format(f), color=cur_color)
                cur_color = 'zebra_0' if cur_color == 'zebra_1' else 'zebra_1'
