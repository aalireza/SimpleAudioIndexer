Contributing
============

.. _issue: https://github.com/aalireza/SimpleAudioIndexer/issues

First, that's for taking the time to make a contribution! Below you may find
the guildlines.


Bug Repors
----------
If you have a bug to report, open up an `issue`_ and include:

+ Your operating system's name and version.

+ Your `sai` 's installation's version, and if relevant, your `sox` 's version.

+ Detailed steps to reproduce the bug.


Feature Requests & Feedback
---------------------------
The best way would be to open up an `issue`_.


Pull requests
-------------
+ Include passing tests (we use `pytest` and `tox`).

+ You should be including docstrings. We use numpy style docstrings (
  `here <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt>`__).

+ You should update docs accordingly i.e. if your feature is in one of the public
  methods and/or it's something that'll be used directly by the users.

+ Avoid including dependencies or other library calls, unless you have a very
  good reason to do so!
