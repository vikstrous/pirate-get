#!/usr/bin/env python3
import unittest
from unittest.mock import patch, call, MagicMock

import pirate.print


class TestPrint(unittest.TestCase):

    def test_print_results(self):
        class MockTable:
            add_row = MagicMock()
            align = {}
        mock = MockTable()
        with patch('prettytable.PrettyTable', return_value=mock) as prettytable:
            results = [{
                'magnet': 'dn=name',
                'seeds': 1,
                'leechers': 2,
                'size': ['3','MiB'],
                'uploaded': 'never'
            }]
            pirate.print.search_results(results)
            prettytable.assert_called_once_with(['LINK', 'SEED', 'LEECH', 'RATIO', 'SIZE', '', 'UPLOAD', 'NAME'])
            mock.add_row.assert_has_calls([call([0, 1, 2, '0.5', '3.0', 'MiB', 'never', 'name'])])

    def test_print_results(self):
        class MockTable:
            add_row = MagicMock()
            align = {}
        mock = MockTable()
        with patch('veryprettytable.VeryPrettyTable', return_value=mock) as prettytable:
            results = [{
                'magnet': 'dn=name',
                'Name': 'name',
            }]
            pirate.print.search_results(results, local=True)
            prettytable.assert_called_once_with(['LINK', 'NAME'])
            mock.add_row.assert_has_calls([call([0, 'name'])])

if __name__ == '__main__':
    unittest.main()
