import re
import sys
import gzip
import urllib.request as request
import urllib.parse as parse
import urllib.error
import os.path

import pirate.data
from pirate.print import print

from io import BytesIO


parser_regex = r'"(magnet\:\?xt=[^"]*)|<td align="right">([^<]+)</td>'


def parse_category(category):
    try:
        category = int(category)
    except ValueError:
        pass
    if category in pirate.data.categories.values():
        return category
    elif category in pirate.data.categories.keys():
        return pirate.data.categories[category]
    else:
        print('Invalid category ignored', color='WARN')
        return '0'


def parse_sort(sort):
    try:
        sort = int(sort)
    except ValueError:
        pass
    if sort in pirate.data.sorts.values():
        return sort
    elif sort in pirate.data.sorts.keys():
        return pirate.data.sorts[sort]
    else:
        print('Invalid sort ignored', color='WARN')
        return '99'


def parse_magnets_seeds_leechers(found):
    res = []
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
                res.append(curr)
                curr = ['', 0, 0]
    return res


#TODO: warn users when using a sort in a mode that doesn't accept sorts
#TODO: warn users when using search terms in a mode that doesn't accept search terms
#TODO: same with page parameter for top and top48h
#TODO: warn the user if trying to use a minor category with top48h
def build_request_path(page, category, sort, mode, terms):
    if mode == 'browse':
        if(category == 0):
            category = 100
        return '/browse/{}/{}/{}'.format(category, page, sort)
    elif mode == 'recent':
        # This is not a typo. There is no / between 48h and the category.
        path = '/top/48h'
        # only major categories can be used with this mode
        if(category == 0):
            return path + 'all'
        else:
            return path + str(category)
    elif mode == 'top':
        path = '/top/'
        if(category == 0):
            return path + 'all'
        else:
            return path + str(category)
    elif mode == 'search':
        query = urllib.parse.quote_plus(' '.join(terms))
        return '/search/{}/{}/{}/{}'.format(query, page, sort, category)
    else:
        raise Exception('Unknown mode.')


#TODO: redo this with html parser instead of regex
def parse_page(res):
    found = re.findall(parser_regex, res)

    # check for a blocked mirror
    no_results = re.search(r'No hits\. Try adding an asterisk in '
                           r'you search phrase\.', res)
    if found == [] and no_results is None:
        # Contradiction - we found no results,
        # but the page didn't say there were no results.
        # The page is probably not actually the pirate bay,
        # so let's try another mirror
        raise IOError('Blocked mirror detected.')

    # get sizes as well and substitute the &nbsp; character
    # TODO: use actual html decode
    sizes = [match.replace('&nbsp;', ' ').split()
                 for match in re.findall(r'(?<=Size )[0-9.]'
                 r'+\&nbsp\;[KMGT]*[i ]*B', res)]

    uploaded = [match.replace('&nbsp;', ' ')
                    for match in re.findall(r'(?<=Uploaded )'
                    r'.+(?=\, Size)',res)]

    identifiers = [match.replace('&nbsp;', ' ')
                    for match in re.findall('(?<=/torrent/)'
                    '[0-9]+(?=/)',res)]

    res_l = parse_magnets_seeds_leechers(found)

    return res_l, sizes, uploaded, identifiers


def remote(pages, category, sort, mode, terms, mirror):
    res_l = []
    sizes = []
    uploaded = []
    identifiers = []

    if pages < 1:
        raise ValueError('Please provide an integer greater than 0 '
                         'for the number of pages to fetch.')

    # Catch the Ctrl-C exception and exit cleanly
    try:
        for page in range(pages):
            path = build_request_path(page, category, sort, mode, terms)

            req = request.Request(mirror + path,
                                  headers=pirate.data.default_headers)
            req.add_header('Accept-encoding', 'gzip')
            f = request.urlopen(req, timeout=pirate.data.default_timeout)
            if f.info().get('Content-Encoding') == 'gzip':
                f = gzip.GzipFile(fileobj=BytesIO(f.read()))
            res = f.read().decode('utf-8')

            page_res_l, page_sizes, page_uploaded, page_identifiers = parse_page(res)
            res_l += page_res_l
            sizes += page_sizes
            uploaded += page_uploaded
            identifiers += page_identifiers

    except KeyboardInterrupt:
        print('\nCancelled.')
        sys.exit(0)

    # return the sizes in a separate list
    return res_l, sizes, uploaded, identifiers


def get_torrent(info_hash):
    url = 'http://torcache.net/torrent/{:X}.torrent'
    req = request.Request(url.format(info_hash),
            headers=pirate.data.default_headers)
    req.add_header('Accept-encoding', 'gzip')
    
    torrent = request.urlopen(req, timeout=pirate.data.default_timeout)
    if torrent.info().get('Content-Encoding') == 'gzip':
        torrent = gzip.GzipFile(fileobj=BytesIO(torrent.read()))

    return torrent.read()


def save_torrents(chosen_links, mags, folder):
    for link in chosen_links:
        magnet = mags[int(link)][0]
        name = re.search(r'dn=([^\&]*)', magnet)
        torrent_name = parse.unquote(name.group(1)).replace('+', ' ')
        info_hash = int(re.search(r'btih:([a-f0-9]{40})', magnet).group(1), 16)
        file = os.path.join(folder, torrent_name + '.torrent')

        try:
            torrent = get_torrent(info_hash)
        except urllib.error.HTTPError:
            print('There is no cached file for this torrent :(', color='ERROR')
        else:
            open(file,'wb').write(torrent)
            print('Saved {:X} in {}'.format(info_hash, file))


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
