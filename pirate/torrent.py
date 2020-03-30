import re
import sys
import gzip
import pyperclip
import urllib.request as request
import urllib.parse as parse
import urllib.error
import os.path

import pirate.data

from bs4 import BeautifulSoup
from io import BytesIO
from http.cookiejar import CookieJar


parser_regex = r'"(magnet\:\?xt=[^"]*)|<td align="right">([^<]+)</td>'


def parse_category(printer, category):
    try:
        category = int(category)
    except ValueError:
        pass
    if category in pirate.data.categories.values():
        return category
    elif category in pirate.data.categories.keys():
        return pirate.data.categories[category]
    else:
        printer.print('Invalid category ignored', color='WARN')
        return 0


def parse_sort(printer, sort):
    try:
        sort = int(sort)
    except ValueError:
        pass
    if sort in pirate.data.sorts.values():
        return sort
    elif sort in pirate.data.sorts.keys():
        return pirate.data.sorts[sort]
    else:
        printer.print('Invalid sort ignored', color='WARN')
        return 99


# TODO:
# * warn users when using a sort in a mode that doesn't accept sorts
# * warn users when using search terms in a mode
#   that doesn't accept search terms
# * same with page parameter for top and top48h
# * warn the user if trying to use a minor category with top48h
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


# this returns a list of dictionaries
def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table', id='searchResult')
    no_results = re.search(r'No hits\. Try adding an asterisk in '
                           r'you search phrase\.', html)

    # check for a blocked mirror
    if not tables and not no_results:
        # Contradiction - we found no results,
        # but the page didn't say there were no results.
        # The page is probably not actually the pirate bay,
        # so let's try another mirror
        raise IOError('Blocked mirror detected.')

    if no_results:
        return []

    # handle ads disguised as fake result tables
    for table in tables:
        results = parse_table(table)
        if results:
            break
    else:
        raise IOError('Mirror does not contain magnets.')

    return results


def parse_table(table):
    results = []

    # parse the rows one by one (skipping headings)
    for row in table('tr')[1:]:
        # grab info about the row
        row_link = row.find('a', class_='detLink')
        if row_link is None:
            continue

        id_ = row_link['href'].split('/')[2]
        seeds, leechers = [i.text for i in row('td')[-2:]]
        magnet_tag = row.find(lambda tag: tag.name == 'a' and
                              tag['href'].startswith('magnet'))
        if magnet_tag is None:
            continue
        magnet = magnet_tag['href']

        # parse descriptions separately
        description = row.find('font', class_='detDesc').text
        size = re.findall(r'(?<=Size )[0-9.]+\s[KMGT]*[i ]*B',
                          description)[0].split()
        uploaded = re.findall(r'(?<=Uploaded ).+(?=\, Size)',
                              description)[0]

        results.append({
            'magnet': magnet,
            'seeds': seeds,
            'leechers': leechers,
            'size': size,
            'uploaded': uploaded,
            'id': id_
        })

    return results


def remote(printer, pages, category, sort, mode, terms, mirror):
    res_l = []

    if pages < 1:
        raise ValueError('Please provide an integer greater than 0 '
                         'for the number of pages to fetch.')

    # Catch the Ctrl-C exception and exit cleanly
    try:
        jar = CookieJar()
        opener = request.build_opener(
            request.HTTPErrorProcessor,
            request.HTTPCookieProcessor(jar))

        for page in range(pages):
            path = build_request_path(page, category, sort, mode, terms)

            req = request.Request(mirror + path,
                                  headers=pirate.data.default_headers)
            req.add_header('Accept-encoding', 'gzip')

            try:
                f = opener.open(req, timeout=pirate.data.default_timeout)
            except urllib.error.URLError as e:
                res = e.fp.read().decode()
                if e.code == 503 and 'cf-browser-verification' in res:
                    raise IOError('Cloudflare protected')
                raise e

            if f.info().get('Content-Encoding') == 'gzip':
                f = gzip.GzipFile(fileobj=BytesIO(f.read()))
            res = f.read().decode('utf-8')

            res_l += parse_page(res)

    except KeyboardInterrupt:
        printer.print('\nCancelled.')
        sys.exit(0)

    return res_l


def get_torrent(info_hash):
    url = 'http://itorrents.org/torrent/{:X}.torrent'
    req = request.Request(url.format(info_hash),
                          headers=pirate.data.default_headers)
    req.add_header('Accept-encoding', 'gzip')

    torrent = request.urlopen(req, timeout=pirate.data.default_timeout)
    if torrent.info().get('Content-Encoding') == 'gzip':
        torrent = gzip.GzipFile(fileobj=BytesIO(torrent.read()))

    return torrent.read()


def save_torrents(printer, chosen_links, results, folder):
    for link in chosen_links:
        magnet = results[link]['magnet']
        name = re.search(r'dn=([^\&]*)', magnet)
        torrent_name = parse.unquote(name.group(1)).replace('+', ' ')
        info_hash = int(re.search(r'btih:([a-f0-9]{40})', magnet).group(1), 16)
        torrent_name = torrent_name.replace('/', '_').replace('\\', '_')
        file = os.path.join(folder, torrent_name + '.torrent')

        try:
            torrent = get_torrent(info_hash)
        except urllib.error.HTTPError as e:
            printer.print('There is no cached file for this torrent :('
                          ' \nCode: {} - {}'.format(e.code, e.reason),
                          color='ERROR')
        else:
            open(file, 'wb').write(torrent)
            printer.print('Saved {:X} in {}'.format(info_hash, file))


def save_magnets(printer, chosen_links, results, folder):
    for link in chosen_links:
        magnet = results[link]['magnet']
        name = re.search(r'dn=([^\&]*)', magnet)
        torrent_name = parse.unquote(name.group(1)).replace('+', ' ')
        info_hash = int(re.search(r'btih:([a-f0-9]{40})', magnet).group(1), 16)
        torrent_name = torrent_name.replace('/', '_').replace('\\', '_')
        file = os.path.join(folder,  torrent_name + '.magnet')

        printer.print('Saved {:X} in {}'.format(info_hash, file))
        with open(file, 'w') as f:
            f.write(magnet + '\n')


def copy_magnets(printer, chosen_links, results):
    clipboard_text = ''
    for link in chosen_links:
        magnet = results[link]['magnet']
        info_hash = int(re.search(r'btih:([a-f0-9]{40})', magnet).group(1), 16)
        clipboard_text += magnet + "\n"
        printer.print('Copying {:X} to clipboard'.format(info_hash))

    pyperclip.copy(clipboard_text)
