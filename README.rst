SimpleAudioIndexer
==================

.. image:: http://rafiei.net/assets/sai/sai_logo.png
         :alt: Simple Audio Indexer: Index audio files and search for a word/phrase or match regex patterns 
         :align: center

|build| |license| |docs| |python| |wheel|


- `Description <#description>`__
- `What can it do? <#what-can-it-do>`__
- `Documentation <#documentation>`__
- `Requirements <#requirements>`__
- `Installation <#installation>`__
- `Uninstallation <#uninstallation>`__
- `Demo <#demo>`__
- `Nice to implement in the future <#nice-to-implement-in-the-future>`__
- `Contributing <#contributing>`__
- `Authors <#authors>`__
- `License <#license>`__


Description
------------

This is a Python library and command-line tool that helps you search for a word
or a phrase within an audio file (wav format). It also builts upon the initial
searching capability and provides some [so-called] advanced searching abilities!


What can it do?
---------------

+ Index audio files (using Watson (Online/Higher-quality) or CMU Pocketsphinx (Offline/Lower-quality)) and save/load the results.
+ Searching within audio files in multiple languages (default is English)
+ Define a timing error for your queries to handle discrepencies.
+ Define constraints on your queries, e.g. whether to include (sub/super)sequences,
  results with missing words etc.
+ Do full blown regex pattern matching!


Documentation
-------------

To read the documentation, visit `here <http://simpleaudioindexer.readthedocs.io/>`__.


Requirements
------------

+ Python (v2.7, 3.3, 3.4, 3.5 or 3.6) with pip installed.
+ Watson API Credentials and/or CMU Pocketsphinx
+ `sox`
+ `ffmpeg` (if you choose CMU Pocketsphinx)
+ `py.text` and `tox` (if you want to run the tests)


Installation
--------------
Open up a terminal and enter:

::

  pip install SimpleAudioIndexer


Installation details can be found at the documentations `here <https://simpleaudioindexer.readthedocs.io/installation/>`__.

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


Demo
----

Say you have this audio file:

|small_audio|


Have it downloaded to an empty directory for simplicity. We'd refer to that
directory as `SRC_DIR` and the name of this audio file as `small_audio.wav`.

Here's how you can search through it.

Command-line Usage
++++++++++++++++++

Open up a terminal and enter.

::

   $ sai --mode "ibm" --username_ibm USERNAME --password_ibm PASSWORD --src_dir SRC_DIR --search "called"

   {'called': {'small_audio.wav': [(1.25, 1.71)]}}

Replace `USERNAME` and `PASSWORD` with your IBM Watson's credentials and `SRC_DIR`
with the absolute path to the directory you just prepared.

The out would be, like above, a dictionary that has the query, the file(s) it
appears in and the all of the (starting second, ending second) of that query.

Note that all commands work uniformally for other engines (i.e. Pocketsphinx),
for example the command above can be enterred as:

::

   $ sai --mode "cmu" --src_dir SRC_DIR --search "lives"

   {'our': {'small_audio': [(2.93, 3.09)]}}

Which would use Pocketsphinx instead of Watson to get the timestamps. Note that
the quality/accuracy of Pocketsphinx is much lower than Watson.

Instead of searching for a word, you could also match a regex pattern, for example:

::

   $ sai --mode ibm --src_dir SRC_DIR --username_ibm USERNAME --password_ibm PASSWORD --regexp " [a-z][a-z] "

   {u' in ': {'small_audio.wav': [(2.81, 2.93)]},
   {u' to ': {'small_audio.wav': [(1.71, 1.81)]}}
   
That was the result of searching for two letter words. Note that your results
would match any aribtrary regular expressions. 

You may also save and load the indexed data from the command line script. For
more information, visit `here <https://simpleaudioindexer.readthedocs.io/usage/#as-a-command-line-script>`__.


Library Usage
+++++++++++++

Say you have this file

.. code-block:: python

  >>> from SimpleAudioIndexer import SimpleAudioIndexer as sai

Afterwards, you should create an instance of `sai`

.. code-block:: python

  >>> indexer = sai(mode="ibm", src_dir="SRC_DIR", username_ibm="USERNAME", password_ibm="PASSWORD")

Now you may index all the available audio files by calling `index_audio` method:

.. code-block:: python

  >>> indexer.index_audio()

You could have a searching generator:

.. code-block:: python

  >>> searcher = indexer.search_gen(query="called")
  # If you're on python 2.7, instead of below, do print searcher.next()
  >>> print(next(searcher))
  {'Query': 'called', 'File Name': 'small_audio.wav', 'Result': (1.25, 1.71)}

Now there are quite a few more arguments implemented for search_gen. Say you
wanted your search to be case sensitive (by default it's not).
Or, say you wanted to look for a phrase but there's a timing gap and the indexer
didn't pick it up right, you could specify `timing_error`. Or, say some word is
completely missed, then you could specify `missing_word_tolerance` etc.

For a full list, see the API reference `here <./reference.html
#SimpleAudioIndexer.SimpleAudioIndexer.search_gen>`__


Note that you could also call `search_all` method to have search for a list of
queries within all the audio files:

Finally, you could do a regex search!

.. code-block:: python

   >>> print(indexer.search_regexp(pattern="[A-Z][^l]* ")
   {u'Americans are ca': {'small_audio.wav': [(0.21, 1.71)]}}

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
feedback, Visit the `CONTRIBUTING <https://github.com/aalireza/SimpleAudioIndexer/blob/master/CONTRIBUTING.rst>`_ file.

Authors
-------

+ **Alireza Rafiei** - `aalireza <https://github.com/aalireza>`_

See also the list of `contributors <https://github.com/aalireza/SimpleAudioIndexer/graphs/contributors>`_
to this project.

License
-------

This project is licensed under the Apache v2.0 license - see the `LICENCE <https://github.com/aalireza/SimpleAudioIndexer/blob/master/LICENSE>`_
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

.. |small_audio| image:: http://rafiei.net/assets/play_button.png
                :target: http://rafiei.net/assets/sai/small_audio.wav
                :alt: Demo audio file

.. _Documentation: https://github.com/aalireza/SimpleAudioIndexer/docs
