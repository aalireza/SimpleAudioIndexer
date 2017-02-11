Usage
=====

.. _sai: https://github.com/aalireza/SimpleAudioIndexer

There are basically two ways to use `sai`_:

1. `As a command line script <#as-a-command-line-script>`_.

2. `As a library for developers <#as-a-python-library>`_. (recommended)


As a command line script
------------------------
Note that currently the command-line script is very limited in its
functionality and not all the available methods have been implemented for the
command-line interface.

We assume you have `sai`_ installed and have IBM Watson's credentials ready (if
not, you may read the installation guide `here <./installation.html>`__).


The help command
++++++++++++++++
Open up a terminal. Enter:

::

   sai -h

The result would be a list of all the implemented commands for the command-line
script.

Timestamps
++++++++++
You can either choose to use Watson as your speech to text engine or
Pocketsphinx.

Say your choice is Watson, then enter the command below (replace
`USERNAME` and `PASSWORD` with your Watson credentials) and replace `SRC_DIR`
with the absolute path to the directory in which your audio files are located):

::

   sai --mode "ibm" --username_ibm USERNAME --password_ibm PASSWORD --src_dir SRC_DIR --timestamps

The command above should give you the timestamps of all the words within the
audio.

Note that the switches `--mode` and `--src_dir` are required for anything you
want to do. If your choice of mode is `ibm`, then the switches `username_ibm`
and `password_ibm` would be required as well.

There are some optional switches as well. You've used `--timestamps` to get
timestamps, however you may use `--search` if you want to search for something,
or `--regexp` to search with regular expressions etc.

For the rest of this tutorial we assume that your choice of mode is `ibm`. If
your choice is `cmu`, then you no longer need to ibm switches, but everything
else remains the same.

Search Commands
+++++++++++++++
Say you want to search for the string "apple", then your command would be:

::

  sai --mode ibm --src_dir SRC_DIR --username_ibm USERNAME --password_ibm PASSWORD --search "apple"

You may also search for a regex pattern via the switch `--regexp`:

::

  sai --mode ibm --src_dir SRC_DIR --username_ibm USERNAME --password_ibm PASSWORD --regexp " [a-z][a-z] "

Note that you cannot simultaneously use `-s` and `-r`!

The default language is American English. If you want to use another
language/accent, then use the switch `--language`. For the list of all models,
see the reference `here <./reference.html>`__.

Note that `--language` switch doesn't work for `cmu` mode.

Saving & Loading indexed data
+++++++++++++++++++++++++++++
The last thing worth mentioning, is that, say your audio files are big enough
that you don't want to spend time indexing them every time you run the script,
then you should use the switch `--save-data` followed by an absolute path to a
file into which the indexed data would be written. If such a file doesn't exist,
it'll be created.

For example, say I want to write the indexed data into my Documents directory
with the name `indexed_data`. Then the command would be:

::
   
  sai --mode ibm --src_dir SRC_DIR --username_ibm USERNAME --password_ibm PASSWORD --save-data ABSOLUTE_PATH_TO_A_FILE_TO_BE_CREATED/indexed_data

Next time that I want to search the those audio files, I'll enter:

::

  sai --mode ibm --load_data ABOSLUTE_PATH_INDEXED_DATA --search "stuff"

Note that whenever you're loading your data, you no longer have to enter your
username and password and src_dir, but you still need to specify your mode.


As a Python library
-------------------

We assume you have `sai`_ installed and have IBM Watson's credentials ready (if
not, you may read the installation guide `here <./installation.html>`__).

Basics
++++++
You should put your audio files inside a single directory. Where ever we say
`SRC_DIR`, you should replace it via the absolute path of that directory.
You should also replace `USERNAME` and `PASSWORD` with your Watson credentials.

Note that the format of your audio files must be `wav` (Specific encodings wont
matter). However if your file is not `wav`, it'll be ignored.

Also note that, your audio files must end in `.wav`. While some operating system
allow you to store files without explicit format decleration, it won't always
be reliable to look at the header of the audio files or guess the format.

There's one class that you need to import:

.. code-block:: python

  >>> from SimpleAudioIndexer import SimpleAudioIndexer as sai

Afterwards, you should create an instance of `sai`

.. code-block:: python

  >>> indexer = sai(mode="ibm", src_dir="SRC_DIR", username_ibm="USERNAME", password_ibm="PASSWORD")


Note that if you choose your mode to be `cmu`, then you no longer have to provide
username and passwords of your Watson account.

Indexing
++++++++
Now you may index all the available audio files by calling `index_audio` method:

.. code-block:: python

  >>> indexer.index_audio()


This method automatically created two directories `filtered` and `staging`
within your `src_dir` to handle intermediarry files.

Also, you could also just index a particular audio file. Say you only wish to
index `SRC_DIR/target.wav`, then:

.. code-block:: python

   >>> indexer.index_audio(basename=target.wav)

For more information on all arguments of this method (including other languages
or accuracy etc.) read the API reference `here <./reference.html
#SimpleAudioIndexer.SimpleAudioIndexer.index_audio>`__

Saving & Loading Indexed data
+++++++++++++++++++++++++++++
`index_audio` method, transfers `wav` files into the `filtered` directory.
Then, checks the size of the audio file and splits it if they are sufficiently
large and moves them to `staging` directory and finally reads and sends a
request to Watson.

Say you've done all of that and the next time you don't want to make that
request. Then save your data:

.. code-block:: python

  >>> indexer.save_indexed_audio("{}/indexed_audio".format(indexer.src_dir))
  

Afterwards, all the timestamps of the audios would be saved in
`SRC_DIR/indexed_audio.txt`. Next time, instead of calling `index_audio` method,
do:

.. code-block:: python

  >>> indexer.load_indexed_audio("{}/indexed_audio.txt".format(indexer.src_dir))


Timestamps and time regularizations
+++++++++++++++++++++++++++++++++++
After you've indexed audio, the timestamps for each word would be saved within
a private attribute. They should not be accessed since if the audio files were
large and they were splitted, then the timing won't be correct.

The time corrected/regularized however can be accessed via
`get_timestamps` method. Say there are two audio files in `SRC_DIR`
called `audio.wav` and `another.wav`. Then the timestamps would look something
like below:

.. code-block:: python

  >>> print(indexer.get_timestamps())
  {"audio.wav": [["hello", 0.01, 0.05], ["how", 0.05, 0.08], ["are", 0.08, 0.11],
  ["you", 0.11, 0.14]], "another": [["yo", 0.01, 0.02]]}

Basically, the output is a dictionary whose keys are the audio files and the
outputs are a list of word blocks.
A word block is a list whose first element is a word, second element is the
starting second and the third (and last) element is the ending second of that
word.

Searching methods
+++++++++++++++++
Now, search methods all use the `get_timestamps` internally. Say after
indexing, you finally wanted to do a search.

You could have a searching generator:

.. code-block:: python

  >>> searcher = indexer.search_gen(query="hello")
  # If you're on python 2.7, instead of below, do print searcher.next()
  >>> print(next(searcher))
  {"Query": "hello", "File Name": "audio.wav", "Result": [(0.01, 0.05)]

So in the example above, `SRC_DIR/audio.wav` is at least 0.14 seconds long and
contains 4 words: "hello", "how", "are", "you".

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

The same arguments that were applicable for `search_gen` are applicable for
`search_all`.


Finally, you could do a regex search!

.. code-block:: python

   >>> print(indexer.search_regexp(pattern=" [a-z][a-z][a-z] ")
   {"are": {"audio.wav": [(0.08, 0.11)]}, "how": {"audio.wav": [(0.05, 0.08)]},
   "you": {"audio.wav": [(0.11, 0.14)]}}


Note that anything that can be done via the implemented word-based control
structures over `search_gen` can be done via regex pattern matching (albeit
maybe nontrivial to write the correct pattern).

The open ended nature of `search_regexp` is intended to compliment `search_gen`.


That's it! You know enough to get started. I recemmend taking a look at API
reference `here <./reference.html>`__ to learn more about other methods that
have been implemented.
