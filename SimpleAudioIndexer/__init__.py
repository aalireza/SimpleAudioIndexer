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
from collections import defaultdict, Counter
from functools import reduce
from math import floor
from shutil import rmtree
from string import ascii_letters
import json
import os
import re
import requests
import subprocess


class SimpleAudioIndexer(object):
    """
    Should write overall process focusing on src_dir events


    Attributes
    ----------
    username :  str
        IBM Watson API username
    password :  str
        IBM Watson API password
    src_dir :  str
        Absolute path to the source directory of audio files such that the
        absolute path of the audio that'll be indexed would be
        `src_dir/audio_file.wav`
    verbose :  bool, optional
        `True` if progress needs to be printed. Default is False.
    api_limit_bytes :  int, optional
        It holds the API limitation of Watson speech api http sessionless
        which is 100Mbs. Default is 100000000.

    Methods
    -------
    get_username()
    set_username()
    get_password()
    set_password()
    index_audio(name=None, continuous=True, model="en-US_BroadbandModel",
                word_confidence=True, word_alternatives_threshold=0.9,
                keywords=None, keywords_threshold=None,
                profanity_filter_for_US_results=False)
        Implements a searching-suitable interface for the Watson API
    get_timestamped_audio()
        Returns a corrected dictionary whose key is the original file name and
        whose value is a list of words and their beginning and ending time. It
        accounts for large files and does the timing calculations to return the
        correct result.
    save_indexed_audio(indexed_audio_file_abs_path)
    load_indexed_audio(indexed_audio_file_abs_path)
    search_gen(query, audio_basename, case_sensitive, subsequence,
               supersequence, timing_error, anagram, missing_word_tolerance)
    search_all(queries, audio_basename, case_sensitive, subsequence,
               supersequence, timing_error, anagram, missing_word_tolerance)
        Returns a dictionary of all results of all of the queries for all of
        the audio files.
    """

    def __init__(self, username, password, src_dir, api_limit_bytes=100000000,
                 verbose=False, needed_directories={"filtered", "staging"}):
        """
        Parameters
        ----------
        username : str
        password : str
        src_dir : str
            Absolute path to the source directory of audio files such that the
            absolute path of the audio that'll be indexed would be
            `src_dir/audio_file.wav`
        api_limit_bytes : int, optional
            default is 100000000
        verbose : bool, optional
            default is False
        """
        self.username = username
        self.password = password
        self.verbose = verbose
        self.src_dir = src_dir
        self.api_limit_bytes = api_limit_bytes
        self.__timestamps = defaultdict(list)
        self._needed_directories = needed_directories
        # Because `needed_directories` are needed even if the initialization of
        # the object is not in a context manager for it to be created
        # automatically.
        self.__enter__()

    def __enter__(self):
        """
        Creates the needed directories for audio processing. It'll be called
        even if not in a context manager.
        """
        for directory in self._needed_directories:
            if not os.path.exists("{}/{}".format(self.src_dir, directory)):
                os.mkdir("{}/{}".format(self.src_dir, directory))
        return self

    def __exit__(self, *args):
        """
        Removes the works of __enter__. Will only be called if in a context
        manager.
        """
        for directory in self._needed_directories:
            rmtree("{}/{}".format(self.src_dir, directory))

    def get_username(self):
        return self.username

    def set_username(self, username):
        """
        Parameters
        ----------
        username : str
        """
        self.username = username

    def get_password(self):
        return self.password

    def set_password(self, password):
        """
        Parameters
        ----------
        password : str
        """
        self.password = password

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
            if self.verbose:
                print("Copying to {}/filtered".format(name, self.src_dir))
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
        # Checks the file size. It's better to use 95% of the allocated size
        # per file since the upper limit is not always respected.
        total_size = os.path.getsize("{}/filtered/{}.wav".format(
            self.src_dir, name))
        if total_size >= self.api_limit_bytes:
            if self.verbose:
                print("{}'s size exceeds API limit ({}). Splitting...".format(
                    name, self.api_limit_bytes))
            self.__split_audio_by_size(
                "{}/filtered/{}.wav".format(self.src_dir, name),
                "{}/staged/{}*.wav".format(self.src_dir, name),
                self.api_limit_bytes * 95 / 100)
        else:
            if self.verbose:
                print("{}'s size is fine. Moving to staging...'".format(name))
            subprocess.Popen(("mv {}/filtered/{}.wav " +
                             "{}/staging/{}000.wav").format(
                                 self.src_dir, name, self.src_dir, name),
                             shell=True, universal_newlines=True).communicate()

    def _prepare_audio(self, basename):
        """
        Prepares and stages the audio file to be indexed.

        Parameters
        ----------
        basename : str
            A basename of `/home/random-guy/some-audio-file.wav` is
            `some-audio-file.wav`
        """
        self._filtering_step(basename)
        self._staging_step(basename)

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
                shell=True, universal_newlines=True).rstrip()
        )
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
               shell=True, universal_newlines=True).rstrip()
        )
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
               ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}' | """ +
                """grep -oh "^[^-]*" """).format(audio_abs_path, "Precision"),
               shell=True, universal_newlines=True).rstrip()
        )
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
            ("""sox --i {} | grep "{}" | awk -F " : " '{{print $2}}' | """ +
             """grep -oh "^[^=]*" """).format(
                audio_abs_path, "Duration"),
            shell=True, universal_newlines=True).rstrip()
        total_seconds = sum(
            [float(x) * 60 ** (2 - i)
             for i, x in enumerate(HHMMSS_duration.split(":"))]
        )
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
        bit_rate = (
           lambda x:
           int(x[:-1]) * 10 ** 3 if x[-1].lower() == "k" else
           int(x[:-1]) * 10 ** 6 if x[-1].lower() == "m" else
           int(x[:-1]) * 10 ** 9 if x[-1].lower() == "g" else
           int(x)
        )(bit_Rate_formatted)
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
                                 starting_second, ending_second):
        """
        Parameters
        -----------
        audio_abs_path : str
        segment_abs_path : str
        starting_second : int
        ending_second : int
        """
        subprocess.Popen(["sox", str(audio_abs_path), str(segment_abs_path),
                          str(starting_second), str(ending_second)],
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
                starting_second=current_segment, ending_second=ending_second
            )

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

    def index_audio(self, name=None, continuous=True,
                    model="en-US_BroadbandModel", word_confidence=True,
                    word_alternatives_threshold=0.9, keywords=None,
                    keywords_threshold=None,
                    profanity_filter_for_US_results=False):
        """
        Implements a search-suitable interface for Watson speech API.

        Some explaination of the parameters here have been taken from [1]_

        Parameters
        ----------
        name : str, optional
            A specific filename to be indexed and is placed in src_dir
            The name of `audio.wav` would be `audio`.
            If `None` is selected, all the valid audio files would be indexed.
            Default is None.
        continuous : bool
            Indicates whether multiple final results that represent consecutive
            phrases separated by long pauses are returned.
            If true, such phrases are returned; if false (the default),
            recognition ends after the first end-of-speech (EOS) incident is
            detected.
            Default is True.
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
        keywords : [str], optional
            A list of keywords to spot in the audio. Each keyword string can
            include one or more tokens. Keywords are spotted only in the final
            hypothesis, not in interim results. Omit the parameter or specify
            an empty array if you do not need to spot keywords.
        keywords_threshold : numeric, optional
            A confidence value that is the lower bound for spotting a keyword.
            A word is considered to match a keyword if its confidence is
            greater than or equal to the threshold. Specify a probability
            between 0 and 1 inclusive. No keyword spotting is performed if you
            specify the default value `None`.
            If you specify a threshold, you must also specify one or more
            keywords.
        profanity_filter_for_US_results : bool
            Indicates whether profanity filtering is performed on the
            transcript. If true, the service filters profanity from all output
            except for keyword results by replacing inappropriate words with a
            series of asterisks.
            If false, the service returns results with no censoring. Applies
            to US English transcription only.
            Default is False.

        References
        ----------
        .. [1] : https://ibm.com/watson/developercloud/speech-to-text/api/v1/
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

        for audio_basename in self._list_audio_files():
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
        audio_json : {str: [{str: [{str: str or nuneric}]}]}
            refer to Watson Speech API refrence

        Returns
        -------
        [[str, float, float]]
        A list whose members are lists. Each member list has three elements.
        First one is a word. Second is the starting second and the third is the
        ending second of that word in the original audio file.
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
        unified_timestamp : {str: [[str, float, float]]}
        """
        staged_files = self._list_audio_files(sub_dir="staging")
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
        """
        Writes the corrected timestamps to a file. Timestamps are a python
        dictionary.

        Parameters
        ----------
        indexed_audio_file_abs_path : str
        """
        with open(indexed_audio_file_abs_path, "wb") as f:
            f.write(str(self.get_timestamped_audio()))

    def load_indexed_audio(self, indexed_audio_file_abs_path):
        """
        Parameters
        ----------
        indexed_audio_file_abs_path : str
        """
        with open(indexed_audio_file_abs_path, "rb") as f:
            self.__timestamps = literal_eval(f.read())

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
            Default is False
        subsequence : bool, optional
            Default is False
        supersequence : bool, optional
            Default is False

        Returns
        -------
        bool

        References
        ----------
        .. [1] : `https://stackoverflow.com/questions/35964155/checking-if-list-is-a-sublist`
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
            return (
                len(list_of_tups) > 0 and
                all([
                    Counter(sub)[tup[0]] <= Counter(sup)[tup[1]]
                    for tup in list_of_tups])
            )

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
        case_sensitive : bool, optional
            Default is False
        subsequence : bool, optional
            `True` if it's not needed for the exact word be detected and larger
            strings that contain the given one are fine.
            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.
            Default is False.
        supersequence : bool, optional
            `True` if it's not needed for the exact word be detected and
            smaller strings that are contained within the given one are fine.
            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.
            Default is False.
        anagram : bool, optional
            `True` if it's acceptable for a complete permutation of the word to
            be found. e.g. "abcde" would be acceptable for "edbac".
            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.
            Default is False.
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
        query_words = list(
            filter(
                lambda element: element is not None,
                ''.join(
                    filter(
                        lambda char: char in (ascii_letters + " "),
                        list(query))
                ).split(" ")
            )
        )
        assert abs(missing_word_tolerance -
                   (len(query_words) - 2)) >= 0, (
            "The number of words that can be missing must be less than " +
            "the total number of words within the query minus the first and " +
            "the last word."
        )
        timestamps = self.get_timestamped_audio()
        if not case_sensitive:
            query_words = [x.lower() for x in query_words]
            timestamps = {
                key: [
                    [word_block[0].lower(), word_block[1], word_block[2]]
                    for word_block in timestamps[key]
                ] for key in timestamps
            }

        for audio_filename in (
                (lambda: (timestamps.keys() if audio_basename is None else
                          [audio_basename]))()
        ):
            result = list()
            missed_words_so_far = 0
            query_cursor = 0
            try:
                # word_block's format: [str, float, float]
                for word_block in timestamps[audio_filename]:
                    if (
                            # When the query is identical
                            (word_block[0] == query_words[query_cursor]) or
                            # When the query is a subsequence of what's
                            # available
                            (subsequence and
                             self._is_subsequence_of(query_words[query_cursor],
                                                     word_block[0])) or
                            # When the query is a supersequence of what's
                            # available
                            (supersequence and self._is_supersequence_of(
                                query_words[query_cursor], word_block[0])) or
                            # When query is a permutation of what's available.
                            (anagram and self._is_anagram_of(
                                query_words[query_cursor], word_block[0]))
                    ):
                        result.append(tuple(word_block))

                        if timing_error is not None:
                            try:
                                if round(result[-1][-2] -
                                         result[-2][-1], 4) > timing_error:
                                    result = list()
                                    query_cursor = 0
                            except IndexError:
                                pass

                        if self._partial_search_validator(
                                query_words, [x[0] for x in result],
                                anagram=anagram,
                                subsequence=subsequence,
                                supersequence=supersequence
                        ):
                            yield {
                                "File Name": audio_filename,
                                "Query": query,
                                "Result": tuple([result[0][1],
                                                 result[-1][-1]])
                            }
                            result = list()
                            query_cursor = 0

                        else:
                            query_cursor += 1

                    elif missed_words_so_far > missing_word_tolerance:
                        result = list()
                        query_cursor = 0

                    elif (missing_word_tolerance > 0) and (len(result) > 0):
                        result.append(tuple(word_block))
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
        case_sensitive  bool
            Default is False
        subsequence : bool, optional
            `True` if it's not needed for the exact word be detected and larger
            strings that contain the given one are fine.
            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.
            Default is False.
        supersequence : bool, optional
            `True` if it's not needed for the exact word be detected and
            smaller strings that are contained within the given one are fine.
            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.
            Default is False.
        anagram : bool, optional
            `True` if it's acceptable for a complete permutation of the word to
            be found. e.g. "abcde" would be acceptable for "edbac".
            If the query is a sentences with multiple words, it'll be
            considered for each word, not the whole sentence.
            Default is False.
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
            "missing_word_tolerance": missing_word_tolerance
        }

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
            search_gen = self.search_gen(query=query,
                                         **search_gen_rest_of_kwargs)
            for search_result in search_gen:
                search_results[query][
                    search_result["File Name"]].append(search_result["Result"])
        return search_results
