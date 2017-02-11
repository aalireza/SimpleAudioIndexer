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


@pytest.mark.parametrize(("pattern"), [r'in', r'in ', r' in ', r' in'])
def test_search_regexp_1(indexer, pattern):
    if pattern in {r" in ", r"in "}:
        assert indexer.search_regexp(pattern) == {
            pattern: {
                "small_audio.wav": [(2.81, 2.93)],
            }
        }
    else:
        assert indexer.search_regexp(pattern) == {
            pattern: {
                "small_audio.wav": [(2.81, 2.93)],
                "test.wav": [(0.4, 0.5)]
            }
        }


@pytest.mark.parametrize(("pattern"), [
    r' [a-z][a-z][a-z] '
])
def test_search_regexp_2(indexer, pattern):
    assert indexer.search_regexp(pattern) == {
        " are ": {
            "small_audio.wav": [(1.07, 1.25)]
        },
        " our ": {
            "small_audio.wav": [(2.93, 3.09)]
        }
    }


@pytest.mark.parametrize(("pattern"), [
    r'[a-z][a-z][a-z]',
])
def test_search_regexp_3(indexer, pattern):
    expected_result = {
        "are": {
            "small_audio.wav": [(1.07, 1.25)]
        },
        "our": {
            "small_audio.wav": [(2.93, 3.09)]
        }
    }
    assert len(indexer.search_regexp(pattern)) > len(expected_result)
    assert set(expected_result.keys()).issubset(set(
        indexer.search_regexp(pattern).keys()))


@pytest.mark.parametrize(("audio_basename"), [
    None, "small_audio.wav", "test.wav"
])
@pytest.mark.parametrize(("pattern"), [
    r' [a-z][a-z] [a-z][a-z][a-z] ',
])
def test_search_regexp_4(indexer, pattern, audio_basename):
    if audio_basename == "test.wav":
        expected_result = {}
    else:
        expected_result = {
            " in our ": {
                "small_audio.wav": [(2.81, 3.09)]
            },
        }
    assert indexer.search_regexp(pattern, audio_basename) == expected_result


@pytest.mark.parametrize(("audio_basename"), [
    None, "small_audio.wav", "test.wav"
])
@pytest.mark.parametrize(("pattern"), [
    r'[a-z][a-z] [a-z][a-z][a-z]'
])
def test_search_regexp_5(indexer, pattern, audio_basename):
    if audio_basename == "test.wav":
        expected_result = {}
    else:
        expected_result = {
            "in our": {
                "small_audio.wav": [(2.81, 3.09)]
            },
        }
    assert len(indexer.search_regexp(pattern,
                                     audio_basename)) > len(expected_result)
    assert set(expected_result.keys()).issubset(set(
        indexer.search_regexp(pattern).keys()))
