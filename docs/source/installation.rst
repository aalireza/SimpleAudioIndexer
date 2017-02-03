Installation
============

.. _sai: https://github.com/aalireza/SimpleAudioIndexer
.. _Ubuntu: https://ubuntu.com
.. _docker: https://docker.org
.. _sox: http://sox.sourceforge.net/
.. _homebrew: http://brew.sh
.. _pytest: http://doc.pytest.org/en/latest/index.html
.. _tox: https://tox.readthedocs.io/en/latest/
.. _pip: https://pypi.python.org/pypi/pip
.. _dockerfile.txt: https://raw.githubusercontent.com/aalireza/SimpleAudioIndexer/master/Dockerfile.txt

There are two main ways to install `sai`_:

1. If you're on a Unix(-like) system, say Linux or OS X, then you can do a
   full/native installation.

2. If you're on a Windows system, or for some reason don't want to install
   natively, you may use the software within a Docker image.

Native Installation
-------------------

You're going to need to get IBM Watson credentials, install `sox`_ and finally
install `sai`_.

First step: IBM Credentials
+++++++++++++++++++++++++++
You need a valid username and password for IBM Watson's Speech to Text API. You
may sign up `here <https://www.ibm.com/watson/developercloud/
speech-to-text.html>`__. After you've created your accout, make an app that uses
Speech to text service. Go the settings and save your credentials.

The process has been explained in detail in `here <https://www.ibm.com/watson/
developercloud/doc/getting_started/gs-credentials.shtml>`__


Second Step: Installing sox
+++++++++++++++++++++++++++
You need to install `sox`_ on your system. We'll use `sox`_ to process the audio.

If you're on a *Linux* system, it should probably be in your distro's repository.
If you're using `Ubuntu`_ (or similar), you may install by entering the command
below in a terminal:

::

  sudo apt-get install sox

If you're on *OS X*, then choose the most recent version from the `sox`_ 's
official repo and install it on your system. The link is `here <https://
sourceforge.net/projects/sox/files/sox/>`_.

If you're using `homebrew`_, however, you could just enter the command below in
a terminal:

::

  brew install sox


Third Step: Installing SAI
++++++++++++++++++++++++++
You should be installing this library via Python's `pip`_. Enter the command
below in a terminal:

::

  pip install SimpleAudioIndexer


Note that if you wish to run the unit tests, you need to install `pytest`_ (and
preferably `tox`_ as well). 


That's it! If everything was okay, you should be having it on your system.
To verify, enter in your terminal:

::

   sai -h


You may also enter in a Python shell:

.. code-block:: python

  >>> from SimpleAudioIndexer import SimpleAudioIndexer as sai

If you didn't see any error messages, then `sai`_ is successfully installed!

That's it! you've installed `sai`_ successfully! 


Docker route
------------
If you're on a Windows system, or for some reason don't want to install natively
you may run `sai`_ within a `docker`_ container.

We don't recommend that you choose the `docker`_ route if you have a choice to
do a native install. `Docker`_ containers are intended to run a single process
and will stop as soon as their job is complete.

Our image, however, will run a process that never ends which in turn would
enable you to get a terminal in that container.

We assume that you have `docker`_ installed and functional on your system.

Download the `Dockerfile.txt`_ from the `sai`_ repo.

Open up a terminal and `cd` into the directory that contains the docker file.
Then, enter the command below:

::

   docker build -t sai-docker .

Note that by running building our docker image, you'd be downloading a lot of
intermediary stuff including `Ubuntu`_ and a new build of Python. That means,
you should have at least 500MB available.

Assuming the build was successfull, then enter the command below to run it:

::

   docker run sai-docker

Now open up a new terminal and enter the command below:

::

   docker ps -a

Now copy the Container-ID of `sai-docker`. Then, in that new terminal enter:

::

   docker exec -i -t CONTAINER-ID /bin/bash


Right now you should be having shell access within `sai-docker` container and
should be able to run `sai` in the command line or import it in a python repl.

To stop the docker process, exit the shell you've got in the container and open
up a new terminal in your system and enter:

::

   docker rm -rf CONTAINER-ID


Uninstall
---------
If for any reason you wish to install `sai`_, fear not! It's quite simple.

Uninstall natively
++++++++++++++++++
If you've installed `sai`_ natively on your system, then you may just open up
a command line and enter:

::

   pip uninstall SimpleAudioIndexer

Depending on your operating system, uninstallation method of `sox`_ would be
different. If you're on Ubuntu, you may just enter:

::

   sudo apt-get remove sox && sudo apt-get autoremove

If you were on OS X and used `homebrew`_, you may open up a terminal and enter:

::

   brew uninstall sox

If however you've installed sox via their repo, then it'd be just a simple drag
and drop wherever you've installed it!

That's it! You've uninstalled `sai`_ successfully!


Uninstall the Docker version
++++++++++++++++++++++++++++
If you've installed `sai`_ from the `dockerfile.txt`_ found at the repo, then
you may just open up a terminal and enter:

::

   docker rmi sai-docker

Note an Ubuntu image would be installed alongside sai-docker as well. You may
remove that similarly.
