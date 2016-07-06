#!/usr/bin/env python3
import sys
import os.path
import unittest
import importlib
from unittest import mock
from unittest.mock import patch, call, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import setup

class TestPirate(unittest.TestCase):

    @patch('sys.exit')
    def test_unsupported(self, mock_exit):
        sys.version = '3.2.1 (default, dec  7 2015, 12:58:09) \n[gcc 5.2.0]'
        importlib.reload(setup)
        mock_exit.assert_called_once_with(1)

    @patch('sys.exit')
    def test_unsupported2(self, mock_exit):
        sys.version = '2.5.1 (default, dec  7 2015, 12:58:09) \n[gcc 5.2.0]'
        importlib.reload(setup)
        mock_exit.assert_called_once_with(1)


    @patch('sys.exit')
    def test_supported(self, mock_exit):
        sys.version = '3.5.1 (default, dec  7 2015, 12:58:09) \n[gcc 5.2.0]'
        importlib.reload(setup)
        mock_exit.assert_not_called()

    @patch('sys.exit')
    def test_supported_exact(self, mock_exit):
        sys.version = '3.4.0 (default, dec  7 2015, 12:58:09) \n[gcc 5.2.0]'
        importlib.reload(setup)
        mock_exit.assert_not_called()

if __name__ == '__main__':
    unittest.main()
