#!/usr/bin/env python3
import unittest
from unittest.mock import patch, call, MagicMock

from pirate.print import Printer


class TestPrint(unittest.TestCase):

    def test_print_results_remote(self):
        class MockTable:
            add_row = MagicMock()
            align = {}
        mock = MockTable()
        printer = Printer(False)
        printer.print = MagicMock()
        with patch('veryprettytable.VeryPrettyTable', return_value=mock) as prettytable:
            results = [{
                'magnet': 'dn=name',
                'seeds': 1,
                'leechers': 2,
                'size': ['3','MiB'],
                'uploaded': 'never'
            }]
            printer.search_results(results)
            prettytable.assert_called_once_with(['LINK', 'SEED', 'LEECH', 'RATIO', 'SIZE', '', 'UPLOAD', 'NAME'])
            mock.add_row.assert_has_calls([call([0, 1, 2, '0.5', '3.0', 'MiB', 'never', 'name'])])

    def test_print_results_local(self):
        class MockTable:
            add_row = MagicMock()
            align = {}
        mock = MockTable()
        printer = Printer(False)
        printer.print = MagicMock()
        with patch('veryprettytable.VeryPrettyTable', return_value=mock) as prettytable:
            results = [{
                'magnet': 'dn=name',
                'Name': 'name',
            },{
                'magnet': 'dn=name2',
                'Name': 'name2',
            }]
            printer.search_results(results, local=True)
            prettytable.assert_called_once_with(['LINK', 'NAME'])
            mock.add_row.assert_has_calls([call([0, 'name']), call([1, 'name2'])])

    def test_print_color(self):
        printer = Printer(False)
        with patch('pirate.print.builtins.print') as mock_print:
            printer.print('abc', color='zebra_1')
            mock_print.assert_called_once_with('abc')
        printer = Printer(True)
        with patch('pirate.print.builtins.print') as mock_print:
            printer.print('abc', color='zebra_1')
            mock_print.assert_called_once_with('\x1b[34mabc', '\x1b[0m')

    def test_print_results_local(self):
        class MockTable:
            add_row = MagicMock()
            align = {}
        mock = MockTable()
        printer = Printer(True)
        printer.print = MagicMock()
        with patch('veryprettytable.VeryPrettyTable', return_value=mock) as prettytable:
            results = [{
                'magnet': 'dn=name',
                'Name': 'name',
            },{
                'magnet': 'dn=name2',
                'Name': 'name2',
            }]
            printer.search_results(results, local=True)
            prettytable.assert_called_once_with(['LINK', 'NAME'])
            mock.add_row.assert_has_calls([call([0, 'name']), call([1, 'name2'], fore_color='blue')])

    def test_print_descriptions(self):
        printer = Printer(False)
        printer.print = MagicMock()
        class MockRequest():
            add_header = MagicMock()
        request_obj = MockRequest()
        class MockResponse():
            read = MagicMock(return_value='<html><div class="nfo"><pre>stuff <a href="href">link</a></pre></div></html>'.encode('utf8'))
            info = MagicMock()
        response_obj = MockResponse()
        with patch('urllib.request.Request', return_value=request_obj) as request:
            with patch('urllib.request.urlopen', return_value=response_obj) as urlopen:
                printer.descriptions([0], [{'id': '1', 'magnet': 'dn=name'}], 'example.com')
                printer.print.assert_has_calls([call('Description for "name":', color='zebra_1'),call('stuff [link](href)', color='zebra_0')])

    def test_print_file_lists(self):
        printer = Printer(False)
        printer.print = MagicMock()
        class MockRequest():
            add_header = MagicMock()
        request_obj = MockRequest()
        class MockResponse():
            read = MagicMock(return_value='<html><tr><td align="left">1.</td><td align="right">filename</tr></html>'.encode('utf8'))
            info = MagicMock()
        response_obj = MockResponse()
        with patch('urllib.request.Request', return_value=request_obj) as request:
            with patch('urllib.request.urlopen', return_value=response_obj) as urlopen:
                printer.file_lists([0], [{'id': '1', 'magnet': 'dn=name'}], 'example.com')
                printer.print.assert_has_calls([call('Files in "name":', color='zebra_1'),call('         1.  filename', color='zebra_0')])

if __name__ == '__main__':
    unittest.main()
