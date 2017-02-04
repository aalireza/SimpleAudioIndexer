SimpleAudioIndexer
==================

.. image:: https://github.com/aalireza/SimpleAudioIndexer/blob/master/docs/source/images/sai_logo.png
         :alt: Simple Audio Indexer: Index audio files and search for a word/phrase or match regex patterns 
         :align: center

|build| |license| |docs| |python| |wheel|


- `Description <#description>`_
- `What can it do? <#what-can-it-do>`_
- `Documentation <#documentation>`_
- `Installation <#installation>`_
- `Uninstallation <#uninstallation>`_
- `Command-line Usage <#command-line-usage>`_
- `Nice to implement in the future <#nice-to-implement-in-the-future>`_
- `Contributing <#contributing>`_
- `Authors <#authors>`_
- `License <#license>`_

Description
------------
This is a Python library and command-line tool that helps you search for a word
or a phrase within an audio file (wav format). It also builts upon the initial
searching capability and provides some [so-called] advanced searching abilities!

What can it do?
---------------
+ Index audio files and save/load the results.
+ Searching within audio files in multiple languages (default is English)
+ Define a timing error for your queries to handle discrepencies.
+ Define constraints on your queries, e.g. whether to include (sub/super)sequences,
  results with missing words etc.
+ Do full blown regex pattern matching!


Documentation
-------------
To read the documentation, visit `here <http://simpleaudioindexer.readthedocs.io/>`__.

Installation
------------
Open up a terminal and enter:
::

  pip install SimpleAudioIndexer


You should also be installing `sox` and get IBM Watson API credentials. To do
so, visit `here <https://simpleaudioindexer.readthedocs.io/installation/>`__.

There's a `dockerfile <https://raw.githubusercontent.com/aalireza/SimpleAudioIndexer/master/Dockerfile>`_
included withing the repo if you're unable to do a native installation or are
on a Windows system.


Uninstallation
--------------
Open up a terminal and enter:

::

   pip uninstall SimpleAudioIndexer

Uninstalling `sox`, however, is dependent upon whether you're on a Linux or Mac
system. For more information, visit `here <https://simpleaudioindexer.readthedocs.io/installation/#uninstall>`__.


Command-line Usage
------------------

Prepare a directory that contains your audio files (`wav` format). Then
open up a terminal and enter:
::

   sai -u USERNAME -p PASSWORD -d SRC_DIR -s "apple"

Replace `USERNAME` and `PASSWORD` with your IBM Watson's credentials and `SRC_DIR`
with the absolute path to the directory you just prepared.

What comes after `-s` switch, is your query. With the command above, you just
searched for "apple" inside those audio files!

You could also match a regex pattern like below:
::

   sai -u USERNAME -p PASSWORD -d SRC_DIR -s " T[a-z][a-z] "

Which would search for three letters words starting with T.

You may also save and load the indexed data from the command line script. For
more information, visit `here <https://simpleaudioindexer.readthedocs.io/usage/#as-a-command-line-script>`__.


Library Usage
--------------
.. code-block:: python

  >>> from SimpleAudioIndexer import SimpleAudioIndexer as sai

Afterwards, you should create an instance of `sai`

.. code-block:: python

  >>> indexer = sai(USERNAME, PASSWORD, SRC_DIR)

Now you may index all the available audio files by calling `index_audio` method:

.. code-block:: python

  >>> indexer.index_audio()

You could have a searching generator:

.. code-block:: python

  >>> searcher = indexer.search_gen(query="hello")
  # If you're on python 2.7, instead of below, do print searcher.next()
  >>> print(next(searcher))
  {"Query": "hello", "File Name": "audio.wav", "Result": [(0.01, 0.05)]

Now there are quite a few more arguments implemented for search_gen. Say you
wanted your search to be case sensitive (by default it's not).
Or, say you wanted to look for a phrase but there's a timing gap and the indexer
didn't pick it up right, you could specify `timing_error`. Or, say some word is
completely missed, then you could specify `missing_word_tolerance` etc.

For a full list, see the API reference `here <./reference.html
#SimpleAudioIndexer.SimpleAudioIndexer.search_gen>`__


You could also call `search_all` method to have search for a list of queries
within all the audio files:

.. code-block:: python

  >>> print(indexer.search_all(queries=["hello", "yo"]))
  {"hello": {"audio.wav": [(0.01, 0.05)]}, {"yo": {"another.wav": [(0.01, 0.02)]}}}

Finally, you could do a regex search!

.. code-block:: python

   >>> print(indexer.search_regexp(pattern=" [a-z][a-z][a-z] ")
   {"are": {"audio.wav": [(0.08, 0.11)]}, "how": {"audio.wav": [(0.05, 0.08)]},
   "you": {"audio.wav": [(0.11, 0.14)]}}


There are more functionalities implemented. For detailed explainations, read the
documentation `here <https://simpleaudioindexer.readthedocs.io/usage/#as-a-python-library>`__.

Nice to implement in the future
--------------------------------
- Uploading in parallel
- More control structures for searching (Typos, phoneme based approximation of
  words using CMU_DICT or NLTK etc.)
- Searching for an unintelligible audio within the audio files. Possibly by
  cross correlation or something similar.


Contributing
-------------
Should you want to contribute code or ideas, file a bug request or give
feedback, Visit the `CONTRIBUTING <CONTRIBUTING>`_ file.

Authors
-------
+ **Alireza Rafiei** - `aalireza <https://github.com/aalireza>`_

See also the list of `contributors <https://github.com/aalireza/SimpleAudioIndexer/graphs/contributors>`_
to this project.

License
-------
This project is licensed under the Apache v2.0 license - see the `LICENCE <LICENSE>`_
file for more details.


.. |license| image:: https://img.shields.io/pypi/l/SimpleAudioIndexer.svg
            :target: LICENSE
            :alt: Apache v2.0 License
   
.. |docs| image:: https://readthedocs.org/projects/simpleaudioindexer/badge/?version=latest
         :target: http://simpleaudioindexer.readthedocs.io/?badge=latest
         :alt: Documentation Status

.. |build| image:: https://travis-ci.org/aalireza/SimpleAudioIndexer.svg?branch=master
          :target: https://travis-ci.org/aalireza/SimpleAudioIndexer
          :alt: Build status

.. |python| image:: https://img.shields.io/pypi/pyversions/SimpleAudioIndexer.svg
           :alt: Python 2,7, 3,3, 3.4, 3.5, 3.6 supported

.. |wheel| image:: https://img.shields.io/pypi/wheel/SimpleAudioIndexer.svg 
          :alt: Wheel ready

.. _Documentation: https://github.com/aalireza/SimpleAudioIndexer/docs
