SimpleAudioIndexer
==================
Index and search through an audio for words or phrases using Watson Speech API


- `Description <#description>`_
- `Dependencies <#dependencies>`_
- `Installation <#installation>`_
- `Usage <#usage>`_
- `Disclaimer <#disclaimer>`_
- `Nice to implement in the future <#nice-to-implement-in-the-future>`_
- `Thanks <#thanks>`_

Description
------------
Assume you have a bunch of audio files and you're trying to see at what second a particular word a phrase is said. This tries to do it.


Dependencies
------------
+ IBM Watson Speech API access (username and password)
+ sox
+ ffmpeg (or avconv)

This library is not meant to work with Windows.

Installation
------------
::

  pip install SimpleAudioIndexer

Usage
-----

Assuming USERNAME and PASSWORD are the username and password of one's IBM Watson Speech API account and SRC_DIR is the absolute path to the directory in which the audio files are located, usage examples would be provided below.

As a library
~~~~~~~~~~~~

.. code-block:: python

  from SimpleAudioIndexer import SimpleAudioIndexer as sai
  
  indexer = sai(USERNAME, PASSWORD, SRC_DIR)
  indexer.index_audio()
  
  # Saves the result to avoid uploading the same files again if one needs to make another search later
  indexer.save_indexed_audio("{}/indexed_audio.txt".format(SRC_DIR))
  
  # Prints the result of the search for a list of queries. Output would ba dictionary whose keys are 
  # "Some word or phrase" and "another word or phrase". The value of each key is another dictionary 
  # whose keys are audio files and whose values are lists of tuples of starting and ending seconds of 
  # that query.
  print(indexer.search_all(["Some word or phrase", "another word or phrase"]))

There are quite a few more methods and control structures implemented. For more information, look at the source code and see the documentation there. 

As an executable command
~~~~~~~~~~~~~~~~~~~~~~~~
::

  sai -u USERNAME -p PASSWORD -d SRC_DIR -s "SOME WORD OR PHRASE"

It's also possible to add `-v` at the end to see the progress and `-t` to see the all of the indexed words per audio file.

---

**Remark:** The audio files are supposed to be wav and less than 9 channels. We'd break a large audio file into 95% of this limit and upload each sequentially and then search and do a time correction for the founded results. It's possible to change this limit by hand upon initialization of the indexer. (Using the `api_limit_bytes` attribute. For more information, see the source code and read the doc there.)

**Remark:** Other languages are supported. You need to choose a `model` accordingly when calling `index_audio`. Again, see the source for more information.

Disclaimer
----------
- By using this program you'd be uploading your files to IBM which means you're not supposed to necessarily upload everything if you have privacy concerns, and also, It won't be free.
- This project was made to improve the results of `Speech Hacker <https://github.com/ParhamP/Speech-Hacker>`_. Among the available audio indexers (assuming one is only trying to index speech), the IBM's api had the best performance by a very long shot yet nothing around that api existed to make searching easier.


Nice to implement in the future
--------------------------------
- Uploading in parallel
- More control structures for searching (Typos, phoneme based approximation of words using CMU_DICT or NLTK, tolerating missing words etc.)
- Searching for an unintelligible audio within the audio files. Possibly by cross correlation or something similar.

Thanks
------
Many thanks to the following GitHub users for contributing code and/or ideas:

- `ParhamP <https://github.com/ParhamP>`_
