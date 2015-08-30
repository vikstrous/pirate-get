from setuptools import setup

setup(name='pirate-get',
    version='0.2.4',
    description='A command line interface for The Pirate Bay',
    url='https://github.com/vikstrous/pirate-get',
    author='vikstrous',
    author_email='',
    license='GPL',
    packages=['pirate'],
    entry_points={
        'console_scripts': ['pirate-get = pirate.pirate:main']
    },
    install_requires=['colorama'],
    keywords=['torrent', 'magnet', 'download', 'tpb', 'client'],
    classifiers=[
        'Topic :: Utilities'
        'Topic :: Terminals'
        'Topic :: System :: Networking'
        'Programming Language :: Python :: 3 :: Only'
        'License :: OSI Approved :: GNU General Public License (GPL)',
    ])