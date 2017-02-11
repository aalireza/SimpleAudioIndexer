from SimpleAudioIndexer import SimpleAudioIndexer as sai
from SimpleAudioIndexer import _WordBlock as WordBlock
import os
import pytest

timestamp = {
    'small_audio.wav': [['Americans', 0.21, 1.07],
                        ['are', 1.07, 1.25],
                        ['called', 1.25, 1.71],
                        ['to', 1.71, 1.81],
                        ['enact', 1.81, 2.17],
                        ['this', 2.17, 2.33],
                        ['promise', 2.33, 2.81],
                        ['in', 2.81, 2.93],
                        ['our', 2.93, 3.09],
                        ['lives', 3.09, 3.89]],
    'test.wav': [['This', 0.01, 0.05],
                 ['is', 0.05, 0.08],
                 ['some', 0.1, 0.2],
                 ['garbage', 0.21, 0.26],
                 ['This', 0.3, 0.4],
                 ['in', 0.4, 0.5]]
}

timestamp = {basename: list(map(
    lambda word_block: (WordBlock(word=word_block[0],
                                  start=word_block[1],
                                  end=word_block[2])), timestamp[basename]))
             for basename in timestamp}


@pytest.fixture(autouse=True)
def indexer(monkeypatch):
    monkeypatch.setattr(os.path, 'exists', lambda path: True)
    monkeypatch.setattr(os, 'mkdir', lambda path: None)
    indexer_obj = sai(mode="ibm", src_dir="src_dir",
                      username_ibm="username", password_ibm="password")
    monkeypatch.setattr(indexer_obj, 'get_timestamps',
                        lambda: timestamp)
    indexer_obj.__timestamps = timestamp
    return indexer_obj


def result_template(query, filename, result):
    if result == []:
        return []
    if filename is not None and filename not in timestamp.keys():
        return []
    return {'Query': str(query),
            'File Name': filename,
            'Result': tuple(result)}


@pytest.mark.parametrize(("missing_word_tolerance"), [0, 1, 2])
@pytest.mark.parametrize(("anagram"), [False, True])
@pytest.mark.parametrize(("supersequence"), [False, True])
@pytest.mark.parametrize(("subsequence"), [False, True])
@pytest.mark.parametrize(("audio_basename"), [
    None, "specified"
])
@pytest.mark.parametrize(("query", "case_sensitive",
                          "filename_for_result", "result"), [
    ("are", True, "small_audio.wav", [1.07, 1.25]),
    ("are called to", True, "small_audio.wav", [1.07, 1.81]),
    ("some", True, "test.wav", [0.1, 0.2]),
    ("This is", True, "test.wav", [0.01, 0.08]),
    ("test", True, "test.wav", []),
    ("this", True, "small_audio.wav", [2.17, 2.33]),
    ("This", True, "test.wav", [0.01, 0.05]),
    ("this", False, "test.wav", [0.01, 0.05])
])
def test_search_gen(indexer, query, case_sensitive, filename_for_result,
                    result, subsequence, supersequence, audio_basename,
                    anagram, missing_word_tolerance):
    if audio_basename == "specified":
        audio_basename = filename_for_result
    actual_kwargs = {
        "query": query,
        "case_sensitive": case_sensitive,
        "audio_basename": audio_basename,
        "anagram": anagram,
        "subsequence": subsequence,
        "supersequence": supersequence,
        "missing_word_tolerance": missing_word_tolerance,
        }
    expected_results = result_template(query, filename_for_result, result)
    if abs(missing_word_tolerance - (len(query.split(" ")) - 2)) < 0:
        with pytest.raises(AssertionError) as e:
            actual_results = list(indexer.search_gen(**actual_kwargs))
            assert str(e.value) == (
                "The number of words that can be missing must be less than " +
                "the total number of words within the query"
                )
    else:
        actual_results = list(indexer.search_gen(**actual_kwargs))
        assert ((expected_results == actual_results) or
                (expected_results in actual_results))


@pytest.mark.parametrize(("audio_basename"), [
    None, "specified"
])
@pytest.mark.parametrize(("query", "case_sensitive",
                          "filename_for_result", "result"), [
    ("are", True, "small_audio.wav", [1.07, 1.25]),
    ("ae", True, "small_audio.wav", [1.07, 1.25]),
    ("ar", True, "small_audio.wav", [1.07, 1.25]),
    ("ae caled t", True, "small_audio.wav", [1.07, 1.81]),
    ("are", False, "test.wav", [0.21, 0.26]),
    ("This", True, "test.wav", [0.01, 0.05]),
    ("tis", False, "test.wav", [0.01, 0.05])
])
def test_search_gen_subsequence_extra(indexer, query, case_sensitive,
                                      audio_basename, filename_for_result,
                                      result):
    if audio_basename == "specified":
        audio_basename = filename_for_result
    expected_results = result_template(query, filename_for_result, result)
    actual_results = list(
        indexer.search_gen(query, audio_basename=audio_basename,
                           case_sensitive=case_sensitive,
                           subsequence=True))
    assert ((expected_results == actual_results) or
            (expected_results in actual_results))


@pytest.mark.parametrize(("audio_basename"), [
    None, "specified"
])
@pytest.mark.parametrize(("query", "case_sensitive",
                          "filename_for_result", "result"), [
    ("arree", True, "small_audio.wav", [1.07, 1.25]),
    ("are", True, "small_audio.wav", [1.07, 1.25]),
    ("are called too", True, "small_audio.wav", [1.07, 1.81]),
    ("This", True, "test.wav", [0.01, 0.05]),
    ("tHissss", False, "test.wav", [0.01, 0.05])
])
def test_search_gen_supersequence_extra(indexer, query, case_sensitive,
                                        audio_basename, filename_for_result,
                                        result):
    if audio_basename == "specified":
        audio_basename = filename_for_result
    expected_results = result_template(query, filename_for_result, result)
    actual_results = list(
        indexer.search_gen(query, audio_basename=audio_basename,
                           case_sensitive=case_sensitive,
                           supersequence=True))
    assert ((expected_results == actual_results) or
            (expected_results in actual_results))


@pytest.mark.parametrize(("audio_basename"), [
    None, "specified"
])
@pytest.mark.parametrize(("query", "case_sensitive",
                          "filename_for_result", "result"), [
    ("era", True, "small_audio.wav", [1.07, 1.25]),
    ("are", True, "small_audio.wav", [1.07, 1.25]),
    ("are lcalde ot", True, "small_audio.wav", [1.07, 1.81]),
    ("This", True, "test.wav", [0.01, 0.05]),
    ("Htis", False, "test.wav", [0.01, 0.05])
])
def test_search_gen_anagram_extra(indexer, query, case_sensitive,
                                  audio_basename, filename_for_result,
                                  result):
    if audio_basename == "specified":
        audio_basename = filename_for_result
    expected_results = result_template(query, filename_for_result, result)
    actual_results = list(
        indexer.search_gen(query, audio_basename=audio_basename,
                           case_sensitive=case_sensitive,
                           anagram=True))
    assert ((expected_results == actual_results) or
            (expected_results in actual_results))


@pytest.mark.parametrize(("audio_basename"), [
    None, "specified"
])
@pytest.mark.parametrize(("query", "case_sensitive", "timing_error",
                          "filename_for_result", "result"), [
    ("This is some", True, 0.02, "test.wav", [0.01, 0.2]),
    ("This is some", True, 0.03, "test.wav", [0.01, 0.2]),
    ("This is some", True, 0.01, "test.wav", []),
    ("in our lives", False, 0.0, "small_audio.wav", [2.81, 3.89])
])
def test_search_gen_timing_error(indexer, query, case_sensitive, timing_error,
                                 audio_basename, filename_for_result,
                                 result):
    if audio_basename == "specified":
        audio_basename = filename_for_result
    expected_results = result_template(query, filename_for_result, result)
    actual_results = list(
        indexer.search_gen(query, audio_basename=audio_basename,
                           case_sensitive=case_sensitive,
                           timing_error=timing_error))
    assert ((expected_results == actual_results) or
            (expected_results
             in actual_results))


@pytest.mark.parametrize(("audio_basename"), [
    None, "specified"
])
@pytest.mark.parametrize(("query", "case_sensitive", "missing_word_tolerance",
                          "filename_for_result", "result"), [
    ("This is some garbage", True, 0, "test.wav", [0.01, 0.26]),
    ("This is some garbage", True, 1, "test.wav", [0.01, 0.26]),
    ("This is some garbage", True, 2, "test.wav", [0.01, 0.26]),
    ("This some garbage", True, 1, "test.wav", [0.01, 0.26]),
    ("This is some", True, 0, "test.wav", [0.01, 0.2]),
    ("This is some", True, 1, "test.wav", [0.01, 0.2]),
    ("This garbage", True, 2, "test.wav", [0.01, 0.26]),
])
def test_search_gen_missing_word_tolerance(
        indexer, query, case_sensitive, missing_word_tolerance, audio_basename,
        filename_for_result, result):
    if audio_basename == "specified":
        audio_basename = filename_for_result
    actual_kwargs = {
        "query": query,
        "audio_basename": audio_basename,
        "case_sensitive": case_sensitive,
        "missing_word_tolerance": missing_word_tolerance,
        "timing_error": None
    }
    expected_results = result_template(query, filename_for_result, result)
    if abs(missing_word_tolerance - (len(query.split(" ")) - 2)) < 0:
        with pytest.raises(AssertionError) as e:
            actual_results = list(indexer.search_gen(**actual_kwargs))
            assert str(e.value) == (
                "The number of words that can be missing must be less than " +
                "the total number of words within the query"
                )
    else:
        actual_results = list(indexer.search_gen(**actual_kwargs))
        assert ((expected_results == actual_results) or
                (expected_results
                in actual_results))


def test_search_gen_mix_1(indexer):
    actual_kwargs = {
        "query": "american calleddd entca",
        "case_sensitive": False,
        "missing_word_tolerance": 2,
        "anagram": True,
        "subsequence": True,
        "supersequence": True}
    expected_results = result_template(actual_kwargs["query"],
                                       "small_audio.wav", [0.21, 2.17])
    actual_results = list(indexer.search_gen(**actual_kwargs))
    assert ((expected_results == actual_results) or
            (expected_results in actual_results))
