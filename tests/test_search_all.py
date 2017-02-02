from SimpleAudioIndexer import SimpleAudioIndexer as sai
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


@pytest.fixture(autouse=True)
def indexer(monkeypatch):
    monkeypatch.setattr(os.path, 'basename', lambda path: "ffmpeg")
    monkeypatch.setattr(os.path, 'exists', lambda path: True)
    monkeypatch.setattr(os, 'mkdir', lambda path: None)
    indexer_obj = sai("username", "password", "src_dir")
    monkeypatch.setattr(indexer_obj, 'get_timestamped_audio',
                        lambda: timestamp)
    indexer_obj.__timestamps = timestamp
    return indexer_obj


def test_search_all(indexer):
    query = "in"
    assert indexer.search_all(query) == {
        "in": {
            "small_audio.wav": [(2.81, 2.93)],
            "test.wav": [(0.4, 0.5)]
        }
    }
