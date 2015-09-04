import builtins
import re
import os
import gzip
import colorama
import urllib.parse as parse
import urllib.request as request
import shutil
from io import BytesIO

import pirate.data


def print(*args, **kwargs):
    if kwargs.get('color', False) and pirate.data.colored_output:
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


# TODO: extract the name from the search results instead of the magnet link when possible
def search_results(results, local=None):
    columns = shutil.get_terminal_size((80, 20)).columns
    cur_color = 'zebra_0'

    if local:
        print('{:>4}   {:{length}}'.format(
              'LINK', 'NAME', length=columns - 8),
              color='header')
    else:
        print('{:>4}  {:>5}  {:>5}  {:>5}  {:9}  {:11}  {:{length}}'.format(
              'LINK', 'SEED', 'LEECH', 'RATIO',
              'SIZE', 'UPLOAD', 'NAME', length=columns - 52),
              color='header')

    for n, result in enumerate(results):
        # Alternate between colors
        cur_color = 'zebra_0' if cur_color == 'zebra_1' else 'zebra_1'

        name = re.search(r'dn=([^\&]*)', result['magnet'])
        torrent_name = parse.unquote_plus(name.group(1))

        if local:
            line = '{:5}  {:{length}}'
            content = [n, torrent_name[:columns]]
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

            line = ('{:4}  {:5}  {:5}  {:5.1f}  {:5.1f}'
                    ' {:3}  {:<11}  {:{length}}')
            content = [n, no_seeders, no_leechers, ratio,
                       size, unit, date, torrent_name[:columns - 52]]

        # enhanced print output with justified columns
        print(line.format(*content, length=columns - 52), color=cur_color)


def descriptions(chosen_links, results, site):
    for link in chosen_links:
        path = '/torrent/%s/' % results[link]['id']
        req = request.Request(site + path, headers=pirate.data.default_headers)
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

        print('Description for "%s":' % torrent_name, color='zebra_1')
        print(desc, color='zebra_0')


def file_lists(chosen_links, results, site):
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
            print('File list not available.')
            return
        files = re.findall(r'<td align="left">\s*([^<]+?)\s*</td><td ali'
                           r'gn="right">\s*([^<]+?)\s*</tr>', res)
        name = re.search(r'dn=([^\&]*)', results[link]['magnet'])
        torrent_name = parse.unquote(name.group(1)).replace('+', ' ')

        print('Files in "%s":' % torrent_name, color='zebra_1')
        cur_color = 'zebra_0'

        for f in files:
            print('{0[0]:>11}  {0[1]}'.format(f), color=cur_color)
            cur_color = 'zebra_0' if (cur_color == 'zebra_1') else 'zebra_1'
