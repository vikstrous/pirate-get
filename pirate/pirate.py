import re
import os
import argparse
import subprocess
import configparser
import socket
import urllib.request as request
import urllib.error
import webbrowser

import pirate.data
import pirate.torrent
import pirate.local
import pirate.print

from os.path import expanduser, expandvars
from pirate.print import print


def load_config():
    config = configparser.ConfigParser()

    # default options
    config.add_section('Save')
    config.set('Save', 'magnets', 'false')
    config.set('Save', 'torrents', 'false')
    config.set('Save', 'directory', os.getcwd())

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


def parse_cmd(cmd, url):
    cmd_args_regex = r'''(('[^']*'|"[^"]*"|(\\\s|[^\s])+)+ *)'''
    ret = re.findall(cmd_args_regex, cmd)
    ret = [i[0].strip().replace('%s', url) for i in ret]
    ret_no_quotes = []
    for item in ret:
        if ((item[0] == "'" and item[-1] == "'") or
           (item[0] == '"' and item[-1] == '"')):
            ret_no_quotes.append(item[1:-1])
        else:
            ret_no_quotes.append(item)
    return ret_no_quotes


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
    parser.add_argument('-L', '--local', dest='database',
                        help='an xml file containing the Pirate Bay database')
    parser.add_argument('-p', dest='pages', default=1,
                        help='the number of pages to fetch '
                             "(doesn't work with --local)")
    parser.add_argument('-0', dest='first',
                        action='store_true',
                        help='choose the top result')
    parser.add_argument('-a', '--download-all',
                        action='store_true',
                        help='download all results')
    parser.add_argument('-t', '--transmission',
                        action='store_true',
                        help='open magnets with transmission-remote')
    parser.add_argument('-P', '--port', dest='port',
                        help='transmission-remote rpc port. default is 9091')
    parser.add_argument('-C', '--custom', dest='command',
                        help='open magnets with a custom command'
                              ' (%%s will be replaced with the url)')
    parser.add_argument('-M', '--save-magnets',
                        action='store_true',
                        help='save magnets links as files')
    parser.add_argument('-T', '--save-torrents',
                        action='store_true',
                        help='save torrent files')
    parser.add_argument('-S', '--save-directory',
                        type=str, metavar='DIRECTORY',
                        help='directory where to save downloaded files'
                             ' (if none is given $PWD will be used)')
    parser.add_argument('--disable-colors', dest='color',
                        action='store_false',
                        help='disable colored output')
    args = parser.parse_args()

    if (config.getboolean('Misc', 'colors') and not args.color
       or not config.getboolean('Misc', 'colors')):
        pirate.data.colored_output = False

    if args.save_directory:
        config.set('Save', 'directory', args.save_directory)

    transmission_command = ['transmission-remote']
    if args.port:
        transmission_command.append(args.port)

    if args.transmission or config.getboolean('Misc', 'transmission'):
        ret = subprocess.call(transmission_command + ['-l'],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        if ret != 0:
            print('Transmission is not running.')
            return

    if args.list_categories:
        cur_color = 'zebra_0'
        for key, value in sorted(pirate.data.categories.items()):
            cur_color = 'zebra_0' if cur_color == 'zebra_1' else 'zebra_1'
            print(str(value), '\t', key, sep='', color=cur_color)
        return

    if args.list_sorts:
        cur_color = 'zebra_0'
        for key, value in sorted(pirate.data.sorts.items()):
            cur_color = 'zebra_0' if cur_color == 'zebra_1' else 'zebra_1'
            print(str(value), '\t', key, sep='', color=cur_color)
        return

    if args.database or config.getboolean('LocalDB', 'enabled'):
        if args.database:
            path = args.database
        else:
            path = config.get('LocalDB', 'path')
        mags = pirate.local.search(path, args.search)
        sizes, uploaded = [], []

    else:
        mags, mirrors = [], {'https://thepiratebay.mn'}
        try:
            req = request.Request('https://proxybay.co/list.txt',
                                  headers=pirate.data.default_headers)
            f = request.urlopen(req, timeout=pirate.data.default_timeout)
        except IOError:
            print('Could not fetch additional mirrors', color='WARN')
        else:
            if f.getcode() != 200:
                raise IOError('The proxy bay responded with an error.')
            mirrors = mirrors.union([i.decode('utf-8').strip()
                                    for i in f.readlines()][3:]
                                    ).difference(pirate.data.blacklist)

        for mirror in mirrors:
            try:
                print('Trying', mirror, end='... ')
                mags, sizes, uploaded, ids = pirate.torrent.remote(args,
                                                                   mirror)
            except (urllib.error.URLError, socket.timeout,
                    IOError, ValueError):
                print('Failed', color='WARN')
            else:
                site = mirror
                print('Ok', color='alt')
                break
        else:
            print('No available mirrors :(', color='WARN')
            return

    if not mags:
        print('No results')
        return

    pirate.print.search_results(mags, sizes, uploaded, local=args.database)

    if args.first:
        print('Choosing first result')
        choices = [0]
    elif args.download_all:
        print('Downloading all results')
        choices = range(len(mags))
    else:
        # New input loop to support different link options
        while True:
            print("\nSelect links (Type 'h' for more options"
                  ", 'q' to quit)", end='\b', color='alt')
            try:
                l = input(': ')
            except KeyboardInterrupt:
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
                # Substitute multiple consecutive spaces/commas for single
                # comma remove anything that isn't an integer or comma.
                # Turn into list
                l = re.sub(r'^[hdfp, ]*|[hdfp, ]*$', '', l)
                l = re.sub('[ ,]+', ',', l)
                l = re.sub('[^0-9,-]', '', l)
                parsed_input = l.split(',')

                # expand ranges
                choices = []
                # loop will generate a list of lists
                for elem in parsed_input:
                    left, sep, right = elem.partition('-')
                    if right:
                        choices.append(list(range(int(left), int(right) + 1)))
                    elif left != '':
                        choices.append([int(left)])

                # flatten list
                choices = sum(choices, [])
                # the current code stores the choices as strings
                # instead of ints. not sure if necessary
                choices = [str(elem) for elem in choices]

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
                    pirate.print.descriptions(choices, mags, site, ids)
                elif code == 'f':
                    pirate.print.file_lists(choices, mags, site, ids)
                elif code == 'p':
                    pirate.print.search_results(mags, sizes, uploaded)
                elif code == 'm':
                    pirate.torrent.save_magnets(choices, mags, config.get(
                        'Save', 'directory'))
                elif code == 't':
                    pirate.torrent.save_torrents(choices, mags, config.get(
                        'Save', 'directory'))
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
        pirate.torrent.save_magnets(choices, mags, config.get(
            'Save', 'directory'))
        save_to_file = True

    if args.save_torrents or config.getboolean('Save', 'torrents'):
        print('Saving selected torrents...')
        pirate.torrent.save_torrents(choices, mags, config.get(
            'Save', 'directory'))
        save_to_file = True

    if save_to_file:
        return

    for choice in choices:
        url = mags[int(choice)][0]

        if args.transmission or config.getboolean('Misc', 'transmission'):
            subprocess.call(transmission_command + ['--add', url])

        elif args.command or config.get('Misc', 'openCommand'):
            command = config.get('Misc', 'openCommand')
            if args.command:
                command = args.command
            subprocess.call(parse_cmd(command, url))

        else:
            webbrowser.open(url)

    if args.transmission or config.getboolean('Misc', 'transmission'):
        subprocess.call(transmission_command + ['-l'])

if __name__ == '__main__':
    main()
