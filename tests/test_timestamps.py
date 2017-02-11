from SimpleAudioIndexer import SimpleAudioIndexer as sai
from SimpleAudioIndexer import _WordBlock as WordBlock
import os
import pytest

timestamp = {
    'test.wav': [
        [['This', 0.01, 0.05],
         ['is', 0.05, 0.08],
         ['some', 0.1, 0.2],
         ['garbage', 0.21, 0.26],
         ['This', 0.3, 0.4],
         ['in', 0.4, 0.5]],
        [['some', 0.01, 0.04],
         ['other', 0.4, 0.5],
         ['test', 0.6, 0.62]]
    ],
    'other.wav': [
        [['other', 0.01, 0.05],
         ['thing', 0.6, 0.62]]
    ],
    'another.wav': [
        [['another', 0.2, 0.5]],
        [['another', 0.2, 0.5]]
    ]
}

audio_len = {
    "src_dir/staging/test000": 0.5,
    "src_dir/staging/test001": 0.62,
    "src_dir/staging/other000": 1,
    "src_dir/staging/another000": 0.51,
    "src_dir/staging/another001": 0.5
}

expected_result = {
    'test.wav': [
        ['This', 0.01, 0.05],
        ['is', 0.05, 0.08],
        ['some', 0.1, 0.2],
        ['garbage', 0.21, 0.26],
        ['This', 0.3, 0.4],
        ['in', 0.4, 0.5],
        ['some', 0.51, 0.54],
        ['other', 0.9, 1.0],
        ['test', 1.1, 1.12]
    ],
    'other.wav': [
        ['other', 0.01, 0.05],
        ['thing', 0.6, 0.62]
    ],
    'another.wav': [
        ['another', 0.2, 0.5],
        ['another', 0.71, 1.01]
    ]
}
timestamp = {basename: [
    list(map(
        lambda word_block: (WordBlock(word=word_block[0],
                                      start=word_block[1],
                                      end=word_block[2])), timestamp_split))
    for timestamp_split in timestamp[basename]]
             for basename in timestamp}

expected_result = {basename: list(map(
    lambda word_block: (WordBlock(word=word_block[0],
                                  start=word_block[1],
                                  end=word_block[2])),
    expected_result[basename]))
                    for basename in expected_result}


@pytest.fixture(autouse=True)
def indexer(monkeypatch):
    monkeypatch.setattr(os.path, 'exists', lambda path: True)
    monkeypatch.setattr(os, 'mkdir', lambda path: None)
    indexer_obj = sai(mode="ibm", src_dir="src_dir",
                      username_ibm="username", password_ibm="password")
    monkeypatch.setitem(indexer_obj.__dict__,
                        "_SimpleAudioIndexer__timestamps_unregulated",
                        timestamp)
    monkeypatch.setattr(indexer_obj, '_list_audio_files',
                        lambda sub_dir: (
                            ["test000", "test001",
                             "other000", "another000", "another001"]
                            if sub_dir == "staging" else None))
    monkeypatch.setattr(indexer_obj, '_get_audio_duration_seconds',
                        lambda staged_audio: audio_len[staged_audio])
    return indexer_obj


def test_get_timestamped_audio(indexer):
    indexer._timestamp_regulator()
    assert indexer.get_timestamps() == expected_result
