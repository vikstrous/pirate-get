#!/usr/bin/env python3
from setuptools import setup, find_packages
from distutils.version import LooseVersion
import sys
import pirate.data

if LooseVersion(sys.version) < LooseVersion("3.4.0"):
    print("pirate-get requires at least python 3.4.0."
          " Your version is %s." % sys.version.split()[0])
    sys.exit(1)

if __name__ == '__main__':
    setup(name='pirate-get',
        version=pirate.data.version,
        description='A command line interface for The Pirate Bay',
        url='https://github.com/vikstrous/pirate-get',
        author='vikstrous',
        author_email='me@viktorstanchev.com',
        license='AGPL',
        packages=find_packages(),
        package_data={'': ["data/*.json"]},
        entry_points={
            'console_scripts': ['pirate-get = pirate.pirate:main']
        },
        install_requires=['colorama>=0.3.3',
                          'beautifulsoup4>=4.4.1',
                          'veryprettytable>=0.8.1'],
        keywords=['torrent', 'magnet', 'download', 'tpb', 'client'],
        classifiers=[
            'Topic :: Utilities',
            'Topic :: Terminals',
            'Topic :: System :: Networking',
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: 3.4',
            'License :: OSI Approved :: GNU General Public License (GPL)',
        ],
        test_suite='tests')
