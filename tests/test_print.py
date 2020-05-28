#!/usr/bin/env python3
import os
import unittest
import json
import sys

from unittest.mock import patch, call, MagicMock
from pirate.print import Printer


class TestPrint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # needed to display the results table
        os.environ['COLUMNS'] = '80'

    def test_print_results_remote(self):
        class MockTable:
            add_row = MagicMock()
            align = {}
        mock = MockTable()
        printer = Printer(False)
        printer.print = MagicMock()
        with patch('veryprettytable.VeryPrettyTable',
                   return_value=mock) as prettytable:
            results = [{
                'name': 'name',
                'seeders': 1,
                'leechers': 2,
                'size': '3.0 MiB',
                'uploaded': 'never'
            }]
            printer.search_results(results)
            prettytable.assert_called_once_with([
                'LINK', 'SEED', 'LEECH', 'RATIO',
                'SIZE', 'UPLOAD', 'NAME'])
            mock.add_row.assert_has_calls([
                call([0, 1, 2, '0.5', '3.0 MiB', 'never', 'name'])])

    def test_print_results_local(self):
        class MockTable:
            add_row = MagicMock()
            align = {}
        mock = MockTable()
        printer = Printer(False)
        printer.print = MagicMock()
        with patch('veryprettytable.VeryPrettyTable',
                   return_value=mock) as prettytable:
            results = [{
                'name': 'name1',
                'date': '1',
                'size': '1',
            }, {
                'name': 'name2',
                'date': '2',
                'size': '2',
            }]
            printer.search_results(results, local=True)
            prettytable.assert_called_once_with(
                ['LINK', 'DATE', 'SIZE', 'NAME'])
            mock.add_row.assert_has_calls(
                [call([0, '1', '1', 'name1']), call([1, '2', '2', 'name2'])])

    def test_print_color(self):
        printer = Printer(False)
        with patch('pirate.print.builtins.print') as mock_print:
            printer.print('abc', color='zebra_1')
            mock_print.assert_called_once_with(
                'abc',
                file=sys.stderr)
        printer = Printer(True)
        with patch('pirate.print.builtins.print') as mock_print:
            printer.print('abc', color='zebra_1')
            mock_print.assert_called_once_with(
                '\x1b[34mabc', '\x1b[0m',
                file=sys.stderr)

    def test_print_results_local2(self):
        class MockTable:
            add_row = MagicMock()
            align = {}
        mock = MockTable()
        printer = Printer(True)
        printer.print = MagicMock()
        with patch('veryprettytable.VeryPrettyTable',
                   return_value=mock) as prettytable:
            results = [{
                'name': 'name1',
                'date': '1',
                'size': '1',
            }, {
                'name': 'name2',
                'date': '2',
                'size': '2',
            }]
            printer.search_results(results, local=True)
            prettytable.assert_called_once_with(
                ['LINK', 'DATE', 'SIZE', 'NAME'])
            mock.add_row.assert_has_calls([
                call([0, '1', '1', 'name1']),
                call([1, '2', '2', 'name2'], fore_color='blue')])

    def test_print_descriptions(self):
        printer = Printer(False)
        printer.print = MagicMock()

        class MockRequest():
            add_header = MagicMock()
        request_obj = MockRequest()

        class MockResponse():
            read = MagicMock(return_value=json.dumps(
                {'name': 'cool torrent',
                 'descr': 'A fake torrent.\n'}))
            info = MagicMock()
        response_obj = MockResponse()

        with patch('urllib.request.Request', return_value=request_obj):
            with patch('urllib.request.urlopen',
                       return_value=response_obj):
                printer.descriptions([0], [{'id': '1', 'name': 'name'}],
                                     'example.com', 9)
                printer.print.assert_has_calls([
                    call('Description for "name":', color='zebra_1'),
                    call('A fake torrent.\n', color='zebra_0')])

    def test_print_file_lists(self):
        printer = Printer(False)
        printer.print = MagicMock()

        class MockRequest():
            add_header = MagicMock()
            info = MagicMock()
        request_obj = MockRequest()

        class MockResponse():
            read = MagicMock(return_value=json.dumps(
                [{'name': ['readme.txt'], 'size': [16]},
                 {'name': ['a.mkv'], 'size': [677739464]},
                 {'name': ['b.nfo'], 'size': [61]}]))
            info = MagicMock()
        response_obj = MockResponse()

        with patch('urllib.request.Request',
                   return_value=request_obj):
            with patch('urllib.request.urlopen',
                       return_value=response_obj):
                printer.file_lists([0], [{'id': '1', 'name': 'name'}],
                                   'example.com', 9)
                printer.print.assert_has_calls([
                    call('Files in name:', color='zebra_1'),
                    call('       16 B readme.txt', color='zebra_0'),
                    call('  646.3 MiB a.mkv', color='zebra_1'),
                    call('       61 B b.nfo', color='zebra_0')])


if __name__ == '__main__':
    unittest.main()
