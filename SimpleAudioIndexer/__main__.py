from pprint import pprint
import argparse
import os
import sys

sys.path.append(os.path.dirname(__file__))

from SimpleAudioIndexer import SimpleAudioIndexer


def argument_handler():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="IBM Watson API Username",
                        type=str, required=True)
    parser.add_argument("-p", "--password", help="IBM Watson API Password",
                        type=str, required=True)
    parser.add_argument("-d", "--src_dir",
                        help="Absolute path to ource directory for audio files",
                        type=str, required=True)
    parser.add_argument("-s", "--search",
                        help="Search for a word within the audios of src_dir",
                        type=str, required=True)
    parser.add_argument("-t", "--show_timestamps",
                        help="prints a timestamp of the audio",
                        action='store_true')
    parser.add_argument("-m", "--model", type=str,
                        help=("Model that'd be used for Watson, default is" +
                              " en-US_BroadbandModel"),
                        default="en-US_BroadbandModel")
    parser.add_argument("-v", "--verbose", help="print stage of the program",
                        action='store_true')
    args = parser.parse_args()
    return (args.username, args.password, args.src_dir, args.search,
            args.show_timestamps, args.model, args.verbose)


(username, password, src_dir, word, show_timestamps, model,
    verbose) = argument_handler()
indexer = SimpleAudioIndexer(username, password, src_dir, verbose=verbose)
indexer.index_audio(model=model)
if show_timestamps:
    pprint(indexer.get_timestamped_audio())
pprint(indexer.search_all(word))
