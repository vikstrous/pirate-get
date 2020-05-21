#!/usr/bin/env python3
import socket
import unittest
from argparse import Namespace
from unittest import mock
from unittest.mock import patch, call, MagicMock

import pirate.pirate
import pirate.data
from pirate.print import Printer


class TestPirate(unittest.TestCase):

    def test_parse_cmd(self):
        tests = [
            [['abc', ''], ['abc']],
            [['abc %s', 'url'], ['abc', 'url']],
            [['abc "%s"', 'url'], ['abc', 'url']],
            [["abc \'%s\'", 'url'], ['abc', 'url']],
            [['abc bash -c "\'%s\'"', 'url'], ['abc', 'bash', '-c', "'url'"]],
            [['abc %s %s', 'url'], ['abc', 'url', 'url']],
        ]
        for test in tests:
            self.assertEqual(pirate.pirate.parse_cmd(*test[0]), test[1])

    @patch('subprocess.call')
    def test_main(self, mock_call):
        result = {
            'name': 'derp',
            'magnet': 'magnet:?xt=urn:btih:deadbeef&dn=derp',
            'seeders': '1',
            'leechers': '1',
            'size': '1 MB',
            'uploaded': '1',
        }
        with patch('pirate.pirate.connect_mirror',
                   return_value=([result], '')):
            config = pirate.pirate.parse_config_file('')
            args = pirate.pirate.combine_configs(
                config,
                pirate.pirate.parse_args(['-0', 'term', '-C', 'blah %s']))
            pirate.pirate.pirate_main(args)
            mock_call.assert_called_once_with(
                ['blah', 'magnet:?xt=urn:btih:deadbeef&dn=derp'])

    @patch('pirate.pirate.builtins.input', return_value='0')
    @patch('subprocess.call')
    def test_main_choice(self, mock_call, mock_input):
        result = {
            'name': 'derp',
            'magnet': 'magnet:?xt=urn:btih:deadbeef&dn=derp',
            'seeders': '1',
            'leechers': '1',
            'size': '1 MB',
            'uploaded': '1',
        }
        with patch('pirate.pirate.connect_mirror',
                   return_value=([result], '')):
            config = pirate.pirate.parse_config_file('')
            args = pirate.pirate.combine_configs(
                config, pirate.pirate.parse_args(['term', '-C', 'blah %s']))
            pirate.pirate.pirate_main(args)
            mock_call.assert_called_once_with(
                ['blah', 'magnet:?xt=urn:btih:deadbeef&dn=derp'])

    def test_parse_torrent_command(self):
        tests = [
            [['h'], ('h', [])],
            [['q'], ('q', [])],
            [['d1'], ('d', [1])],
            [['f1'], ('f', [1])],
            [['p1'], ('p', [1])],
            [['t1'], ('t', [1])],
            [['m1'], ('m', [1])],
            [['d 23'], ('d', [23])],
            [['d 23,1'], ('d', [23, 1])],
            [['d 23, 1'], ('d', [23, 1])],
            [['1d'], ('d', [1])],
            [['1 ... d'], ('d', [1])],
            [['1-3 d'], ('d', [1, 2, 3])],
            [['1-3'], (None, [1, 2, 3])],
        ]
        for test in tests:
            self.assertEqual(
                pirate.pirate.parse_torrent_command(*test[0]),
                test[1])

    def test_parse_config_file(self):
        types = {
            'Save': {
                'magnets': bool,
                'Magnets': bool,
                'torrents': bool,
                'directory': str,
            },
            'LocalDB': {
                'enabled': bool,
                'path': str,
            }
        }
        config1 = """
        [Save]
        magnets=False
        directory=dir
        [LocalDB]
        enabled=true
        path=abc
        """
        config2 = """
        [Save]
        Magnets=True
        """
        tests = [
            (config1, {'Save': {'magnets': False}}),
            (config1, {'Save': {'torrents': False}}),
            (config1, {'Save': {'directory': 'dir'}}),
            (config1, {'LocalDB': {'enabled': True}}),
            (config1, {'LocalDB': {'path': 'abc'}}),
            (config2, {'Save': {'magnets': True}}),
        ]
        for test in tests:
            config = pirate.pirate.parse_config_file(test[0])
            for section in test[1].keys():
                for name in test[1][section].keys():
                    if types[section][name] == bool:
                        lhs = config.getboolean(section, name)
                    else:
                        lhs = config.get(section, name)
                    rhs = test[1][section][name]
                    self.assertEqual(lhs, rhs)

    def test_parse_args(self):
        tests = [
            ('', ['-b'], {'action': 'browse'}),
            ('', [], {'action': 'top'}),
            ('', ['-R'], {'action': 'recent'}),
            ('', ['-l'], {'action': 'list_categories'}),
            ('', ['--list_sorts'], {'action': 'list_sorts'}),
            ('', ['term'], {'action': 'search', 'source': 'tpb'}),
            ('',
             ['-L', 'filename', 'term'],
             {'action': 'search', 'source': 'local_tpb',
              'database': 'filename'}),
            ('',
             ['term', '-S', 'dir'],
             {'action': 'search', 'save_directory': 'dir'}),
            ('',
             ['-E', 'localhost:1337'],
             {'transmission_command':
              ['transmission-remote', 'localhost:1337']}),
            ('', ['term'], {'output': 'browser_open'}),
            ('', ['term', '-t'], {'output': 'transmission'}),
            ('', ['term', '--save-magnets'], {'output': 'save_magnet_files'}),
            ('',
             ['term', '-C', 'command'],
             {'output': 'open_command', 'open_command': 'command'}),
            ('', ['internets'], {'action': 'search', 'search': ['internets']}),
            ('',
             ['term', '--save-torrents'],
             {'output': 'save_torrent_files'}),
            ('',
             ['internets lol', 'lel'],
             {'action': 'search', 'search': ['internets lol', 'lel']}),
        ]
        for test in tests:
            args = pirate.pirate.parse_args(test[1])
            config = pirate.pirate.parse_config_file(test[0])
            args = pirate.pirate.combine_configs(config, args)
            for option in test[2].keys():
                value = getattr(args, option)
                self.assertEqual(test[2][option], value)

    def test_search_mirrors(self):
        args = Namespace(
            category=100, sort=10,
            action='browse', search=[],
            mirror=[pirate.data.default_mirror],
            timeout=pirate.data.default_timeout)

        class MockResponse():
            readlines = mock.MagicMock(
                return_value=[
                    x.encode('utf-8') for x in
                    ['', '', '', 'https://example.com']])
            info = mock.MagicMock()
            getcode = mock.MagicMock(return_value=200)
        response_obj = MockResponse()

        returns = [None, ([], 'https://example.com')]

        printer = MagicMock(Printer)
        with patch('pirate.pirate.connect_mirror',
                   side_effect=returns) as connect:
            with patch('urllib.request.urlopen', return_value=response_obj):
                results, mirror = pirate.pirate.search_mirrors(printer, args)

        connect.assert_has_calls([
            call(pirate.data.default_mirror, printer, args),
            call('https://example.com', printer, args)])

        self.assertEqual(results, [])
        self.assertEqual(mirror, 'https://example.com')


if __name__ == '__main__':
    unittest.main()
