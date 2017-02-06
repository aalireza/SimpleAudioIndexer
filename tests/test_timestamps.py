from SimpleAudioIndexer import SimpleAudioIndexer as sai
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


@pytest.fixture(params=["ibm", "cmu"])
def indexer(monkeypatch, request):
    monkeypatch.setattr(os.path, 'exists', lambda path: True)
    monkeypatch.setattr(os, 'mkdir', lambda path: None)
    if request.param == "ibm":
        indexer = sai(mode="ibm", username_ibm="username",
                      password_ibm="password", src_dir="src_dir")
    elif request.param == "cmu":
        indexer = sai(mode="cmu", src_dir="src_dir")
    staging_list = ["test000", "test001", "other000", "other001",
                    "another000", "another001"]
    monkeypatch.setitem(indexer.__dict__,
                        "_SimpleAudioIndexer__timestamps", timestamp)
    monkeypatch.setattr(indexer, '_list_audio_files', lambda sub_dir: (
        staging_list if sub_dir == "staging" else None))
    monkeypatch.setattr(indexer, '_get_audio_duration_seconds',
                        lambda staged_audio: audio_len[staged_audio])
    return indexer


def test_get_timestamped_audio(indexer):
    assert indexer.get_timestamped_audio() == expected_result
