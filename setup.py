from setuptools import setup
from os import path
import codecs
import ConfigParser

here = path.abspath(path.dirname(__file__))
meta_parser = ConfigParser.RawConfigParser()
meta_parser.read(path.join(here, 'META.txt'))

with codecs.open(path.join(here, 'README.rst'), "rb", "utf-8") as f:
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
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Communications",
        "Topic :: Multimedia",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
    ],
    keywords=["audio", "indexing", "search", "ibm", "watson", "anagram",
              "subsequence", "supersequence", "sequence", "timestamp"],
    entry_points={
          'console_scripts': [
              'sai = SimpleAudioIndexer.__main__:Main',
          ],
      },
    install_requires=['requests'],
)
