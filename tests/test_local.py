#!/usr/bin/env python3
import unittest
import pirate.local
import os
import base64

from tests import util


class TestLocal(unittest.TestCase):

    def test_local_csv_db(self):
        path = util.data_path('db.csv')
        expected = [
                {
                    'date':'2018-May-14 11:05:31',
                    'magnet': 'magnet:?xt=urn:btih:34930674EF3BB9317FB5F263CCA830F52685235B&dn=ubuntu-14.04.5-desktop-amd64.iso',
                    'size': '1.0 GiB',
                },
                {
                    'date': '2018-Apr-15 00:04:09',
                    'magnet': 'magnet:?xt=urn:btih:F07E0B0584745B7BCB35E98097488D34E68623D0&dn=Ubuntu%2017.10.1%20Desktop%20%28amd64%29',
                    'size': '1.4 GiB',
                },
                {
                    'date': '2017-Aug-01 15:08:07',
                    'magnet': 'magnet:?xt=urn:btih:4096EC129404689CEB8056D907E384FF872C2CE9&dn=LINUX%20UBUNTU%2016.10%2032X64',
                    'size': '1.5 GiB',
                },
            ]
        actual = pirate.local.search(path, ('ubuntu',))
        self.assertEqual(len(actual), len(expected))
        for i in range(len(expected)):
            self.assertDictEqual(actual[i], expected[i])

if __name__ == '__main__':
    unittest.main()
