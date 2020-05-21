#!/usr/bin/env python3
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
import io
import urllib
import json

import pirate.torrent
import pirate.data
from pirate.print import Printer
from tests import util


class TestTorrent(unittest.TestCase):

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
        self.assertEqual(7, sort)
        sort = pirate.torrent.parse_sort(MagicMock(Printer), '7')
        self.assertEqual(7, sort)
        sort = pirate.torrent.parse_sort(MagicMock(Printer), 'asdf')
        self.assertEqual(99, sort)
        sort = pirate.torrent.parse_sort(MagicMock(Printer), '7000')
        self.assertEqual(99, sort)

    def test_request_path(self):
        # the args are (page, category, sort, mode, terms)
        tests = [
            ((0, 100, 10, 'browse', []), '/browse/100/0/10'),
            ((0, 0, 10, 'browse', []), '/browse/100/0/10'),
            ((0, 0, 10, 'recent', []), '/top/48hall'),
            ((0, 100, 10, 'recent', []), '/top/48h100'),
            ((0, 100, 10, 'top', []), '/top/100'),
            ((0, 0, 10, 'top', []), '/top/all'),
            ((0, 100, 10, 'search', ['abc']), '/search/abc/0/10/100'),
            ((0, 100, 10, 'search', ['abc', 'def']), '/search/abc+def/0/10/100'),
            ((0, 100, 10, 'search', [u'\u1234']), '/search/%E1%88%B4/0/10/100'),
            ((0, 100, 10, 'asdf', []), Exception),
        ]
        for test in tests:
            if test[1] != Exception:
                path = pirate.torrent.build_request_path(*test[0])
                self.assertEqual(test[1], path)
            else:
                with self.assertRaises(test[1]):
                    pirate.torrent.build_request_path(test[0])

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

        with patch('urllib.request.Request', return_value=req_obj) as req:
            with patch('urllib.request.urlopen', return_value=res_obj) as res:
                results = pirate.torrent.remote(
                    MagicMock(Printer), 100, 10, 'browse',
                    [], 'http://example.com', 9)
                req.assert_called_once_with(
                    'http://example.com/precompiled/data_top100_100.json',
                    headers=pirate.data.default_headers)
                res.assert_called_once_with(req_obj, timeout=9)
                self.assertEqual(results, [])


if __name__ == '__main__':
    unittest.main()
