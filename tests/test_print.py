#!/usr/bin/env python3
import unittest
from unittest.mock import patch
from unittest.mock import call

import pirate.print


class TestPrint(unittest.TestCase):

    def test_print_results(self):
        with patch('pirate.print.print') as mock:
            results = [{
                'magnet': 'dn=name',
                'seeds': 1,
                'leechers': 2,
                'size': ['3','MiB'],
                'uploaded': 'never'
            }]
            pirate.print.search_results(results)
            actual = mock.call_args_list
            expected = [
                call('LINK   SEED  LEECH  RATIO  SIZE       UPLOAD       NAME                        ', color='header'),
                call('   0      1      2    0.5    3.0 MiB  never        name                        ', color='zebra_1'),
            ]
            self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()
