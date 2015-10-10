#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(name='pirate-get',
    version='0.2.8',
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
    install_requires=['colorama>=0.3.3', 'pyquery>=1.2.9', 'veryprettytable>=0.8.1'],
    keywords=['torrent', 'magnet', 'download', 'tpb', 'client'],
    classifiers=[
        'Topic :: Utilities',
        'Topic :: Terminals',
        'Topic :: System :: Networking',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: GNU General Public License (GPL)',
    ],
    test_suite='tests',
)
