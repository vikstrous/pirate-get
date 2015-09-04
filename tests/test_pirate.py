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

if __name__ == '__main__':
    unittest.main()
