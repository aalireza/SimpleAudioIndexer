#!/usr/bin/env python

"""
  Copyright 2016-2017 Alireza Rafiei

  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at:

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
"""


from __future__ import absolute_import, division, print_function
from collections import Counter, defaultdict
from distutils.spawn import find_executable
from functools import reduce, wraps
from math import floor
from shutil import rmtree
from string import ascii_letters
from time import time
import json
import os
import re
import requests
import subprocess
import sys

if sys.version_info >= (3, 0):
    from contextlib import ContextDecorator
    import pickle
    unicode = str
    long = int
else:
    import cPickle as pickle

    class ContextDecorator(object):
        """
        A base class or mixin that enables context managers to work as
        decorators.

        Code is from Python's source:
        https://hg.python.org/cpython/file/3.6/Lib/contextlib.py
        """
        def _recreate_cm(self):
            return self

        def __call__(self, func):
            @wraps(func)
            def inner(*args, **kwds):
                with self._recreate_cm():
                    return func(*args, **kwds)
            return inner


class _PrettyDefaultDict(defaultdict):
    # When printing the output of search_results, normally the defaultdict
    # type would be shown as well. To print the `search_results` normally,
    # defining a PrettyDefaultDict type that is printable the same way as a
    # dict, is easier/faster than json.load(json.dump(x)) etc. and we don't
    # actually have to deal with encoding either.
    __repr__ = dict.__repr__


class _WordBlock(object):
    """
    Holds a word with its starting second and ending second (with respect to
    an audio file)

    Attributes
    ----------
    word : str
    start : float
    end : float
    """

    def __init__(self, word, start, end):
        self.word = word
        self.start = round(start, 2)
        self.end = round(end, 2)

    def __eq__(self, other):
        if type(other) is not _WordBlock:
            raise TypeError
        return (self.word == other.word and
                self.start == other.start and
                self.end == other.end)

    def __getitem__(self, i):
        if type(i) is not int:
            raise TypeError
        if i == 0:
            return self.word
        elif i == 1:
            return self.start
        elif i == 2:
            return self.end
        raise IndexError

    def __repr__(self):
        return "(\"{}\", {}, {})".format(self.word, self.start, self.end)


class _Subdirectory_Managing_Decorator(ContextDecorator):

        def __init__(self, src_dir, needed_directories):
            self.src_dir = src_dir
            self.needed_directories = needed_directories

        def __enter__(self):
            """
            Creates the needed directories for audio processing.
            """
            if self.src_dir is not None:
                for directory in self.needed_directories:
                    if not os.path.exists("{}/{}".format(
                            self.src_dir, directory)):
                        os.mkdir("{}/{}".format(self.src_dir, directory))
            return self

        def __exit__(self, *args):
            """
            Removes the works of __enter__.
            """
            if self.src_dir is not None:
                for directory in self.needed_directories:
                    if os.path.exists("{}/{}".format(self.src_dir, directory)):
                        rmtree("{}/{}".format(self.src_dir, directory))


class SimpleAudioIndexer(object):
    """
    Indexes audio and searches for a string within it or matches a regex
    pattern.

    Audio files that are intended to be indexed should be in wav format, placed
    in a same directory and the absolute path to that directory should be
    passed as `src_dir` upon initialization.

    Call the method `index_audio` (which results in calling `index_audio_ibm`
    or `index_audio_cmu` based on the given mode) prior to searching
    or accessing timestamps, unless you have saved the data for your
    previously indexed audio (in that case, `load_indexed_audio` method must
    be used)

    You may see timestamps of the words that have been indexed so far sorted
    by audio files and the time of their occurance, by calling the method
    `get_audio_timestamps`.

    You may saved the indexed audio data (which is basically just the time-
    regularized timestamps) via `save_indexed_audio` method and load it back
    via `load_indexed_audio`

    Do exhustive search with the method `search_all`, do iterative search with
    the method `search_gen` or do regex based search with the method
    `search_regexp`

    For more information see the docs and read usage guide.

    Attributes
    ----------
    mode : {"ibm", "cmu"}
        specifying whether speech to text engine is IBM's Watson or
        Pocketsphinx.
    src_dir :  str
        Absolute path to the source directory of audio files such that the
        absolute path of the audio that'll be indexed would be
        `src_dir/audio_file.wav`
    verbose :  bool, optional
        `True` if progress needs to be printed. Default is `False`.
    ibm_api_limit_bytes :  int, optional
        It holds the API limitation of Watson speech api http sessionless
        which is 100Mbs. Default is 100000000.

    Methods
    -------
    get_mode()
    get_username_ibm()
    set_username_ibm()
    get_password_ibm()
    set_password_ibm()
    get_verbosity()
    set_verbosity()
    get_timestamps()
        Returns a corrected dictionary whose key is the original file name and
        whose value is a list of words and their beginning and ending time. It
        accounts for large files and does the timing calculations to return the
        correct result.
    get_errors()
        Returns a dictionary that has all the erros that have occured while
        processing the audio file. Dictionary contains time of error, file that
        had the error and the actual error.
    _index_audio_ibm(name=None, continuous=True, model="en-US_BroadbandModel",
                     word_confidence=True, word_alternatives_threshold=0.9,
                     profanity_filter_for_US_results=False)
        Implements a searching-suitable interface for the Watson API
    _index_audio_cmu(name=None)
        Implements an experimental interface for the CMu Pocketsphinx
    index_audio(*args, **kwargs)
        Returns a corrected dictionary whose key is the original file name and
        whose value is a list of words and their beginning and ending time. It
        accounts for large files and does the timing calculations to return the
        correct result.
    save_indexed_audio(indexed_audio_file_abs_path)
    load_indexed_audio(indexed_audio_file_abs_path)
    search_gen(query, audio_basename=None, case_sensitive=False,
               subsequence=False, supersequence=False, timing_error=0.0,
               anagram=False, missing_word_tolerance=0)
        A generator which returns a valid search result at each iteraiton.
    search_all(queries, audio_basename=None, case_sensitive=False,
               subsequence=False, supersequence=False, timing_error=0.0,
               anagram=False, missing_word_tolerance=0)
        Returns a dictionary of all results of all of the queries for either
        all of the audio files or the `audio_basename`.
    search_regexp(pattern, audio_basename=None)
        Returns a dictionary of all results which matched `pattern` for either
        all of the audio files or the `auio_basename`
    """

    def __init__(self, src_dir, mode, username_ibm=None, password_ibm=None,
                 ibm_api_limit_bytes=100000000, verbose=False,
                 needed_directories={"filtered", "staging"}):
        """
        Parameters
        ----------
        src_dir : str
            Absolute path to the source directory of audio files such that the
            absolute path of the audio that'll be indexed would be
            `src_dir/audio_file.wav`
        mode : {"ibm", "cmu"}
            specifying whether speech to text engine is IBM's Watson or
            Pocketsphinx. Pros for IBM is its accuracy, Cons is that it's not
            free and you have to upload your audio files.
            Pros for Pocketsphinx is that it's opensource and free, Cons is
            that its accuracy is pre-alpha (currently it's Febuary 2017).
        username_ibm : str, None
            Default is `None`, since if mode is "cmu", no username is needed.
        password_ibm : str
            Default is `None`, since if mode is "cmu", no password is needed.
        ibm_api_limit_bytes : int, optional
            default is 100000000
        verbose : bool, optional
            default is False
        """
        assert mode.lower() in {"ibm", "cmu"}, (
            "Mode has to be either `cmu` or `ibm`")
        self.__mode = mode.lower()
        if self.__mode == "cmu":
            assert (all([x is None for x in {username_ibm, password_ibm}])), (
                "Mode is `cmu`, IBM credentials should not be given")
        elif self.__mode == "ibm":
            assert ((username_ibm is not None) and
                    (password_ibm is not None)), (
                "Mode is `ibm`, IBM credentials must be provided")
        assert os.path.exists(src_dir), ("Provided path doesn't exist")

        if src_dir[-1] == "/":
            src_dir = src_dir[:-1]

        self.src_dir = src_dir
        self.__username_ibm = username_ibm
        self.__password_ibm = password_ibm
        self.verbose = verbose
        self.ibm_api_limit_bytes = ibm_api_limit_bytes
        # __timestamps is for the regulated valid timestamps. Its values is
        # a single list that contains WordBlocks. The timing of WordBlocks
        # is calculated with respect to the entire audio file.
        self.__timestamps = _PrettyDefaultDict(list)
        # __timestamps_unregulated is for the intermediary processing. Its
        # values is a list that contains other lists (as many as the splitted
        # files in the staged directory) and those lists contain WordBlocks.
        # The timing of WordBlocks is calculated with respect to the audio
        # split.
        self.__timestamps_unregulated = _PrettyDefaultDict(list)
        self.__errors = dict()
        self._needed_directories = needed_directories

    def __enter__(self):
        """
        Creates the needed directories for audio processing. Will only be
        called if the instance is initialized within a context manager.
        """
        if self.src_dir is not None:
            for directory in self._needed_directories:
                if not os.path.exists("{}/{}".format(
                        self.src_dir, directory)):
                    os.mkdir("{}/{}".format(self.src_dir, directory))
        return self

    def __exit__(self, *args):
        """
        Removes the works of __enter__. Will only be called if the instance is
        initialized within a context manager.
        """
        if self.src_dir is not None:
            for directory in self._needed_directories:
                if os.path.exists("{}/{}".format(self.src_dir, directory)):
                    rmtree("{}/{}".format(self.src_dir, directory))

    def get_mode(self):
        """
        Returns whether the instance is initialized with `ibm` or `cmu` mode.

        Returns
        -------
        str
        """
        return self.__mode

    def get_username_ibm(self):
        """
        Returns
        -------
        str, None
            Returns `str` if mode is `ibm`, else `None`
        """
        return self.__username_ibm

    def set_username_ibm(self, username_ibm):
        """
        Parameters
        ----------
        username_ibm : str

        Raises
        ------
        Exception
            If mode is not `ibm`
        """
        if self.get_mode() == "ibm":
            self.__username_ibm = username_ibm
        else:
            raise Exception(
                "Mode is {}, whereas it must be `ibm`".format(
                    self.get_moder()))

    def get_password_ibm(self):
        """
        Returns
        -------
        str, None
            Returns `str` if mode is `ibm`, else `None`
        """
        return self.__password_ibm

    def set_password_ibm(self, password_ibm):
        """
        Parameters
        ----------
        password_ibm : str

        Raises
        ------
        Exception
            If mode is not `ibm`
        """
        if self.get_mode() == "ibm":
            self.__password_ibm = password_ibm
        else:
            raise Exception(
                "Mode is {}, whereas it must be `ibm`".format(self.get_mode()))

    def get_verbosity(self):
        """
        Returns whether the instance is initialized to be quite or loud while
        processing audio files.

        Returns
        -------
        bool
            True for being verbose.
        """
        return self.verbose

    def set_verbosity(self, pred):
        """
        Parameters
        ----------
        pred : bool
        """
        self.verbose = bool(pred)

    def get_timestamps(self):
        """
        Returns a dictionary whose keys are audio file basenames and whose
        values are a list of word blocks.
        In case the audio file was large enough to be splitted, it adds seconds
        to correct timing and in case the timestamp was manually loaded, it
        leaves it alone.

        Returns
        -------
        {str: [[str, float, float]]}
        """
        return self.__timestamps

    def get_errors(self):
        """
        Returns a dictionary containing any errors while processing the
        audio files. Works for either mode.

        Returns
        -------
        {(float, str): any}
            The return is a dictionary whose keys are tuples whose first
            elements are the time of the error and whose second values are
            the audio file's name.
            The values of the dictionary are the actual errors.
        """
        return self.__errors

    def _list_audio_files(self, sub_dir=""):
        """
        Parameters
        ----------
        sub_dir : one of `needed_directories`, optional
            Default is "", which means it'll look through all of subdirs.

        Returns
        -------
        audio_files : [str]
            A list whose elements are basenames of the present audiofiles whose
            formats are `wav`
        """
        audio_files = list()
        for possibly_audio_file in os.listdir("{}/{}".format(self.src_dir,
                                                             sub_dir)):
            file_format = ''.join(possibly_audio_file.split('.')[-1])
            if file_format.lower() == "wav":
                audio_files.append(possibly_audio_file)
        return audio_files

    def _get_audio_channels(self, audio_abs_path):
        """
        Parameters
        ----------
        audio_abs_path : str

        Returns
        -------
        channel_num : int
        """
        channel_num = int(
            subprocess.check_output(
                ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}'"""
                 ).format(audio_abs_path, "Channels"),
                shell=True, universal_newlines=True).rstrip())
        return channel_num

    def _get_audio_sample_rate(self, audio_abs_path):
        """
        Parameters
        ----------
        audio_abs_path : str

        Returns
        -------
        sample_rate : int
        """
        sample_rate = int(
           subprocess.check_output(
               ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}'"""
                ).format(audio_abs_path, "Sample Rate"),
               shell=True, universal_newlines=True).rstrip())
        return sample_rate

    def _get_audio_sample_bit(self, audio_abs_path):
        """
        Parameters
        ----------
        audio_abs_path : str

        Returns
        -------
        sample_bit : int
        """
        sample_bit = int(
           subprocess.check_output(
               ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}' | """
                """grep -oh "^[^-]*" """).format(audio_abs_path, "Precision"),
               shell=True, universal_newlines=True).rstrip())
        return sample_bit

    def _get_audio_duration_seconds(self, audio_abs_path):
        """
        Parameters
        ----------
        audio_abs_path : str

        Returns
        -------
        total_seconds : int
        """
        HHMMSS_duration = subprocess.check_output(
            ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}' | """
             """grep -oh "^[^=]*" """).format(
                audio_abs_path, "Duration"),
            shell=True, universal_newlines=True).rstrip()
        total_seconds = sum(
            [float(x) * 60 ** (2 - i)
             for i, x in enumerate(HHMMSS_duration.split(":"))])
        return total_seconds

    def _get_audio_bit_rate(self, audio_abs_path):
        """
        Parameters
        -----------
        audio_abs_path : str

        Returns
        -------
        bit_rate : int
        """
        bit_Rate_formatted = subprocess.check_output(
            """sox --i {} | grep "{}" | awk -F " : " '{{print $2}}'""".format(
                audio_abs_path, "Bit Rate"),
            shell=True, universal_newlines=True).rstrip()
        bit_rate = (lambda x:
                    int(x[:-1]) * 10 ** 3 if x[-1].lower() == "k" else
                    int(x[:-1]) * 10 ** 6 if x[-1].lower() == "m" else
                    int(x[:-1]) * 10 ** 9 if x[-1].lower() == "g" else
                    int(x))(bit_Rate_formatted)
        return bit_rate

    def _seconds_to_HHMMSS(seconds):
        """
        Retuns a string which is the hour, minute, second(milli) representation
        of the intput `seconds`

        Parameters
        ----------
        seconds : float

        Returns
        -------
        str
            Has the form <int>H<int>M<int>S.<float>
        """
        less_than_second = seconds - floor(seconds)
        minutes, seconds = divmod(floor(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return "{}H{}M{}S.{}".format(hours, minutes, seconds, less_than_second)

    def _audio_segment_extractor(self, audio_abs_path, segment_abs_path,
                                 starting_second, duration):
        """
        Parameters
        -----------
        audio_abs_path : str
        segment_abs_path : str
        starting_second : int
        duration : int
        """

        subprocess.Popen(["sox",  str(audio_abs_path), str(segment_abs_path),
                          "trim", str(starting_second), str(duration)],
                         universal_newlines=True).communicate()

    def _split_audio_by_duration(self, audio_abs_path,
                                 results_abs_path, duration_seconds):
        """
        Calculates the length of each segment and passes it to
        self._audio_segment_extractor

        Parameters
        ----------
        audio_abs_path : str
        results_abs_path : str
            A place for adding digits needs to be added prior the the format
            decleration i.e. name%03.wav. Here, we've added `*` at staging
            step, which we'll replace.
        duration_seconds : int
        """
        total_seconds = self._get_audio_duration_seconds(audio_abs_path)
        current_segment = 0
        while current_segment <= total_seconds // duration_seconds + 1:
            if current_segment + duration_seconds > total_seconds:
                ending_second = total_seconds
            else:
                ending_second = current_segment + duration_seconds
            self._audio_segment_extractor(
                audio_abs_path,
                results_abs_path.replace("*", "{:03d}".format(
                    current_segment)),
                starting_second=current_segment, duration=(ending_second -
                                                           current_segment))
            current_segment += 1

    def _split_audio_by_size(self, audio_abs_path, results_abs_path,
                             chunk_size):
        """
        Calculates the duration of the name.wav in order for all splits have
        the size of chunk_size except possibly the last split (which will be
        smaller) and then passes the duration to `split_audio_by_duration`

        Parameters
        ----------
        audio_abs_path : str
        results_abs_path : str
            A place for adding digits needs to be added prior the the format
            decleration i.e. name%03.wav
        chunk_size : int
            Should be in bytes
        """
        sample_rate = self._get_audio_sample_rate(audio_abs_path)
        sample_bit = self._get_audio_sample_bit(audio_abs_path)
        channel_num = self._get_audio_channels(audio_abs_path)
        duration = 8 * chunk_size / reduce(lambda x, y: int(x) * int(y),
                                           [sample_rate, sample_bit,
                                            channel_num])
        self._split_audio_by_duration(audio_abs_path, results_abs_path,
                                      duration)

    def _filtering_step(self, basename):
        """
        Moves the audio file if the format is `wav` to `filtered` directory.

        Parameters
        ----------
        basename : str
            A basename of `/home/random-guy/some-audio-file.wav` is
            `some-audio-file.wav`
        """
        name = ''.join(basename.split('.')[:-1])
        # May cause problems if wav is not less than 9 channels.
        if basename.split('.')[-1] == "wav":
            if self.get_verbosity():
                print("Found wave! Copying to {}/filtered/{}".format(
                    self.src_dir, basename))
            subprocess.Popen(["cp", "{}/{}.wav".format(self.src_dir, name),
                              "{}/filtered/{}.wav".format(self.src_dir, name)],
                             universal_newlines=True).communicate()

    def _staging_step(self, basename):
        """
        Checks the size of audio file, splits it if it's needed to manage api
        limit and then moves to `staged` directory while appending `*` to
        the end of the filename for self.split_audio_by_duration to replace
        it by a number.

        Parameters
        ----------
        basename : str
            A basename of `/home/random-guy/some-audio-file.wav` is
            `some-audio-file.wav`
        """
        name = ''.join(basename.split('.')[:-1])

        if self.get_mode() == "ibm":
            # Checks the file size. It's better to use 95% of the allocated
            # size per file since the upper limit is not always respected.
            total_size = os.path.getsize("{}/filtered/{}.wav".format(
                self.src_dir, name))
            if total_size >= self.ibm_api_limit_bytes:
                if self.get_verbosity():
                    print(("{}'s size over API limit ({}). Splitting").format(
                        name, self.ibm_api_limit_bytes))
                self._split_audio_by_size(
                    "{}/filtered/{}.wav".format(self.src_dir, name),
                    "{}/staging/{}*.wav".format(self.src_dir, name),
                    self.ibm_api_limit_bytes * 95 / 100)
            else:
                if self.get_verbosity():
                    print("{}'s size is fine. Moving to staging dir'".format(
                        name))
                subprocess.Popen((
                    "mv {}/filtered/{}.wav {}/staging/{}000.wav").format(
                                    self.src_dir, name, self.src_dir, name),
                                 shell=True,
                                 universal_newlines=True).communicate()

        elif self.get_mode() == "cmu":
            if self.get_verbosity():
                print("Converting {} to a readable wav".format(basename))
            ffmpeg = os.path.basename(find_executable("ffmpeg") or
                                      find_executable("avconv"))
            if ffmpeg is None:
                raise Exception(("Either ffmpeg or avconv is needed. "
                                 "Neither is installed or accessible"))
            try:
                # ffmpeg log levels:
                # https://ffmpeg.org/ffmpeg.html#Generic-options
                ffmpeg_log_level = "8"  # fatal errors.
                if self.get_verbosity():
                    ffmpeg_log_level = "32"  # info `default for ffmpeg`
                subprocess.check_call([
                    str(ffmpeg), "-y", "-i", "{}/filtered/{}.wav".format(
                        self.src_dir, str(name)), "-acodec", "pcm_s16le",
                    "-ac", "1", "-ar", "16000", "{}/staging/{}000.wav".format(
                        self.src_dir, name),
                    "-v", ffmpeg_log_level], universal_newlines=True)
            except subprocess.CalledProcessError as e:
                print(e)
            if os.path.exists("{}/staging/{}000.wav".format(
                    self.src_dir, name)):
                if self.get_verbosity():
                    print(("{}/filtered/{} was converted to "
                           "{}/staging/{}000.wav Now removing the copy of "
                           "{} in filtered sub directory").format(
                                self.src_dir, basename,
                                self.src_dir, name, basename))
                subprocess.Popen([
                    "rm", "{}/filtered/{}".format(self.src_dir, basename)],
                                    universal_newlines=True).communicate()
            else:
                raise Exception("Something went wrong with ffmpeg conversion!")

    def _prepare_audio(self, basename, replace_already_indexed=False):
        """
        Prepares and stages the audio file to be indexed.

        Parameters
        ----------
        basename : str, None
            A basename of `/home/random-guy/some-audio-file.wav` is
            `some-audio-file.wav`
            If basename is `None`, it'll prepare all the audio files.
        """
        if basename is not None:
            if basename in self.get_timestamps():
                if self.get_verbosity():
                    print("File specified was already indexed. Reindexing...")
                del self.__timestamps[basename]
            self._filtering_step(basename)
            self._staging_step(basename)
        else:
            for audio_basename in self._list_audio_files():
                if audio_basename in self.__timestamps:
                    if replace_already_indexed:
                        if self.get_verbosity():
                            print("Already indexed {}. Reindexing...".format(
                                audio_basename))
                        del self.__timestamps[audio_basename]
                    else:
                        if self.get_verbosity():
                            print("Already indexed {}. Skipping...".format(
                                audio_basename))
                        continue
                self._filtering_step(audio_basename)
                self._staging_step(audio_basename)

    def _index_audio_cmu(self, basename=None, replace_already_indexed=False):
        """
        Indexes audio with pocketsphinx. Beware that the output would not be
        sufficiently accurate. Use this only if you don't want to upload your
        files to IBM.

        Parameters
        -----------
        basename : str, optional
            A specific basename to be indexed and is placed in src_dir
            E.g. `audio.wav`.

            If `None` is selected, all the valid audio files would be indexed.
            Default is `None`.

        Raises
        ------
        OSError
            If the output of pocketsphinx command results in an error.
        """
        self._prepare_audio(basename=basename,
                            replace_already_indexed=replace_already_indexed)

        for staging_audio_basename in self._list_audio_files(
                sub_dir="staging"):
            original_audio_name = ''.join(
                staging_audio_basename.split('.')[:-1])[:-3]
            pocketsphinx_command = ''.join([
                "pocketsphinx_continuous", "-infile",
                str("{}/staging/{}".format(
                    self.src_dir, staging_audio_basename)),
                "-time", "yes", "-logfn", "/dev/null"])
            try:
                if self.get_verbosity():
                    print("Now indexing {}".format(staging_audio_basename))
                output = subprocess.check_output([
                    "pocketsphinx_continuous", "-infile",
                    str("{}/staging/{}".format(
                        self.src_dir, staging_audio_basename)),
                    "-time", "yes", "-logfn", "/dev/null"
                ], universal_newlines=True).split('\n')
                str_timestamps_with_sil_conf = list(map(
                    lambda x: x.split(" "), filter(None, output[1:])))
                # Timestamps are putted in a list of a single element. To match
                # Watson's output.
                self.__timestamps_unregulated[
                    original_audio_name + ".wav"] = [(
                        self._timestamp_extractor_cmu(
                            staging_audio_basename,
                            str_timestamps_with_sil_conf))]
                if self.get_verbosity():
                    print("Done indexing {}".format(staging_audio_basename))
            except OSError as e:
                if self.get_verbosity():
                    print(e, "The command was: {}".format(
                        pocketsphinx_command))
                self.__errors[(time(), staging_audio_basename)] = e
        self._timestamp_regulator()

        if self.get_verbosity():
            print("Finished indexing procedure")

    def _timestamp_extractor_cmu(self, staging_audio_basename,
                                 str_timestamps_with_sil_conf):
        """
        Parameters
        ----------
        str_timestamps_with_sil_conf : [[str, str, str, str]]
            Of the form [[word, starting_sec, ending_sec, confidence]]

        Returns
        -------
        timestamps : [[str, float, float]]
        """
        filter_untimed = filter(lambda x: len(x) == 4,
                                str_timestamps_with_sil_conf)
        if filter_untimed != str_timestamps_with_sil_conf:
            self.__errors[
                (time(), staging_audio_basename)
            ] = str_timestamps_with_sil_conf
        str_timestamps = [
            str_timestamp[:-1]
            for str_timestamp in filter_untimed
            if not any([letter in {"<", ">", "/"}
                        for letter in ''.join(str_timestamp)])]
        timestamps = list([
            _WordBlock(
                word=re.findall("^[^\(]+", x[0])[0],
                start=round(float(x[1]), 2),
                end=round(float(x[2]), 2)
            ) for x in str_timestamps])
        return timestamps

    def _index_audio_ibm(self, basename=None, replace_already_indexed=False,
                         continuous=True, model="en-US_BroadbandModel",
                         word_confidence=True, word_alternatives_threshold=0.9,
                         profanity_filter_for_US_results=False):
        """
        Implements a search-suitable interface for Watson speech API.

        Some explaination of the parameters here have been taken from [1]_

        Parameters
        ----------
        basename : str, optional
            A specific basename to be indexed and is placed in src_dir
            e.g `audio.wav`.

            If `None` is selected, all the valid audio files would be indexed.
            Default is `None`.

        replace_already_indexed : bool
            `True`, To reindex some audio file that's already in the
             timestamps.

             Default is `False`.

        continuous : bool
            Indicates whether multiple final results that represent consecutive
            phrases separated by long pauses are returned.
            If true, such phrases are returned; if false (the default),
            recognition ends after the first end-of-speech (EOS) incident is
            detected.

            Default is `True`.
        model :  {
                    'ar-AR_BroadbandModel',
                    'en-UK_BroadbandModel'
                    'en-UK_NarrowbandModel',
                    'en-US_BroadbandModel', (the default)
                    'en-US_NarrowbandModel',
                    'es-ES_BroadbandModel',
                    'es-ES_NarrowbandModel',
                    'fr-FR_BroadbandModel',
                    'ja-JP_BroadbandModel',
                    'ja-JP_NarrowbandModel',
                    'pt-BR_BroadbandModel',
                    'pt-BR_NarrowbandModel',
                    'zh-CN_BroadbandModel',
                    'zh-CN_NarrowbandModel'
                 }
            The identifier of the model to be used for the recognition

            Default is 'en-US_BroadbandModel'
        word_confidence : bool
            Indicates whether a confidence measure in the range of 0 to 1 is
            returned for each word.

            The default is True. (It's False in the original)
        word_alternatives_threshold : numeric
            A confidence value that is the lower bound for identifying a
            hypothesis as a possible word alternative (also known as
            "Confusion Networks"). An alternative word is considered if its
            confidence is greater than or equal to the threshold. Specify a
            probability between 0 and 1 inclusive.

            Default is `0.9`.
        profanity_filter_for_US_results : bool
            Indicates whether profanity filtering is performed on the
            transcript. If true, the service filters profanity from all output
            by replacing inappropriate words with a series of asterisks.

            If false, the service returns results with no censoring. Applies
            to US English transcription only.

            Default is `False`.

        References
        ----------
        .. [1] : https://ibm.com/watson/developercloud/speech-to-text/api/v1/
        """
        params = {'continuous': continuous,
                  'model': model,
                  'word_alternatives_threshold': word_alternatives_threshold,
                  'word_confidence': word_confidence,
                  'timestamps': True,
                  'inactivity_timeout': str(-1),
                  'profanity_filter': profanity_filter_for_US_results}

        self._prepare_audio(basename=basename,
                            replace_already_indexed=replace_already_indexed)

        for staging_audio_basename in self._list_audio_files(
                sub_dir="staging"):
            original_audio_name = ''.join(
                staging_audio_basename.split('.')[:-1])[:-3]
            with open("{}/staging/{}".format(
                    self.src_dir, staging_audio_basename), "rb") as f:
                if self.get_verbosity():
                    print("Uploading {}...".format(staging_audio_basename))
                response = requests.post(
                    url=("https://stream.watsonplatform.net/"
                         "speech-to-text/api/v1/recognize"),
                    auth=(self.get_username_ibm(), self.get_password_ibm()),
                    headers={'content-type': 'audio/wav'},
                    data=f.read(),
                    params=params)
                if self.get_verbosity():
                    print("Indexing {}...".format(staging_audio_basename))
                self.__timestamps_unregulated[
                    original_audio_name + ".wav"].append(
                        self._timestamp_extractor_ibm(
                            staging_audio_basename, json.loads(response.text)))
                if self.get_verbosity():
                    print("Done indexing {}".format(staging_audio_basename))
        self._timestamp_regulator()

        if self.get_verbosity():
            print("Indexing procedure finished")

    def _timestamp_extractor_ibm(self, staging_audio_basename, audio_json):
        """
        Parameters
        ----------
        audio_json : {str: [{str: [{str: str or nuneric}]}]}
            Refer to Watson Speech API refrence [1]_

        Returns
        -------
        [[str, float, float]]
            A list whose members are lists. Each member list has three
            elements. First one is a word. Second is the starting second and
            the third is the ending second of that word in the original
            audio file.
        """
        try:
            timestamps_of_sentences = [
                audio_json['results'][i]['alternatives'][0]['timestamps']
                for i in range(len(audio_json['results']))]
            return [
                _WordBlock(
                    word=word_block[0],
                    start=round(float(word_block[1]), 2),
                    end=round(float(word_block[2]), 2)
                ) for sentence_block in timestamps_of_sentences
                for word_block in sentence_block]
        except KeyError:
            self.__errors[(time(), staging_audio_basename)] = audio_json
            if self.get_verbosity():
                print(audio_json)
                print("The resulting request from Watson was unintelligible.")
            return False

    def index_audio(self, *args, **kwargs):
        """
        Calls the correct indexer function based on the mode.

        If mode is `ibm`, _indexer_audio_ibm is called which is an interface
        for Watson. Note that some of the explaination of _indexer_audio_ibm's
        arguments is from [1]_

        If mode is `cmu`, _indexer_audio_cmu is called which is an interface
        for PocketSphinx Beware that the output would not be sufficiently
        accurate. Use this only if you don't want to upload your files to IBM.

        Parameters
        ----------
        mode : {"ibm", "cmu"}

        basename : str, optional

            A specific basename to be indexed and is placed in src_dir
            e.g `audio.wav`.

            If `None` is selected, all the valid audio files would be indexed.
            Default is `None`.

        replace_already_indexed : bool

            `True`, To reindex some audio file that's already in the
            timestamps.

            Default is `False`.

        continuous : bool

            Valid Only if mode is `ibm`

            Indicates whether multiple final results that represent consecutive
            phrases separated by long pauses are returned.
            If true, such phrases are returned; if false (the default),
            recognition ends after the first end-of-speech (EOS) incident is
            detected.

            Default is `True`.

        model :  {
                    'ar-AR_BroadbandModel',
                    'en-UK_BroadbandModel'
                    'en-UK_NarrowbandModel',
                    'en-US_BroadbandModel', (the default)
                    'en-US_NarrowbandModel',
                    'es-ES_BroadbandModel',
                    'es-ES_NarrowbandModel',
                    'fr-FR_BroadbandModel',
                    'ja-JP_BroadbandModel',
                    'ja-JP_NarrowbandModel',
                    'pt-BR_BroadbandModel',
                    'pt-BR_NarrowbandModel',
                    'zh-CN_BroadbandModel',
                    'zh-CN_NarrowbandModel'
                 }

            Valid Only if mode is `ibm`

            The identifier of the model to be used for the recognition

            Default is 'en-US_BroadbandModel'

        word_confidence : bool

            Valid Only if mode is `ibm`

            Indicates whether a confidence measure in the range of 0 to 1 is
            returned for each word.

            The default is True. (It's False in the original)

        word_alternatives_threshold : numeric

            Valid Only if mode is `ibm`

            A confidence value that is the lower bound for identifying a
            hypothesis as a possible word alternative (also known as
            "Confusion Networks"). An alternative word is considered if its
            confidence is greater than or equal to the threshold. Specify a
            probability between 0 and 1 inclusive.

            Default is `0.9`.

        profanity_filter_for_US_results : bool

            Valid Only if mode is `ibm`

            Indicates whether profanity filtering is performed on the
            transcript. If true, the service filters profanity from all output
            by replacing inappropriate words with a series of asterisks.

            If false, the service returns results with no censoring. Applies
            to US English transcription only.

            Default is `False`.

        Raises
        ------
        OSError

            Valid only if mode is `cmu`.

            If the output of pocketsphinx command results in an error.

        References
        ----------
        .. [1] : https://ibm.com/watson/developercloud/speech-to-text/api/v1/

        Else if mode is `cmu`, then _index_audio_cmu would be called:
        """
        with _Subdirectory_Managing_Decorator(
                self.src_dir, self._needed_directories):
            if self.get_mode() == "ibm":
                self._index_audio_ibm(*args, **kwargs)
            elif self.get_mode() == "cmu":
                self._index_audio_cmu(*args, **kwargs)

    def _timestamp_regulator(self):
        """
        Makes a dictionary whose keys are audio file basenames and whose
        values are a list of word blocks from unregulated timestamps and
        updates the main timestamp attribute. After all done, purges
        unregulated ones.
        In case the audio file was large enough to be splitted, it adds seconds
        to correct timing and in case the timestamp was manually loaded, it
        leaves it alone.

        Note that the difference between self.__timestamps and
        self.__timestamps_unregulated is that in the regulated version,
        right after the word, a list of word blocks must appear. However in the
        unregulated version, after a word, a list of individual splits
        containing word blocks would appear!
        """
        unified_timestamps = _PrettyDefaultDict(list)
        staged_files = self._list_audio_files(sub_dir="staging")
        for timestamp_basename in self.__timestamps_unregulated:
            if len(self.__timestamps_unregulated[timestamp_basename]) > 1:
                # File has been splitted
                timestamp_name = ''.join(timestamp_basename.split('.')[:-1])
                staged_splitted_files_of_timestamp = list(
                    filter(lambda staged_file: (
                        timestamp_name == staged_file[:-3] and
                        all([(x in set(map(str, range(10))))
                             for x in staged_file[-3:]])), staged_files))
                if len(staged_splitted_files_of_timestamp) == 0:
                    self.__errors[(time(), timestamp_basename)] = {
                        "reason": "Missing staged file",
                        "current_staged_files": staged_files}
                    continue
                staged_splitted_files_of_timestamp.sort()
                unified_timestamp = list()
                for staging_digits, splitted_file in enumerate(
                        self.__timestamps_unregulated[timestamp_basename]):
                    prev_splits_sec = 0
                    if int(staging_digits) != 0:
                        prev_splits_sec = self._get_audio_duration_seconds(
                            "{}/staging/{}{:03d}".format(
                                self.src_dir, timestamp_name,
                                staging_digits - 1))
                    for word_block in splitted_file:
                        unified_timestamp.append(
                            _WordBlock(
                                word=word_block.word,
                                start=round(word_block.start +
                                            prev_splits_sec, 2),
                                end=round(word_block.end +
                                          prev_splits_sec, 2)))
                unified_timestamps[
                    str(timestamp_basename)] += unified_timestamp
            else:
                unified_timestamps[
                    timestamp_basename] += self.__timestamps_unregulated[
                        timestamp_basename][0]

        self.__timestamps.update(unified_timestamps)
        self.__timestamps_unregulated = _PrettyDefaultDict(list)

    def save_indexed_audio(self, indexed_audio_file_abs_path):
        """
        Writes the corrected timestamps to a file. Timestamps are a python
        dictionary.

        Parameters
        ----------
        indexed_audio_file_abs_path : str
        """
        with open(indexed_audio_file_abs_path, "wb") as f:
            pickle.dump(self.get_timestamps(), f, pickle.HIGHEST_PROTOCOL)

    def load_indexed_audio(self, indexed_audio_file_abs_path):
        """
        Parameters
        ----------
        indexed_audio_file_abs_path : str
        """
        with open(indexed_audio_file_abs_path, "rb") as f:
            self.__timestamps = pickle.load(f)

    def _is_anagram_of(self, candidate, target):
        """
        Parameters
        ----------
        candidate : str
        target : str

        Returns
        --------
        bool
        """
        return (sorted(candidate) == sorted(target))

    def _is_subsequence_of(self, sub, sup):
        """
        Parameters
        ----------
        sub : str
        sup : str

        Returns
        -------
        bool
        """
        return bool(re.search(".*".join(sub), sup))

    def _is_supersequence_of(self, sup, sub):
        """
        Parameters
        ----------
        sub : str
        sup : str

        Returns
        -------
        bool
        """
        return self._is_subsequence_of(sub, sup)

    def _partial_search_validator(self, sub, sup, anagram=False,
                                  subsequence=False, supersequence=False):
        """
        It's responsible for validating the partial results of `search` method.
        If it returns True, the search would return its result. Else, search
        method would discard what it found and look for others.

        First, checks to see if all elements of `sub` is in `sup` with at least
        the same frequency and then checks to see if every element `sub`
        appears in `sup` with the same order (index-wise).
        If advanced control sturctures are specified, the containment condition
        won't be checked.
        The code for index checking is from [1]_.

        Parameters
        ----------
        sub : list
        sup : list
        anagram : bool, optional
            Default is `False`
        subsequence : bool, optional
            Default is `False`
        supersequence : bool, optional
            Default is `False`

        Returns
        -------
        bool

        References
        ----------
        .. [1] : `
   https://stackoverflow.com/questions/35964155/checking-if-list-is-a-sublist`
        """
        def get_all_in(one, another):
            for element in one:
                if element in another:
                    yield element

        def containment_check(sub, sup):
            return (set(Counter(sub).keys()).issubset(
                set(Counter(sup).keys())))

        def containment_freq_check(sub, sup):
            return (all([Counter(sub)[element] <= Counter(sup)[element]
                         for element in Counter(sub)]))

        def extra_freq_check(sub, sup, list_of_tups):
            # Would be used for matching anagrams, subsequences etc.
            return (len(list_of_tups) > 0 and
                    all([Counter(sub)[tup[0]] <= Counter(sup)[tup[1]]
                         for tup in list_of_tups]))

        # Regarding containment checking while having extra conditions,
        # there's no good way to map each anagram or subseuqnece etc. that was
        # found to the query word, without making it more complicated than
        # it already is, because a query word can be anagram/subsequence etc.
        # to multiple words of the timestamps yet finding the one with the
        # right index would be the problem.
        # Therefore we just approximate the solution by just counting
        # the elements.
        if len(sub) > len(sup):
            return False

        for pred, func in set([(anagram, self._is_anagram_of),
                               (subsequence, self._is_subsequence_of),
                               (supersequence, self._is_supersequence_of)]):
            if pred:
                pred_seive = [(sub_key, sup_key)
                              for sub_key in set(Counter(sub).keys())
                              for sup_key in set(Counter(sup).keys())
                              if func(sub_key, sup_key)]
                if not extra_freq_check(sub, sup, pred_seive):
                    return False

        if (
                not any([anagram, subsequence, supersequence]) and
                (not containment_check(sub, sup) or
                 not containment_freq_check(sub, sup))
        ):
                return False

        for x1, x2 in zip(get_all_in(sup, sub), get_all_in(sub, sup)):
            if x1 != x2:
                return False

        return True

    def search_gen(self, query, audio_basename=None, case_sensitive=False,
                   subsequence=False, supersequence=False, timing_error=0.0,
                   anagram=False, missing_word_tolerance=0):
        """
        A generator that searches for the `query` within the audiofiles of the
        src_dir.

        Parameters
        ----------
        query : str
            A string that'll be searched. It'll be splitted on spaces and then
            each word gets sequentially searched.
        audio_basename : str, optional
            Search only within the given audio_basename.

            Default is `None`
        case_sensitive : bool, optional
            Default is `False`
        subsequence : bool, optional
            `True` if it's not needed for the exact word be detected and larger
            strings that contain the given one are fine.

            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.

            Default is `False`.
        supersequence : bool, optional
            `True` if it's not needed for the exact word be detected and
            smaller strings that are contained within the given one are fine.

            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.

            Default is `False`.
        anagram : bool, optional
            `True` if it's acceptable for a complete permutation of the word to
            be found. e.g. "abcde" would be acceptable for "edbac".

            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.

            Default is `False`.
        timing_error : None or float, optional
            Sometimes other words (almost always very small) would be detected
            between the words of the `query`. This parameter defines the
            timing difference/tolerance of the search.

            Default is 0.0 i.e. No timing error is tolerated.
        missing_word_tolerance : int, optional
            The number of words that can be missed within the result.
            For example, if the query is "Some random text" and the tolerance
            value is `1`, then "Some text" would be a valid response.
            Note that the first and last words cannot be missed. Also,
            there'll be an error if the value is more than the number of
            available words. For the example above, any value more than 1
            would have given an error (since there's only one word i.e.
            "random" that can be missed)

            Default is 0.

        Yields
        ------
        {"File Name": str, "Query": `query`, "Result": (float, float)}
            The result of the search is returned as a tuple which is the value
            of the "Result" key. The first element of the tuple is the
            starting second of `query` and the last element is the ending
            second of `query`

        Raises
        ------
        AssertionError
            If `missing_word_tolerance` value is more than the total number of
            words in the query minus 2 (since the first and the last word
            cannot be removed)
        """
        def case_sensitivity_handler(case_sensitive=case_sensitive):

            def get_query_words(query, case_sensitive=case_sensitive):
                query_words = list(
                    filter(None, ''.join(
                        filter(lambda char: char in (ascii_letters + " "),
                               list(query))).split(" ")))
                if case_sensitive:
                    return query_words
                return [q.lower() for q in query_words]

            def get_timestamps(case_sensitive=case_sensitive):
                timestamps = self.get_timestamps().copy()
                if not case_sensitive:
                    return {
                        audio_basename: [
                            _WordBlock(word=word_block.word.lower(),
                                       start=word_block.start,
                                       end=word_block.end)
                            for word_block in timestamps[audio_basename]]
                        for audio_basename in timestamps}
                return timestamps

            return locals()

        query_words = case_sensitivity_handler()["get_query_words"](query)
        timestamps = case_sensitivity_handler()["get_timestamps"]()

        assert abs(missing_word_tolerance -
                   (len(query_words) - 2)) >= 0, (
            "The number of words that can be missing must be less than "
            "the total number of words within the query minus the first and "
            "the last word."
        )

        for audio_filename in (
                (lambda: (timestamps.keys() if audio_basename is None else
                          [audio_basename]))()):
            result = list()
            missed_words_so_far = 0
            query_cursor = 0
            try:
                for word_block in timestamps[audio_filename]:
                    if (
                            # When the query is identical
                            (word_block.word == query_words[query_cursor]) or
                            # When the query is a subsequence of what's
                            # available
                            (subsequence and
                             self._is_subsequence_of(query_words[query_cursor],
                                                     word_block.word)) or
                            # When the query is a supersequence of what's
                            # available
                            (supersequence and self._is_supersequence_of(
                                query_words[query_cursor], word_block.word)) or
                            # When query is a permutation of what's available.
                            (anagram and self._is_anagram_of(
                                query_words[query_cursor], word_block.word))
                    ):
                        result.append(word_block)

                        if timing_error is not None:
                            try:
                                if round(result[-1].start -
                                         result[-2].end, 4) > timing_error:
                                    result = list()
                                    query_cursor = 0
                            except IndexError:
                                pass

                        if self._partial_search_validator(
                                query_words, [x.word for x in result],
                                anagram=anagram,
                                subsequence=subsequence,
                                supersequence=supersequence):
                            yield {
                                "File Name": audio_filename,
                                "Query": query,
                                "Result": tuple([result[0].start,
                                                 result[-1].end])}
                            result = list()
                            query_cursor = 0

                        else:
                            query_cursor += 1

                    elif missed_words_so_far > missing_word_tolerance:
                        result = list()
                        query_cursor = 0

                    elif (missing_word_tolerance > 0) and (len(result) > 0):
                        result.append(word_block)
                        missed_words_so_far += 1

            except KeyError:
                # This is needed for the case where no timestamp is present.
                pass

            except IndexError:
                # This is needed when multiple timestamps are present, and
                # advanced control structures like `missed_word_tolerance` are
                # non-zero. In that case, it can search to the end of the first
                # timestamp looking to complete its partial result and since
                # there are no more `word_block`s left, it returns an error.
                # `continue` should be used to reset the partial result and
                # move to the next timestamp.
                continue

    def search_all(self, queries, audio_basename=None, case_sensitive=False,
                   subsequence=False, supersequence=False, timing_error=0.0,
                   anagram=False, missing_word_tolerance=0):
        """
        Returns a dictionary of all results of all of the queries for all of
        the audio files.
        All the specified parameters work per query.

        Parameters
        ----------
        queries : [str] or str
            A list of the strings that'll be searched. If type of queries is
            `str`, it'll be insterted into a list within the body of the
            method.
        audio_basename : str, optional
            Search only within the given audio_basename.

            Default is `None`.
        case_sensitive : bool
            Default is `False`
        subsequence : bool, optional
            `True` if it's not needed for the exact word be detected and larger
            strings that contain the given one are fine.

            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.

            Default is `False`.
        supersequence : bool, optional
            `True` if it's not needed for the exact word be detected and
            smaller strings that are contained within the given one are fine.

            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.

            Default is `False`.
        anagram : bool, optional
            `True` if it's acceptable for a complete permutation of the word to
            be found. e.g. "abcde" would be acceptable for "edbac".

            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.

            Default is `False`.
        timing_error : None or float, optional
            Sometimes other words (almost always very small) would be detected
            between the words of the `query`. This parameter defines the
            timing difference/tolerance of the search.

            Default is 0.0 i.e. No timing error is tolerated.
        missing_word_tolerance : int, optional
            The number of words that can be missed within the result.
            For example, if the query is "Some random text" and the tolerance
            value is `1`, then "Some text" would be a valid response.
            Note that the first and last words cannot be missed. Also,
            there'll be an error if the value is more than the number of
            available words. For the example above, any value more than 1
            would have given an error (since there's only one word i.e.
            "random" that can be missed)

            Default is 0.

        Returns
        -------
        search_results : {str: {str: [(float, float)]}}
            A dictionary whose keys are queries and whose values are
            dictionaries whose keys are all the audiofiles in which the query
            is present and whose values are a list whose elements are 2-tuples
            whose first element is the starting second of the query and whose
            values are the ending second. e.g.
            {"apple": {"fruits.wav" : [(1.1, 1.12)]}}

        Raises
        ------
        TypeError
            if `queries` is neither a list nor a str
        """

        search_gen_rest_of_kwargs = {
            "audio_basename": audio_basename,
            "case_sensitive": case_sensitive,
            "subsequence": subsequence,
            "supersequence": supersequence,
            "timing_error": timing_error,
            "anagram": anagram,
            "missing_word_tolerance": missing_word_tolerance}

        if not isinstance(queries, (list, str)):
            raise TypeError("Invalid query type.")
        if type(queries) is not list:
            queries = [queries]
        search_results = _PrettyDefaultDict(lambda: _PrettyDefaultDict(list))
        for query in queries:
            search_gen = self.search_gen(query=query,
                                         **search_gen_rest_of_kwargs)
            for search_result in search_gen:
                search_results[query][
                    search_result["File Name"]].append(search_result["Result"])
        return search_results

    def search_regexp(self, pattern, audio_basename=None):
        """
        First joins the words of the word_blocks of timestamps with space, per
        audio_basename. Then matches `pattern` and calculates the index of the
        word_block where the first and last word of the matched result appears
        in. Then presents the output like `search_all` method.

        Note that the leading and trailing spaces from the matched results
        would be removed while determining which word_block they belong to.

        Parameters
        ----------
        pattern : str
            A regex pattern.
        audio_basename : str, optional
            Search only within the given audio_basename.

            Default is `False`.

        Returns
        -------
        search_results : {str: {str: [(float, float)]}}
            A dictionary whose keys are queries and whose values are
            dictionaries whose keys are all the audiofiles in which the query
            is present and whose values are a list whose elements are 2-tuples
            whose first element is the starting second of the query and whose
            values are the ending second. e.g.
            {"apple": {"fruits.wav" : [(1.1, 1.12)]}}
        """

        def indexes_in_transcript_to_start_end_second(index_tup,
                                                      audio_basename):
            """
            Calculates the word block index by having the beginning and ending
            index of the matched result from the transcription

            Parameters
            ----------
            index_tup : (int, tup)
                index_tup is of the form tuple(index_start, index_end)
            audio_basename : str

            Retrun
            ------
            [float, float]
                The time of the output of the matched result. Derived from two
                separate word blocks belonging to the beginning and the end of
                the index_start and index_end.
            """
            space_indexes = [i for i, x in enumerate(
                transcription[audio_basename]) if x == " "]
            space_indexes.sort(reverse=True)
            index_start, index_end = index_tup
            # re.finditer returns the ending index by one more
            index_end -= 1
            while transcription[audio_basename][index_start] == " ":
                index_start += 1
            while transcription[audio_basename][index_end] == " ":
                index_end -= 1
            block_number_start = 0
            block_number_end = len(space_indexes)
            for block_cursor, space_index in enumerate(space_indexes):
                if index_start > space_index:
                    block_number_start = (len(space_indexes) - block_cursor)
                    break
            for block_cursor, space_index in enumerate(space_indexes):
                if index_end > space_index:
                    block_number_end = (len(space_indexes) - block_cursor)
                    break
            return (timestamps[audio_basename][block_number_start].start,
                    timestamps[audio_basename][block_number_end].end)

        timestamps = self.get_timestamps()
        if audio_basename is not None:
            timestamps = {audio_basename: timestamps[audio_basename]}
        transcription = {
            audio_basename: ' '.join(
                [word_block.word for word_block in timestamps[audio_basename]]
            ) for audio_basename in timestamps}
        match_map = map(
            lambda audio_basename: tuple((
                audio_basename,
                re.finditer(pattern, transcription[audio_basename]))),
            transcription.keys())
        search_results = _PrettyDefaultDict(lambda: _PrettyDefaultDict(list))
        for audio_basename, match_iter in match_map:
            for match in match_iter:
                search_results[match.group()][audio_basename].append(
                    tuple(indexes_in_transcript_to_start_end_second(
                        match.span(), audio_basename)))
        return search_results
