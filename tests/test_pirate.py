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
            [['1-3'], (None, [1,2,3])],
        ]
        for test in tests:
            self.assertEqual(pirate.pirate.parse_torrent_command(*test[0]), test[1])

    def test_parse_config_file(self):
        types = {
            'Save': {
                'magnets': bool,
                'Magnets': bool,
                'torrents': bool,
                'directory': str,
            },
            'LocalDB': {
                'enabled': bool,
                'path': str,
            }
        }
        config1 = """
        [Save]
        magnets=False
        directory=dir
        [LocalDB]
        enabled=true
        path=abc
        """
        config2 = """
        [Save]
        Magnets=True
        """
        tests = [
            (config1, {'Save': {'magnets': False}}),
            (config1, {'Save': {'torrents': False}}),
            (config1, {'Save': {'directory': 'dir'}}),
            (config1, {'LocalDB': {'enabled': True}}),
            (config1, {'LocalDB': {'path': 'abc'}}),
            (config2, {'Save': {'magnets': True}}),
        ]
        for test in tests:
            config = pirate.pirate.parse_config_file(test[0])
            for section in test[1].keys():
                for name in test[1][section].keys():
                    if types[section][name] == bool:
                        lhs = config.getboolean(section, name)
                    else:
                        lhs = config.get(section, name)
                    rhs = test[1][section][name]
                    self.assertEqual(lhs, rhs)

    def test_parse_args(self):
        tests = [
            (['-b'], {'mode': 'browse'}),
            ([], {'mode': 'top'}),
            (['-R'], {'mode': 'recent'}),
            (['internets'], {'mode': 'search', 'search': ['internets']}),
            (['internets lol', 'lel'], {'mode': 'search', 'search': ['internets lol', 'lel']}),
        ]
        for test in tests:
            config = pirate.pirate.parse_args(test[0])
            for option in test[1].keys():
                value = getattr(config, option)
                self.assertEqual(test[1][option], value)

if __name__ == '__main__':
    unittest.main()
