import sys
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
    # TODO: try to use configparser.BasicInterpolation
    #       for interpolating in the command
    config.set('Misc', 'openCommand', '')
    config.set('Misc', 'transmission', 'false')
    config.set('Misc', 'colors', 'true')
    config.set('Misc', 'mirror', pirate.data.default_mirror)

    config.read_string(text)

    # expand env variables
    directory = expanduser(expandvars(config.get('Save', 'Directory')))
    path = expanduser(expandvars(config.get('LocalDB', 'path')))

    config.set('Save', 'Directory', directory)
    config.set('LocalDB', 'path', path)

    return config


def load_config():
    # user-defined config files
    config_home = os.getenv('XDG_CONFIG_HOME', '~/.config')
    config = expanduser(os.path.join(config_home, 'pirate-get'))

    # read config file
    if os.path.isfile(config):
        with open(config) as f:
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
    parser.add_argument('-A', '--auth', dest='auth',
            help='transmission-remote rpc authentication, <user:pw>')
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
    parser.add_argument('--disable-colors', dest='disable_color',
                        action='store_true',
                        help='disable colored output')
    parser.add_argument('-m', '--mirror',
                        type=str, nargs='+',
                        help='the pirate bay mirror(s) to use')
    parser.add_argument('-v', '--version',
                        action='store_true',
                        help='print pirate-get version number')
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

    if args.disable_color or config.getboolean('Misc', 'colors') == False:
        args.color = False
    else:
        args.color = True

    if not args.save_directory:
        args.save_directory = config.get('Save', 'directory')

    if not args.mirror:
        args.mirror = config.get('Misc', 'mirror').split()

    args.transmission_command = ['transmission-remote']
    if args.port:
        args.transmission_command.append(args.port)
    if args.auth:
        args.transmission_command.append('--auth')
        args.transmission_command.append(args.auth)

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

    return args


def connect_mirror(mirror, printer, args):
    try:
        printer.print('Trying', mirror, end='... ')
        results = pirate.torrent.remote(
            printer=printer,
            pages=args.pages,
            category=pirate.torrent.parse_category(printer, args.category),
            sort=pirate.torrent.parse_sort(printer, args.sort),
            mode=args.action,
            terms=args.search,
            mirror=mirror)
    except (urllib.error.URLError, socket.timeout, IOError, ValueError):
        printer.print('Failed', color='WARN')
        return None
    else:
        printer.print('Ok', color='alt')
        return results, mirror


def search_mirrors(printer, args):
    # try default or user mirrors
    for mirror in args.mirror:
        result = connect_mirror(mirror, printer, args)
        if result:
            return result

    # download mirror list
    try:
        req = request.Request(pirate.data.mirror_list,
                              headers=pirate.data.default_headers)
        f = request.urlopen(req, timeout=pirate.data.default_timeout)
    except urllib.error.URLError as e:
        raise IOError('Could not fetch mirrors', e.reason)

    if f.getcode() != 200:
        raise IOError('The proxy bay responded with an error',
                      f.read().decode('utf-8'))

    mirrors = [i.decode('utf-8').strip() for i in f.readlines()][3:]

    # try mirrors
    for mirror in mirrors:
        if mirror in pirate.data.blacklist:
            continue
        result = connect_mirror(mirror, printer, args)
        if result:
            return result
    else:
        raise IOError('No more available mirrors')


def pirate_main(args):
    printer = Printer(args.color)

    # print version
    if args.version:
        printer.print('pirate-get, version {}'.format(pirate.data.version))
        sys.exit(0)

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
        if os.path.isfile(args.database):
            results = pirate.local.search(args.database, args.search)
        else:
            printer.print("Local pirate bay database doesn't exist.",
                          '(%s)' % args.database, color='ERROR')
            sys.exit(1)
    elif args.source == 'tpb':
        try:
            results, site = search_mirrors(printer, args)
        except IOError as e:
            printer.print(e.args[0] + ' :( ', color='ERROR')
            if len(e.args) > 1:
                printer.print(e.args[1])
            sys.exit(1)

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
                    pirate.torrent.save_magnets(printer, choices, results,
                                                args.save_directory)
                elif code == 't':
                    pirate.torrent.save_torrents(printer, choices, results,
                                                 args.save_directory)
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
        pirate.torrent.save_magnets(printer, choices, results, args.save_directory)
        return

    if args.output == 'save_torrent_files':
        printer.print('Saving selected torrents...')
        pirate.torrent.save_torrents(printer, choices, results, args.save_directory)
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
