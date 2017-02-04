Contributing
============

.. _issue: https://github.com/aalireza/SimpleAudioIndexer/issues

First, Tahnk you very much for taking the time to make a contribution! Below you may find
the guidelines.


Bug Reports
----------
If you have a bug to report, open up an `issue`_ and include:

+ Your operating system's name and version.

+ Your `sai` 's installation's version, and if relevant, your `sox` 's version.

+ Detailed steps to reproduce the bug.


Feature Requests & Feedback
---------------------------
The best way would be to open up an `issue`_. Being as specific as possible would be great!


Development setup
-----------------
For local development:

1. Fork `SimpleAudioIndexer <https://github.com/aalireza/SimpleAudioIndexer>`_.
2. Clone your fork locally (replace `USERNAME` with your own)::

    git clone git@github.com:USERNAME/SimpleAudioIndexer.git

3. Create a branch for local development::

    git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

4. When you're done making changes run the tests locally with `tox <http://tox.readthedocs.org/en/latest/install.html>`_::

    tox
    
   `py.test <http://doc.pytest.org/en/latest/>`_ would be the testing framework that'll be running underneath. So you should
   be installing it as well. Note that `tox` runs the tests for Python 2 and 3. If you don't have them, you may run your
   tests with the just::
   
    pytest
    
   And let `Travis <https://travis-ci.org/aalireza/SimpleAudioIndexer>`_ automattically handle testing for other versions,
   but it'll be much slower! :)

5. Commit your changes and push your branch to GitHub::

    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature

6. Submit a pull request through the GitHub website.


Pull requests
-------------
If your request is for merging (either a new functionality and/or fixing and `issue`_), then:

+ Include passing tests (we use `pytest` and `tox`).

+ You should be including docstrings. We use numpy style docstrings (`here <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt>`__).

+ You should update docs accordingly i.e. if your feature is in one of the public
  methods and/or it's something that'll be used directly by the users.

+ Avoid including dependencies or other library calls, unless you have a very
  good reason to do so!
