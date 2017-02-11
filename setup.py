from setuptools import setup
from os import path
import sys
import codecs

if sys.version_info < (3, 0):
    import ConfigParser as configparser
else:
    import configparser

here = path.abspath(path.dirname(__file__))
meta_parser = configparser.RawConfigParser()
meta_parser.read(path.join(here, 'META.txt'))

with codecs.open(path.join(here, 'README.rst'), 'r') as f:
    long_description = f.read()


setup(
    name=meta_parser.get("Program", "Name"),
    version=meta_parser.get("Program", "Version"),
    description=meta_parser.get("Program", "Description"),
    long_description=long_description,
    license=meta_parser.get("Program", "License"),
    author=meta_parser.get("Author", "Name"),
    author_email=meta_parser.get("Author", "Email"),
    packages=["SimpleAudioIndexer"],
    url=meta_parser.get("Program", "URL"),
    download_url=(
        "{}/tarball/{}".format(
            meta_parser.get("Program", "URL"),
            meta_parser.get("Program", "TAG"),
        )
    ),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords=["audio", "indexing", "search", "ibm", "watson", "anagram",
              "subsequence", "supersequence", "sequence", "timestamp", "cmu",
              "sphinx", "cpmsphinx", "speech", "speech recognition"],
    entry_points={
          'console_scripts': [
              'sai = SimpleAudioIndexer.__main__:Main',
          ],
      },
    install_requires=['requests'],
)
