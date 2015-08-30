#!/usr/bin/env python3
import unittest
import pirate.local
import os

class TestLocal(unittest.TestCase):

    def test_rich_xml(self):
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rich.xml')
        expected = [['magnet:?xt=urn:btih:b03c8641415d3a0fc7077f5bf567634442989a74&dn=High.Chaparall.S02E02.PDTV.XViD.SWEDiSH-HuBBaTiX', '?', '?']]
        actual = pirate.local.search(path, ('High',))
        self.assertEqual(actual, expected)

if __name__ == '__main__':
    unittest.main()
