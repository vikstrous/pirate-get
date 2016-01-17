import sys
from distutils.version import LooseVersion
if LooseVersion(sys.version) < LooseVersion("3.4.0"):
    print("At least python 3.4.0 required. Your version is "+sys.version)
    sys.exit(1)

import re
import os
import argparse
import subprocess
import configparser
import socket
import urllib.request as request
import urllib.error
import builtins
from collections import OrderedDict

import webbrowser

import pirate.data
import pirate.torrent
import pirate.local

from os.path import expanduser, expandvars
from pirate.print import Printer


def parse_config_file(text):
    config = configparser.RawConfigParser()

    # default options
    config.add_section('Save')
    config.set('Save', 'magnets', 'false')
    config.set('Save', 'torrents', 'false')
    config.set('Save', 'directory', os.getcwd())

    config.add_section('LocalDB')
    config.set('LocalDB', 'enabled', 'false')
    config.set('LocalDB', 'path', expanduser('~/downloads/pirate-get/db'))

    config.add_section('Misc')
    # TODO: try to use https://docs.python.org/3/library/configparser.html#configparser.BasicInterpolation for interpolating in the command
    config.set('Misc', 'openCommand', '')
    config.set('Misc', 'transmission', 'false')
    config.set('Misc', 'colors', 'true')

    # Additional mirror that work for the user.
    config.add_section('Mirror')
    config.set('Mirror', 'url', 'https://thepiratebay.mn')

    config.read_string(text)

    # expand env variables
    directory = expanduser(expandvars(config.get('Save', 'Directory')))
    path = expanduser(expandvars(config.get('LocalDB', 'path')))

    config.set('Save', 'Directory', directory)
    config.set('LocalDB', 'path', path)

    return config


def load_config():
    # user-defined config files
    main = expandvars('$XDG_CONFIG_HOME/pirate-get')
    alt = expanduser('~/.config/pirate-get')

    # read config file
    if os.path.isfile(main):
        with open(main) as f:
            return parse_config_file(f.read())

    if os.path.isfile(alt):
        with open(alt) as f:
            return parse_config_file(f.read())

    return parse_config_file("")


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


def parse_torrent_command(l):
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
    choices = [elem for elem in choices]
    return code, choices


def parse_args(args_in):
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
    parser.add_argument('-p', dest='pages', default=1, type=int,
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
    parser.add_argument('--mirror', dest='mirror',
                        help='url of a pirate bay mirror. It will be tried first.')

    args = parser.parse_args(args_in)

    return args


def combine_configs(config, args):
    # figure out the action - browse, search, top, etc.
    if args.browse:
        args.action = 'browse'
    elif args.recent:
        args.action = 'recent'
    elif args.list_categories:
        args.action = 'list_categories'
    elif args.list_sorts:
        args.action = 'list_sorts'
    elif len(args.search) == 0:
        args.action = 'top'
    else:
        args.action = 'search'

    args.source = 'tpb'
    if args.database or config.getboolean('LocalDB', 'enabled'):
        args.source = 'local_tpb'

    if not args.database:
        args.database = config.get('LocalDB', 'path')

    if not args.color or not config.getboolean('Misc', 'colors'):
        # TODO: consider how this can be moved to the args
        pirate.data.colored_output = False

    if not args.save_directory:
        args.save_directory = config.get('Save', 'directory')

    args.transmission_command = ['transmission-remote']
    if args.port:
        args.transmission_command.append(args.port)

    args.output = 'browser_open'
    if args.transmission or config.getboolean('Misc', 'transmission'):
        args.output = 'transmission'
    elif args.save_magnets or config.getboolean('Save', 'magnets'):
        args.output = 'save_magnet_files'
    elif args.save_torrents or config.getboolean('Save', 'torrents'):
        args.output = 'save_torrent_files'
    elif args.command or config.get('Misc', 'openCommand'):
        args.output = 'open_command'

    args.open_command = args.command
    if not args.open_command:
        args.open_command = config.get('Misc', 'openCommand')

    if not args.mirror and config.get('Mirror', 'url'):
        args.mirror = config.get('Mirror', 'url')

    return args


def search_on_mirror(printer, pages, category, sort, action, search, mirror):

    try:
        printer.print('Trying', mirror, end='... \n')
        results = pirate.torrent.remote(
            printer=printer,
            pages=pages,
            category=pirate.torrent.parse_category(printer, category),
            sort=pirate.torrent.parse_sort(printer, sort),
            mode=action,
            terms=search,
            mirror=mirror
        )
    except (urllib.error.URLError, socket.timeout,
            IOError, ValueError):
        printer.print('Failed', color='WARN')
    else:
        printer.print('Ok', color='alt')
        return results, mirror

    return [], None

def search_mirrors(printer, pages, category, sort, action, search, mirror):
    """Search on our mirror first. If not, get a mirror list and try again.
    Return a tuple results, url of the working mirror.
    """

    # Search on our mirror, or the default one.
    if not mirror:
        mirror = pirate.data.MIRROR_DEFAULT

    results, mirror = search_on_mirror(printer, pages, category, sort, action, search, mirror)
    if results:
        return results, mirror

    # If the default mirror failed, get some mirrors.
    mirror_sources = [pirate.data.MIRROR_SOURCE]
    for mirror_source in mirror_sources:
        mirrors = OrderedDict()
        try:
            req = request.Request(mirror_source,
                                    headers=pirate.data.default_headers)
            f = request.urlopen(req, timeout=pirate.data.default_timeout)
        except IOError:
            printer.print('Could not fetch additional mirrors', color='WARN')
        else:
            if f.getcode() != 200:
                raise IOError('The proxy bay responded with an error.')
            # Parse the list of mirrors
            for mirror in [i.decode('utf-8').strip() for i in f.readlines()][3:]:
                mirrors[mirror] = None
        for mirror in pirate.data.blacklist:
            if mirror in mirrors:
                del mirrors[mirror]

        if mirrors:
            results = []
            while not results:
                results, mirror = search_on_mirror(printer, pages, category, sort, action, search, mirror)

            return results, mirror

        else:
            printer.print('No available mirrors :(', color='WARN')
            return [], None

def pirate_main(args):
    printer = Printer(args.color)

    # check it transmission is running
    if args.transmission:
        ret = subprocess.call(args.transmission_command + ['-l'],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        if ret != 0:
            printer.print('Transmission is not running.')
            sys.exit(1)

    # non-torrent fetching actions

    if args.action == 'list_categories':
        cur_color = 'zebra_0'
        for key, value in sorted(pirate.data.categories.items()):
            cur_color = 'zebra_0' if cur_color == 'zebra_1' else 'zebra_1'
            printer.print(str(value), '\t', key, sep='', color=cur_color)
        return

    if args.action == 'list_sorts':
        cur_color = 'zebra_0'
        for key, value in sorted(pirate.data.sorts.items()):
            cur_color = 'zebra_0' if cur_color == 'zebra_1' else 'zebra_1'
            printer.print(str(value), '\t', key, sep='', color=cur_color)
        return

    # fetch torrents

    if args.source == 'local_tpb':
        results = pirate.local.search(args.database, args.search)
    elif args.source == 'tpb':
        results, site = search_mirrors(printer, args.pages, args.category,
                                       args.sort, args.action, args.search,
                                       args.mirror)

    if len(results) == 0:
        printer.print('No results')
        return

    printer.search_results(results, local=args.source == 'local_tpb')

    # number of results to pick
    if args.first:
        printer.print('Choosing first result')
        choices = [0]
    elif args.download_all:
        printer.print('Downloading all results')
        choices = range(len(results))
    else:
        # interactive loop for per-torrent actions
        while True:
            printer.print("\nSelect links (Type 'h' for more options"
                  ", 'q' to quit)", end='\b', color='alt')
            try:
                l = builtins.input(': ')
            except (KeyboardInterrupt, EOFError):
                printer.print('\nCancelled.')
                return

            try:
                code, choices = parse_torrent_command(l)
                # Act on option, if supplied
                printer.print('')
                if code == 'h':
                    printer.print('Options:',
                          '<links>: Download selected torrents',
                          '[m<links>]: Save magnets as files',
                          '[t<links>]: Save .torrent files',
                          '[d<links>]: Get descriptions',
                          '[f<links>]: Get files',
                          '[p] Print search results',
                          '[q] Quit', sep='\n')
                elif code == 'q':
                    printer.print('Bye.', color='alt')
                    return
                elif code == 'd':
                    printer.descriptions(choices, results, site)
                elif code == 'f':
                    printer.file_lists(choices, results, site)
                elif code == 'p':
                    printer.search_results(results)
                elif code == 'm':
                    pirate.torrent.save_magnets(printer, choices, results, args.save_directory)
                elif code == 't':
                    pirate.torrent.save_torrents(printer, choices, results, args.save_directory)
                elif not l:
                    printer.print('No links entered!', color='WARN')
                else:
                    break
            except Exception as e:
                printer.print('Exception:', e, color='ERROR')
                return

    # output

    if args.output == 'save_magnet_files':
        printer.print('Saving selected magnets...')
        pirate.torrent.save_magnets(choices, results, args.save_directory)
        return

    if args.output == 'save_torrent_files':
        printer.print('Saving selected torrents...')
        pirate.torrent.save_torrents(choices, results, args.save_directory)
        return

    for choice in choices:
        url = results[choice]['magnet']

        if args.output == 'transmission':
            subprocess.call(args.transmission_command + ['--add', url])
        elif args.output == 'open_command':
            cmd = parse_cmd(args.open_command, url)
            printer.print(" ".join(cmd))
            subprocess.call(cmd)
        elif args.output == 'browser_open':
            webbrowser.open(url)

    if args.output == 'transmission':
        subprocess.call(args.transmission_command + ['-l'])


def main():
    args = combine_configs(load_config(), parse_args(sys.argv[1:]))
    pirate_main(args)


if __name__ == '__main__':
    main()
