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
from ast import literal_eval
from collections import defaultdict
from distutils.spawn import find_executable
from functools import reduce
from math import floor
from shutil import rmtree
from string import ascii_letters
import json
import os
import re
import requests
import subprocess


needed_directories = {"filtered", "staging"}


class SimpleAudioIndexer(object):
    """
    Should write overall process focusing on src_dir events


    Attributes
    ----------
    username:           str
                        IBM Watson API username
    password:           str
                        IBM Watson API password
    src_dir:            str
                        Absolute path to the source directory of audio files
                        such that the absolute path of the audio that'll be
                        indexed would be `src_dir/audio_file.wav`
    verbose:            Bool
                        `True` if progress needs to be printed
    __api_limit_bytes:  int
                        It holds the API limitation of Watson speech api http
                        sessionless which is 100Mbs.
    __timestamps:       defaultdict(list)
                        It holds the timestamps of the audio in a format
                        similar to above
    __ffmpeg:           str
                        Looks to see if ffmpeg is installed, if not, searches
                        for avconv.

    Methods
    -------
    get_username()
    set_username()
    get_password()
    set_password()
    _filtered_step(basename)
        Moves the audio to `filtered` dir if its format is `wav`
    _staging_step(basename)
        Splits the audio -if needed to be under api limit- and then moves it
        to `staged` directory.
    _prepare_audio(basename)
        A method that'll be called from the method `index_audio`. This method
        primarily validates/splits and reads the audio file(s)
    list_audio_files(sub_dir, only_wav)
        Returns a list of audiofiles in a subdir or the self.src_dir whose
        formats are `wav`
    get_audio_channels(abs_path_audio)
    get_audio_sample_rate(abs_path_audio)
    get_audio_sample_bit(abs_path_audio)
    get_audio_duration_seconds(abs_path_audio)
    get_audio_bit_rate(abs_path_audio)
    split_audio_by_duration(audio_abs_path, results_abs_path, duration_seconds)
    split_audio_by_size(audio_abs_path, results_abs_path, chunk_size)
    index_audio(name=None, continuous=True, model="en-US_BroadbandModel",
                word_confidence=True, word_alternatives_threshold=0.9,
                keywords=None, keywords_threshold=None,
                profanity_filter_for_US_results=False)
        Implements a searching-suitable interface for the Watson API
    _timestamp_extractor(audio_json)
        Parses the generated Json from `index_audio` method to get the
        timestamps. It works for a single audio file that's less than 100M
    get_timestamped_audio()
        Returns a corrected dictionary whose key is the original file name and
        whose value is a list of words and their beginning and ending time. It
        accounts for large files and does the timing calculations to return the
        correct result.
    save_indexed_audio(indexed_audio_file_abs_path)
    load_indexed_audio(indexed_audio_file_abs_path)
    search(query, audio_basename, subsequence, timing_error, case_sensitive)
    search_all(queries, audio_basename, part_of_bigger_word, timing_error)
        Returns a dictionary of all results of all of the queries for all of
        the audio files.
    seconds_to_HHMMSS(seconds)
        Retuns a string which is the hour, minute, second(milli) representation
        of the intput `seconds`
    """

    def __init__(self, username, password, src_dir, api_limit_bytes=100000000,
                 verbose=False):
        """
        Parameters
        ----------
        username:           str
        password:           str
        src_dir             str
                            Absolute path to the source directory of audio
                            files such that the absolute path of the audio
                            that'll be indexed would be
                            `src_dir/audio_file.wav`
        api_limit_bytes:    int
        verbose:            Bool

        Raises
        ------
        Exception           If ffmpeg and avconv are not installed
        """
        self.username = username
        self.password = password
        self.verbose = verbose
        self.src_dir = src_dir
        self.__api_limit_bytes = api_limit_bytes
        self.__timestamps = defaultdict(list)
        # Recently no ffmpeg for Ubuntu or Debian. All the used commands here
        # are compatible for avconv so either one would work.
        self.__ffmpeg = os.path.basename(find_executable("ffmpeg") or
                                         find_executable("avconv"))
        if self.__ffmpeg is None:
            raise Exception("Either ffmpeg or avconv is needed. " +
                            "Neither is installed or accessible")
        # Because `needed_directories` are needed even if the initialization of
        # the object is not in a context manager for it to be created
        # automatically.
        self.__enter__()

    def __enter__(self):
        for directory in needed_directories:
            if not os.path.exists("{}/{}".format(self.src_dir, directory)):
                os.mkdir("{}/{}".format(self.src_dir, directory))
        return self

    def __exit__(self, *args):
        for directory in needed_directories:
            rmtree("{}/{}".format(self.src_dir, directory))

    def get_username(self):
        return self.username

    def set_username(self, username):
        self.username = username

    def get_password(self):
        return self.password

    def set_password(self, password):
        self.password = password

    def _filtering_step(self, basename):
        """
        Moves the audio file if the format is `wav` to `filtered` directory.
        Parameters
        ----------
        basename    str
                    A basename of `/home/random-guy/some-audio-file.wav` is
                    `some-audio-file.wav`
        """
        name = ''.join(basename.split('.')[:-1])
        # May cause problems if wav is not less than 9 channels.
        if basename.split('.')[-1] == "wav":
            if self.verbose:
                print("Copying to {}/filtered".format(name, self.src_dir))
            subprocess.Popen(["cp", "{}/{}.wav".format(self.src_dir, name),
                              "{}/filtered/{}.wav".format(self.src_dir, name)],
                             universal_newlines=True).communicate()

    def _staging_step(self, basename):
        """
        Checks the size of audio file, splits it if it's needed to manage api
        limit and then moves to `staged` directory while appending \d{3} to
        the end of the filename.
        Parameters
        ----------
        basename    str
                    A basename of `/home/random-guy/some-audio-file.wav` is
                    `some-audio-file.wav`
        """
        name = ''.join(basename.split('.')[:-1])
        # Checks the file size. It's better to use 95% of the allocated size
        # per file since the upper limit is not always respected.
        total_size = os.path.getsize("{}/filtered/{}.wav".format(
            self.src_dir, name))
        if total_size >= self.__api_limit_bytes:
            if self.verbose:
                print("{}'s size exceeds API limit ({}). Splitting...".format(
                    name, self.__api_limit_bytes))
            self.split_audio_by_size(
                "{}/filtered/{}.wav".format(self.src_dir, name),
                "{}/staged/{}%03.wav".format(self.src_dir, name),
                self.__api_limit_bytes * 95 / 100)
        else:
            if self.verbose:
                print("{}'s size is fine. Moving to staging...'".format(name))
            subprocess.Popen(("mv {}/filtered/{}.wav " +
                             "{}/staging/{}000.wav").format(
                                 self.src_dir, name, self.src_dir, name),
                             shell=True, universal_newlines=True).communicate()

    def _prepare_audio(self, basename):
        """
        prepares and stages the audio file to be indexed.

        Parameters
        ----------
        basename    str
                    A basename of `/home/random-guy/some-audio-file.wav` is
                    `some-audio-file.wav`
        """
        self._filtering_step(basename)
        self._staging_step(basename)

    def list_audio_files(self, sub_dir=""):
        """
        Parameters
        ----------
        sub_dir         one of `needed_directories`

        Returns
        -------
        audio_files     [str]
                        A list whose elements are basenames of the present
                        audiofiles whose formats are `wav`
        """
        audio_files = list()
        for possibly_audio_file in os.listdir("{}/{}".format(self.src_dir,
                                                             sub_dir)):
            file_format = ''.join(possibly_audio_file.split('.')[-1])
            if file_format.lower() == "wav":
                audio_files.append(possibly_audio_file)
        return audio_files

    def get_audio_channels(self, abs_path_audio):
        """
        Parameters
        ----------
        abs_path_audio      str

        Returns
        -------
        channel_num         int
        """
        channel_num = int(
            subprocess.check_output(
                ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}'"""
                 ).format(abs_path_audio, "Channels"),
                shell=True, universal_newlines=True).rstrip()
        )
        return channel_num

    def get_audio_sample_rate(self, abs_path_audio):
        """
        Parameters
        ----------
        abs_path_audio      str

        Returns
        -------
        sample_rate         int
        """
        sample_rate = int(
           subprocess.check_output(
               ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}'"""
                ).format(abs_path_audio, "Sample Rate"),
               shell=True, universal_newlines=True).rstrip()
        )
        return sample_rate

    def get_audio_sample_bit(self, abs_path_audio):
        """
        Parameters
        ----------
        audio_abs_path      str

        Returns
        -------
        sample_bit          int
        """
        sample_bit = int(
           subprocess.check_output(
               ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}' | """ +
                """grep -oh "^[^-]*" """).format(abs_path_audio, "Precision"),
               shell=True, universal_newlines=True).rstrip()
        )
        return sample_bit

    def get_audio_duration_seconds(self, abs_path_audio):
        """
        Parameters
        ----------
        abs_path_audio      str

        Returns
        -------
        total_seconds       int
        """
        HHMMSS_duration = subprocess.check_output(
            ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}' | """ +
             """grep -oh "^[^=]*" """).format(
                abs_path_audio, "Duration"),
            shell=True, universal_newlines=True).rstrip()
        total_seconds = sum(
            [float(x) * 60 ** (2 - i)
             for i, x in enumerate(HHMMSS_duration.split(":"))]
        )
        return total_seconds

    def get_audio_bit_rate(self, abs_path_audio):
        """
        Parameters
        -----------
        abs_path_audio      str

        Returns
        -------
        bit_rate            int
        """
        bit_Rate_formatted = subprocess.check_output(
            """sox --i {} | grep "{}" | awk -F " : " '{{print $2}}'""".format(
                abs_path_audio, "Bit Rate"),
            shell=True, universal_newlines=True).rstrip()
        bit_rate = (
           lambda x:
           int(x[:-1]) * 10 ** 3 if x[-1].lower() == "k" else
           int(x[:-1]) * 10 ** 6 if x[-1].lower() == "m" else
           int(x[:-1]) * 10 ** 9 if x[-1].lower() == "g" else
           int(x)
        )(bit_Rate_formatted)
        return bit_rate

    def split_audio_by_duration(self, audio_abs_path,
                                results_abs_path, duration_seconds):
        """
        Parameters
        ----------
        audio_abs_path      str
        results_abs_path    str
                            A place for adding digits needs to be added prior
                            the the format decleration i.e. name%03.wav
        duration_seconds    int
        """
        subprocess.Popen(
            "{} -i {} -c copy -map 0 -segment_time {} -f segment {}".format(
                self.__ffmpeg, audio_abs_path, duration_seconds,
                results_abs_path),
            shell=True, universal_newlines=True).communicate()

    def split_audio_by_size(self, audio_abs_path, results_abs_path,
                            chunk_size):
        """
        Calculates the duration of the name.wav in order for all splits have
        the size of chunk_size except possibly the last split (which will be
        smaller) and then passes the duration to `split_audio_by_duration`

        Parameters
        ----------
        audio_abs_path      str
        results_abs_path    str
                            A place for adding digits needs to be added prior
                            the the format decleration i.e. name%03.wav
        chunk_size          int
                            Should be in bytes
        """
        sample_rate = self.get_audio_sample_rate(audio_abs_path)
        sample_bit = self.get_audio_sample_bit(audio_abs_path)
        channel_num = self.get_audio_channels(audio_abs_path)
        duration = 8 * chunk_size / reduce(lambda x, y: int(x) * int(y),
                                           [sample_rate, sample_bit,
                                            channel_num])
        self.split_audio_by_duration(audio_abs_path, results_abs_path,
                                     duration)

    def index_audio(self, name=None, continuous=True,
                    model="en-US_BroadbandModel", word_confidence=True,
                    word_alternatives_threshold=0.9, keywords=None,
                    keywords_threshold=None,
                    profanity_filter_for_US_results=False):
        """
        Implements a search-suitable interface for Watson speech API.

        For more information visit:
            https://www.ibm.com/watson/developercloud/speech-to-text/api/v1/
        The explainations of the Parameters of this method (except for `name`)
        has been taken from the API reference above, as well.

        Parameters
        ----------
        name        str
                    A specific filename to be indexed and is placed in src_dir
                    The name of `audio.wav` would be `audio`
        continuous  Bool
                    Indicates whether multiple final results that represent
                    consecutive phrases separated by long pauses are returned.
                    If true, such phrases are returned; if false (the default),
                    recognition ends after the first end-of-speech (EOS)
                    incident is detected.
        model       str
                    The identifier of the model to be used for the recognition
                    request:
                        ar-AR_BroadbandModel
                        en-UK_BroadbandModel
                        en-UK_NarrowbandModel
                        en-US_BroadbandModel (the default)
                        en-US_NarrowbandModel
                        es-ES_BroadbandModel
                        es-ES_NarrowbandModel
                        fr-FR_BroadbandModel
                        ja-JP_BroadbandModel
                        ja-JP_NarrowbandModel
                        pt-BR_BroadbandModel
                        pt-BR_NarrowbandModel
                        zh-CN_BroadbandModel
                        zh-CN_NarrowbandModel
        word_confidence     str
                            Indicates whether a confidence measure in the range
                            of 0 to 1 is returned for each word.
                            The default is True. (It's False in the original)
        word_alternatives_threshold     numeric
                                        A confidence value that is the lower
                                        bound for identifying a hypothesis as a
                                        possible word alternative (also known
                                        as "Confusion Networks"). An
                                        alternative word is considered if its
                                        confidence is greater than or equal to
                                        the threshold. Specify a probability
                                        between 0 and 1 inclusive. No
                                        alternative words are computed if you
                                        omit the parameter or specify the
                                        default value (null).
        keywords    [str]
                    A list of keywords to spot in the audio. Each keyword
                    string can include one or more tokens. Keywords are
                    spotted only in the final hypothesis, not in interim
                    results. Omit the parameter or specify an empty array if
                    you do not need to spot keywords.
        keywords_threshold      numeric
                                A confidence value that is the lower bound for
                                spotting a keyword. A word is considered to
                                match a keyword if its confidence is greater
                                than or equal to the threshold. Specify a
                                probability between 0 and 1 inclusive. No
                                keyword spotting is performed if you omit the
                                parameter or specify the default value (null).
                                If you specify a threshold, you must also
                                specify one or more keywords.
        profanity_filter_for_US_results     bool
                                            Indicates whether profanity
                                            filtering is performed on the
                                            transcript. If true (the default),
                                            the service filters profanity from
                                            all output except for keyword
                                            results by replacing inappropriate
                                            words with a series of asterisks.
                                            If false, the service returns
                                            results with no censoring. Applies
                                            to US English transcription only.
        """
        params = {'continuous': continuous,
                  'model': model,
                  'word_alternatives_threshold': word_alternatives_threshold,
                  'word_confidence': word_confidence,
                  'timestamps': True,
                  'profanity_filter': profanity_filter_for_US_results}
        if keywords is not None:
            params['keywords'] = keywords
        if keywords_threshold is not None:
            params['keywords_threshold'] = keywords_threshold

        for audio_basename in self.list_audio_files(only_wav=False):
            audio_name = ''.join(audio_basename.split('.')[:-1])
            if name is not None and audio_name != name:
                continue
            self._prepare_audio(audio_basename)
            if name is not None and audio_name == name:
                break
        for staging_audio_name in self.list_audio_files(sub_dir="staging"):
            original_audio_name = ''.join(
                staging_audio_name.split('.')[:-1]
            )[:-3]
            if name is not None and original_audio_name != name:
                continue
            with open(
                "{}/staging/{}".format(
                    self.src_dir, staging_audio_name), "rb") as f:
                if self.verbose:
                    print("Reading {}...".format(staging_audio_name))
                response = requests.post(
                    url=("https://stream.watsonplatform.net/" +
                         "speech-to-text/api/v1/recognize"),
                    auth=(self.get_username(), self.get_password()),
                    headers={'content-type': 'audio/wav'},
                    data=f.read(),
                    params=params)
                if self.verbose:
                    print("Indexing {}...".format(original_audio_name))
                self.__timestamps[original_audio_name + ".wav"].append(
                    self._timestamp_extractor(json.loads(response.text))
                )
                if name is not None and original_audio_name == name:
                    break

    def _timestamp_extractor(self, audio_json):
        """
        Parameters
        ----------
        audio_json      {str: [{str: [{str: str or nuneric}]}]}
                        (refer to Watson Speech API refrence)
        Returns
        -------
        -               [[str, float, float]]
                        A list whose members are lists. Each member list has
                        three elements. First one is a word. Second is the
                        starting second and the third is the ending second of
                        that word in the original audio file.
        """
        try:
            timestamps_of_sentences = [
                audio_json['results'][i]['alternatives'][0]['timestamps']
                for i in range(len(audio_json['results']))
            ]
            return [
                [word[0], float(word[1]), float(word[2])]
                for sentence_block in timestamps_of_sentences
                for word in sentence_block
            ]
        except KeyError:
            print(audio_json)
            print("The resulting request from Watson was unintelligible.")

    def get_timestamped_audio(self):
        """
        Returns a dictionary whose keys are audio file basenames and whose
        values are a list of word blocks (a word block is a list which has
        three elements, first one is a word <str>, second one is the starting
        second <float> and the third on is the ending second <float>).
        In case the audio file was large enough to be splitted, it adds seconds
        to correct timing and in case the timestamp was manually loaded, it
        leaves it alone.

        Note that even if no operation is done on the word blocks, the output
        of this method would be different than that of self.__timestamps.
        The timestamps attribute is a dictionary whose keys are basenames but
        whose values are lists corresponding to different blocks of 100Mbs or
        less splitted audio files and each list is then composed of lists of
        word blocks. So the signature of self.__timestamps would be
        {str: [[[str, floatm float]]]} which one dimension more than the output
        of this method - since here we don't differentiate between different
        splits of an audio file and we put the result of all splits in a single
        list.

        Returns
        -------
        unified_timestamp   {str: [[str, float, float]]}
        """
        staged_files = self.list_audio_files(sub_dir="staging")
        unified_timestamps = dict()
        for timestamp_basename in self.__timestamps:
            timestamp_name = ''.join(timestamp_basename.split('.')[0])
            if type(self.__timestamps[timestamp_basename][0][0]) is list:
                staged_splitted_file_basenames = list(
                    filter(
                        lambda x: timestamp_name in x, staged_files
                    )
                )
                staged_splitted_file_basenames.sort()
                unified_timestamp = list()
                seconds_passed = 0
                for split_index, splitted_file_timestamp in enumerate(
                  self.__timestamps[timestamp_basename]):
                    total_seconds = self.get_audio_duration_seconds(
                        "{}/staging/{}".format(
                            self.src_dir,
                            staged_splitted_file_basenames[split_index]
                        )
                    )
                    unified_timestamp += map(
                        lambda word: [word[0],
                                      word[1] + seconds_passed,
                                      word[2] + seconds_passed],
                        splitted_file_timestamp
                    )
                    seconds_passed += total_seconds
                unified_timestamps[str(timestamp_basename)] = unified_timestamp
            else:
                unified_timestamps[timestamp_basename] = self.__timestamps[
                    timestamp_basename]
        return unified_timestamps

    def save_indexed_audio(self, indexed_audio_file_abs_path):
        with open(indexed_audio_file_abs_path, "wb") as f:
            f.write(str(self.get_timestamped_audio()))

    def load_indexed_audio(self, indexed_audio_file_abs_path):
        with open(indexed_audio_file_abs_path, "rb") as f:
            self.__timestamps = literal_eval(f.read())

    def _levenshtein_distance(s1, s2):
        """
        Minimum number of single char edits (i.e. substitution, insertion and
        deletion) on `s1` to make it equivalent to `s2`.

        Code is from: https://rosettacode.org/wiki/Levenshtein_distance#Python

        Parameters
        ----------
        s1            str
        s2            str

        Returns
        -------
        -             int
        """
        if len(s1) > len(s2):
            s1, s2 = s2, s1
        distances = range(len(s1) + 1)
        for index2, char2 in enumerate(s2):
            new_distances = [index2+1]
            for index1, char1 in enumerate(s1):
                if char1 == char2:
                    new_distances.append(distances[index1])
                else:
                    new_distances.append(1 + min((distances[index1],
                                                 distances[index1+1],
                                                 new_distances[-1])))
            distances = new_distances
        return distances[-1]

    def search(self, query, audio_basename=None, subsequence=False,
               timing_error=0.1, case_sensitive=True, anagram=False,
               maximum_single_char_edits_to_match=0,
               differing_letters_tolerance=0):
        """
        A generator that searches for the `query` within the audiofiles of the
        src_dir.

        Parameters
        ----------
        query          str
                        A string that'll be searched. It'll be splitted on
                        spaces and then each word gets sequentially searched
        audio_basename str
                        Search only within the given audio_basename
        subsequence     bool
                        `True` if it's not needed for the exact word be
                        detected and larger strings that contain the given one
                        are fine. Default is False.
        timing_error    float
                        Sometimes other words (almost always very small) would
                        be detected between the words of the `query`. This
                        parameter defines the timing difference/tolerance of
                        the search. By default it's 0.1, which means it'd be
                        acceptable if the next word of the `query` is found
                        before 0.1 seconds of the end of the previous word.

        Yields
        ------
        -               {"File Name": str,
                         "Query": `query`,
                         "Result": (float, float)}
                         The result of the search is returned as a tuple which
                         is the value of the "Result" key. The first element
                         of the tuple is the starting second of `query` and
                         the last element is the ending second of `query`
        """
        word_list = list(
            filter(
                lambda element: element is not None,
                ''.join(
                    filter(
                        lambda char: char in (ascii_letters + " "),
                        list(query))
                ).split(" ")
            )
        )
        timestamps = self.get_timestamped_audio()
        if not case_sensitive:
            word_list = [x.lower() for x in word_list]
            timestamps = {
                key: [
                    [word_block[0].lower(), word_block[1], word_block[2]]
                    for word_block in timestamps[key]
                ] for key in timestamps
            }
        for audio_filename in (
                timestamps.keys() * (audio_basename is None) +
                [audio_basename] * (audio_basename is not None)):
            result = list()
            try:
                for word_block in timestamps[audio_filename]:
                    if (
                            # When the query is identical
                            (word_block[0] == word_list[len(result)]) or
                            # When the query is a subsequence of what's
                            # available
                            (subsequence and
                             bool(re.search(".*".join(word_list[len(result)]),
                                            word_block[0]))) or
                            # When query is a permutation of what's available.
                            (anagram and
                             sorted(word_block[0]) == sorted(
                                 word_list[len(result)])) or
                            # When some letters are different. (i.e. Hamming)
                            (len(word_block[0]) == len(
                                word_list[len(result)]) and
                             (sum(x != y for x, y in zip(
                                 word_block[0], word_list[len(result)])) <=
                              differing_letters_tolerance)) or
                            # When query can be editted to look like what's
                            # available. (i.e. Levenshtein)
                            (word_block[0] != word_list[len(result)] and
                             (0 <= maximum_single_char_edits_to_match <=
                             self._levenshtein_distance(
                                 word_list[len(result)], word_block[0])))
                    ):
                        result.append(tuple(word_block[1:]))
                        if len(result) == len(word_list):
                            yield {
                                "File Name": audio_filename,
                                "Query": query,
                                "Result": tuple([result[0][0],
                                                 result[-1][-1]])
                            }
                            result = list()
                    else:
                        try:
                            if (word_block[1] - result[-1][-1]) > timing_error:
                                result = list()
                        except IndexError:
                            continue
            except KeyError:
                pass

    def search_all(self, queries, audio_basename=None,
                   part_of_bigger_word=False, timing_error=0.1):
        """
        Returns a dictionary of all results of all of the queries for all of
        the audio files.

        Parameters
        ----------
        queries         [str]
                        A list of the strings that'll be searched. If type of
                        queries is `str`, it'll be insterted into a list within
                        the body of the method.
        audio_basename str
                        Search only within the given audio_basename
        part_of_bigger_word     bool
                                `True` if it's not needed for the exact word be
                                detected and larger strings that contain the
                                given one are fine. Default is False.
        timing_error    float
                        Sometimes other words (almost always very small) would
                        be detected between the words of the elements of
                        `queries`. This parameter defines the timing
                        difference/tolerance of the search. By default it's
                        0.1 which means it'd be acceptable if the next word of
                        an element of `queries` is found before 0.1 seconds of
                        the end of the previous word.

        Returns
        -------
        search_results  {str: {str: [(float, float)]}}
                        A dictionary whose keys are queries and whose values
                        are dictionaries whose keys are all the audiofiles in
                        which the query is present and whose values are a list
                        whose elements are 2-tuples whose first element is
                        the starting second of the query and whose values are
                        the ending second. e.g.
                        {"apple": {"fruits.wav" : [(1.1, 1.12)]}}

        Raises
        ------
        TypeError       if `queries` is neither a list nor a str
        """
        # When printing the output of search_results, normally the defaultdict
        # type would be shown as well. To print the `search_results` normally,
        # defining a PrettyDefaultDict type that is printable the same way as a
        # dict, is easier/faster than json.load(json.dump(x)) etc. and we don't
        # actually have to deal with encoding either.
        class PrettyDefaultDict(defaultdict):
            __repr__ = dict.__repr__

        if not isinstance(queries, (list, str)):
            raise TypeError("Invalid query type.")
        if type(queries) is not list:
            queries = [queries]
        search_results = PrettyDefaultDict(lambda: PrettyDefaultDict(list))
        for query in queries:
            search_gen = self.search(query, audio_basename,
                                     part_of_bigger_word, timing_error)
            for search_result in search_gen:
                search_results[query][
                    search_result["File Name"]].append(search_result["Result"])
        return search_results

    def seconds_to_HHMMSS(seconds):
        """
        Retuns a string which is the hour, minute, second(milli) representation
        of the intput `seconds`

        Parameters
        ----------
        seconds         float

        Returns
        -------
        -               str
                        Has the form <int>H<int>M<int>S.<float>
        """
        less_than_second = seconds - floor(seconds)
        minutes, seconds = divmod(floor(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return "{}H{}M{}S.{}".format(hours, minutes, seconds, less_than_second)
