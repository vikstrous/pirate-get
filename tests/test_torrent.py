#!/usr/bin/env python3
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
import os
import io
import urllib

import pirate.torrent
import pirate.data
from pirate.print import Printer
from tests import util

class TestTorrent(unittest.TestCase):

    def test_no_hits(self):
        res = util.read_data('no_hits.html')
        actual = pirate.torrent.parse_page(res)
        expected = []
        self.assertEqual(actual, expected)

    def test_blocked_mirror(self):
        res = util.read_data('blocked.html')
        with self.assertRaises(IOError):
            pirate.torrent.parse_page(res)

    def test_search_results(self):
        res = util.read_data('dan_bull_search.html')
        actual = pirate.torrent.parse_page(res)
        expected = [
            {'uploaded': '04-04\xa02014', 'seeds': '16', 'leechers': '1', 'id': '9890864', 'magnet': 'magnet:?xt=urn:btih:30df4f8b42b8fd77f5e5aa34abbffe97f5e81fbf&dn=Dan+Croll+%26bull%3B+Sweet+Disarray+%5B2014%5D+320&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['89.33', 'MiB']},
            {'uploaded': '03-02\xa02014', 'seeds': '4', 'leechers': '0', 'id': '9684858', 'magnet': 'magnet:?xt=urn:btih:7abd3eda600996b8e6fc9a61b83288e0c6ac0d83&dn=Dan+Bull+-+Massive+Collection&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['294', 'MiB']},
            {'uploaded': '01-19\xa02013', 'seeds': '2', 'leechers': '0', 'id': '8037968', 'magnet': 'magnet:?xt=urn:btih:8f8d68fd0a51237c89692c428ed8a8f64a969c70&dn=Dan+Bull+-+Generation+Gaming+-+2013&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['54.86', 'MiB']},
            {'uploaded': '01-21\xa02010', 'seeds': '1', 'leechers': '0', 'id': '5295449', 'magnet': 'magnet:?xt=urn:btih:3da6a0fdc1d67a768cb32597e926abdf3e1a2fdd&dn=Dan+Bull+Collection&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['236.78', 'MiB']},
            {'uploaded': '09-02\xa02014', 'seeds': '1', 'leechers': '0', 'id': '10954408', 'magnet': 'magnet:?xt=urn:btih:5cd371a235317319db7da52c64422f9c2ac75d77&dn=Dan+Bull+-+The+Garden+%7B2014-Album%7D&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['36.27', 'MiB']},
            {'uploaded': '09-27\xa02009', 'seeds': '0', 'leechers': '1', 'id': '5101630', 'magnet': 'magnet:?xt=urn:btih:4e14dbd077c920875be4c15971b23b609ad6716a&dn=Dan+Bull+-+Dear+Lily+%5Ban+open+letter+to+Lily+Allen%5D+-+2009%5BMP3+%40&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['5.51', 'MiB']},
            {'uploaded': '11-29\xa02009', 'seeds': '0', 'leechers': '0', 'id': '5185893', 'magnet': 'magnet:?xt=urn:btih:5d9319cf852f7462422cb1bffc37b65174645047&dn=Dan+Bull+-+Dear+Mandy+%5Ban+open+letter+to+Lord+Mandelson%5D&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['5.07', 'MiB']},
            {'uploaded': '11-10\xa02011', 'seeds': '0', 'leechers': '0', 'id': '6806996', 'magnet': 'magnet:?xt=urn:btih:1c54af57426f53fdef4bbf1a9dbddf32f7b4988a&dn=Dan+Bull+-+Dear+Lily+%28Lily+Allen%29+%28Song+about+filesharing%29&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['5.34', 'MiB']},
            {'uploaded': '12-20\xa02011', 'seeds': '0', 'leechers': '0', 'id': '6901871', 'magnet': 'magnet:?xt=urn:btih:942c5bf3e1e9bc263939e13cea6ad7bd5f62aa36&dn=Dan+Bull+-+SOPA+Cabana.mp3&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['4.8', 'MiB']},
            {'uploaded': '12-21\xa02011', 'seeds': '0', 'leechers': '1', 'id': '6902247', 'magnet': 'magnet:?xt=urn:btih:d376f68a31b0db652234e790ed7256ac5e32db57&dn=Dan+Bull+-+SOPA+Cabana&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['3.4', 'MiB']},
            {'uploaded': '12-21\xa02011', 'seeds': '0', 'leechers': '1', 'id': '6903548', 'magnet': 'magnet:?xt=urn:btih:28163770a532eb24b9e0865878288a9bbdb7a5e6&dn=Dan+Bull+-+SOPA+Cabana+%5BWORKING%5D&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['4.8', 'MiB']},
            {'uploaded': '03-09\xa02012', 'seeds': '0', 'leechers': '1', 'id': '7088979', 'magnet': 'magnet:?xt=urn:btih:779ab0f13a3fbb12ba68b27721491e4d143f26eb&dn=Dan+Bull+-+Bye+Bye+BPI+2012++%5BMP3%40192%5D%28oan%29&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['60.72', 'MiB']},
            {'uploaded': '10-24\xa02012', 'seeds': '0', 'leechers': '0', 'id': '7756344', 'magnet': 'magnet:?xt=urn:btih:2667e4795bd5c868dedcabcb52943f4bb7212bab&dn=Dan+Bull+-+Dishonored+%5BExplicit+ver.%5D+%28Single+2012%29&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['6.29', 'MiB']},
            {'uploaded': '11-10\xa02012', 'seeds': '0', 'leechers': '0', 'id': '7812951', 'magnet': 'magnet:?xt=urn:btih:16364f83c556ad0fd3bb57a4a7c890e7e8087414&dn=Halo+4+EPIC+Rap+By+Dan+Bull&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['6.41', 'MiB']},
            {'uploaded': '01-19\xa02013', 'seeds': '0', 'leechers': '1', 'id': '8037899', 'magnet': 'magnet:?xt=urn:btih:843b466d9fd1f0bee3a476573b272dc2d6d0ebae&dn=Dan+Bull+-+Generation+Gaming+-+2013&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969', 'size': ['54.87', 'MiB']}
        ]
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
        with patch('pirate.torrent.open', mock.mock_open(), create=True) as open_:
            magnet = 'magnet:?xt=urn:btih:335fcd3cfbecc85554616d73de888033c6c16d37&dn=Test+Drive+Unl\im/ited+%5BPC+Version%5D&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969'
            pirate.torrent.save_torrents(MagicMock(Printer), [0], [{'magnet':magnet}], 'path')
            get_torrent.assert_called_once_with(293294978876299923284263767676068334936407502135)
            open_.assert_called_once_with('path/Test Drive Unl_im_ited [PC Version].torrent', 'wb')

    @patch('pirate.torrent.get_torrent', side_effect=urllib.error.HTTPError('', '', '', '', io.StringIO()))
    def test_save_torrents_fail(self, get_torrent):
        magnet = 'magnet:?xt=urn:btih:335fcd3cfbecc85554616d73de888033c6c16d37&dn=Test+Drive+Unlimited+%5BPC+Version%5D&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969'
        pirate.torrent.save_torrents(MagicMock(Printer), [0], [{'magnet':magnet}], 'path')

    def test_save_magnets(self):
        with patch('pirate.torrent.open', mock.mock_open(), create=True) as open_:
            magnet = 'magnet:?xt=urn:btih:335fcd3cfbecc85554616d73de888033c6c16d37&dn=Test+Drive+Unl\im/ited+%5BPC+Version%5D&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969'
            pirate.torrent.save_magnets(MagicMock(Printer), [0], [{'magnet':magnet}], 'path')
            open_.assert_called_once_with('path/Test Drive Unl_im_ited [PC Version].magnet', 'w')

    @patch('urllib.request.urlopen')
    def test_get_torrent(self, urlopen):
        class MockRequest():
            add_header = mock.MagicMock()
        request_obj = MockRequest()
        with patch('urllib.request.Request', return_value=request_obj) as request:
            pirate.torrent.get_torrent(100000000000000)
            request.assert_called_once_with('http://itorrents.org/torrent/5AF3107A4000.torrent', headers=pirate.data.default_headers)
            urlopen.assert_called_once_with(request_obj, timeout=pirate.data.default_timeout)

    def test_remote(self):
        class MockRequest():
            add_header = mock.MagicMock()
        request_obj = MockRequest()
        class MockResponse():
            read = mock.MagicMock(return_value='<html>No hits. Try adding an asterisk in you search phrase.</html>'.encode('utf8'))
            info = mock.MagicMock()
        response_obj = MockResponse()
        with patch('urllib.request.Request', return_value=request_obj) as request:
            with patch('urllib.request.urlopen', return_value=response_obj) as urlopen:
                res = pirate.torrent.remote(MagicMock(Printer), 1, 100, 10, 'browse', [], 'http://example.com')
                request.assert_called_once_with('http://example.com/browse/100/0/10', headers=pirate.data.default_headers)
                urlopen.assert_called_once_with(request_obj, timeout=pirate.data.default_timeout)
                self.assertEqual(res, [])

if __name__ == '__main__':
    unittest.main()
