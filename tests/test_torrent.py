#!/usr/bin/env python3
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
import io
import urllib
import json
import os
import time

import pirate.torrent
import pirate.data
from pirate.print import Printer
from tests import util


class TestTorrent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # to make test deterministic
        os.environ['TZ'] = 'Etc/UTC'
        time.tzset()

    def test_no_hits(self):
        expected = []
        with util.open_data('no_hits.json') as res:
            actual = pirate.torrent.parse_page(res)
        self.assertEqual(actual, expected)

    def test_blocked_mirror(self):
        with util.open_data('blocked.html') as res:
            with self.assertRaises(IOError):
                pirate.torrent.parse_page(res)

    def test_search_results(self):
        with util.open_data('result.json') as file:
            expected = json.load(file)
        with util.open_data('debian_iso.json') as res:
            actual = pirate.torrent.parse_page(res)
        json.dump(actual, open('result.json', 'w'))
        self.assertEqual(actual, expected)

    def test_parse_category(self):
        category = pirate.torrent.parse_category(MagicMock(Printer), 'Audio')
        self.assertEqual(100, category)
        category = pirate.torrent.parse_category(MagicMock(Printer), 'Video')
        self.assertEqual(200, category)
        category = pirate.torrent.parse_category(MagicMock(Printer), '100')
        self.assertEqual(100, category)
        category = pirate.torrent.parse_category(MagicMock(Printer), 'asdf')
        self.assertEqual(0, category)
        category = pirate.torrent.parse_category(MagicMock(Printer), '9001')
        self.assertEqual(0, category)

    def test_parse_sort(self):
        sort = pirate.torrent.parse_sort(MagicMock(Printer), 'SeedersDsc')
        self.assertEqual(['seeders', True], sort)
        sort = pirate.torrent.parse_sort(MagicMock(Printer), 'CategoryAsc')
        self.assertEqual(['category', False], sort)
        sort = pirate.torrent.parse_sort(MagicMock(Printer), 'DateAsc')
        self.assertEqual(['raw_uploaded', False], sort)
        sort = pirate.torrent.parse_sort(MagicMock(Printer), '7')
        self.assertEqual(['seeders', True], sort)
        sort = pirate.torrent.parse_sort(MagicMock(Printer), 'asdf')
        self.assertEqual(['seeders', True], sort)
        sort = pirate.torrent.parse_sort(MagicMock(Printer), '7000')
        self.assertEqual(['seeders', True], sort)

    def test_request_path(self):
        # the args are (mode, category, terms)
        succeed = [
            (('recent', 1,   0, []), '/precompiled/data_top100_recent_1.json'),
            (('recent', 2, 100, []), '/precompiled/data_top100_recent_2.json'),
            (('top',    1,   0, []), '/precompiled/data_top100_all.json'),
            (('top',    1, 100, []), '/precompiled/data_top100_100.json'),
            (('search', 1, 100, ['abc']), '/q.php?q=abc&cat=100'),
            (('search', 1, 100, ['abc', 'def']), '/q.php?q=abc%20def&cat=100'),
            (('search', 1, 100, ['\u1234']), '/q.php?q=%E1%88%B4&cat=100'),
            (('browse', 1, 100, []), '/q.php?q=category%3A100'),
        ]
        fail = [
            (('browse', 1,   0, []), Exception),
            (('asdf',   1, 100, []), Exception)
        ]
        for inp, out in succeed:
            path = pirate.torrent.build_request_path(*inp)
            self.assertEqual(out, path)
        for inp, out, in fail:
            with self.assertRaises(out):
                pirate.torrent.build_request_path(*inp)

    @patch('pirate.torrent.get_torrent')
    def test_save_torrents(self, get_torrent):
        with patch('pirate.torrent.open',
                   mock.mock_open(), create=True) as open_:
            pirate.torrent.save_torrents(
                MagicMock(Printer), [0],
                [{'name': 'cool torrent',
                  'info_hash': 3735928559,
                  'magnet': 'magnet:?xt=urn:btih:deadbeef'}], 'path', 9)
            get_torrent.assert_called_once_with(3735928559, 9)
            open_.assert_called_once_with('path/cool torrent.torrent', 'wb')

    @patch('pirate.torrent.get_torrent',
           side_effect=urllib.error.HTTPError('', '', '', '', io.StringIO()))
    def test_save_torrents_fail(self, get_torrent):
        pirate.torrent.save_torrents(
            MagicMock(Printer), [0],
            [{'name': 'cool torrent',
              'info_hash': 3735928559,
              'magnet': 'magnet:?xt=urn:btih:deadbeef'}], 'path', 9)

    def test_save_magnets(self):
        with patch('pirate.torrent.open',
                   mock.mock_open(), create=True) as open_:
            pirate.torrent.save_magnets(
                MagicMock(Printer), [0],
                [{'name': 'cool torrent',
                  'info_hash': 3735928559,
                  'magnet': 'magnet:?xt=urn:btih:deadbeef'}], 'path')
            open_.assert_called_once_with('path/cool torrent.magnet', 'w')

    @patch('urllib.request.urlopen')
    def test_get_torrent(self, urlopen):
        class MockRequest():
            add_header = mock.MagicMock()
        request_obj = MockRequest()
        with patch('urllib.request.Request', return_value=request_obj) as req:
            pirate.torrent.get_torrent(100000000000000, 9)
            req.assert_called_once_with(
                'http://itorrents.org/torrent/5AF3107A4000.torrent',
                headers=pirate.data.default_headers)
            urlopen.assert_called_once_with(
                request_obj,
                timeout=9)

    def test_remote(self):
        class MockRequest():
            add_header = mock.MagicMock()
        req_obj = MockRequest()

        class MockInfo():
            get_content_type = mock.MagicMock(return_value='application/json')
            get = mock.MagicMock()

        class MockResponse():
            read = mock.MagicMock(return_value=b'[]')
            info = mock.MagicMock(return_value=MockInfo())
        res_obj = MockResponse()

        sort = pirate.torrent.parse_sort(MagicMock(Printer), 10)

        with patch('urllib.request.Request', return_value=req_obj) as req:
            with patch('urllib.request.urlopen', return_value=res_obj) as res:
                results = pirate.torrent.remote(
                    MagicMock(Printer), 1, 100, sort, 'top',
                    [], 'http://example.com', 9)
                req.assert_called_once_with(
                    'http://example.com/precompiled/data_top100_100.json',
                    headers=pirate.data.default_headers)
                res.assert_called_once_with(req_obj, timeout=9)
                self.assertEqual(results, [])


if __name__ == '__main__':
    unittest.main()
