#!/usr/bin/env python3
import unittest
import pirate.pirate


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
            [['1-3 d'], ('d', [1,2,3])],
        ]
        for test in tests:
            self.assertEqual(pirate.pirate.parse_torrent_command(*test[0]), test[1])

if __name__ == '__main__':
    unittest.main()
