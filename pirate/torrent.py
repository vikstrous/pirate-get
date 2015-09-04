import re
import sys
import gzip
import urllib.request as request
import urllib.parse as parse
import urllib.error
import os.path

from pyquery import PyQuery as pq

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


def parse_page(html):
    d = pq(html)

    # first get the magnet links and make sure there are results
    magnets = list(map(lambda l: pq(l).attr('href'), 
        d('table#searchResult tr>td:nth-child(2)>a:nth-child(2)')))

    # check for a blocked mirror
    no_results = re.search(r'No hits\. Try adding an asterisk in '
                           r'you search phrase\.', html)
    if len(magnets) == 0 and no_results is None:
        # Contradiction - we found no results,
        # but the page didn't say there were no results.
        # The page is probably not actually the pirate bay,
        # so let's try another mirror
        raise IOError('Blocked mirror detected.')

    # next get more info
    seeds = list(map(lambda l: pq(l).text(), 
        d('table#searchResult tr>td:nth-child(3)')))
    leechers = list(map(lambda l: pq(l).text(), 
        d('table#searchResult tr>td:nth-child(4)')))
    identifiers = list(map(lambda l: pq(l).attr('href').split('/')[2],
        d('table#searchResult .detLink')))

    sizes = []
    uploaded = []
    # parse descriptions separately
    for node in d('font.detDesc'):
        text = pq(node).text()
        sizes.append(re.findall(r'(?<=Size )[0-9.]+\s[KMGT]*[i ]*B', text)[0].split())
        uploaded.append(re.findall(r'(?<=Uploaded ).+(?=\, Size)', text)[0])

    return list(zip(magnets,seeds,leechers)), sizes, uploaded, identifiers


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
