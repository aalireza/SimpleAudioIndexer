from pprint import pprint
import argparse
import os
import sys


def argument_handler():
    parser = argparse.ArgumentParser()
    loadsave = parser.add_mutually_exclusive_group()
    search = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument("-u", "--username", help="IBM Watson API Username",
                        type=str)
    parser.add_argument("-p", "--password", help="IBM Watson API Password",
                        type=str)
    parser.add_argument("-d", "--src_dir", type=str,
                        help="Absolute path to location of audio files")
    search.add_argument("-s", "--search", type=str,
                        help="Search for a word within the audios of src_dir")
    search.add_argument("-r", "--regexp", type=str,
                        help="Match regex patterns")
    parser.add_argument("-t", "--show_timestamps", action='store_true',
                        help="prints a timestamp of the audio")
    parser.add_argument("-n", "--audio_name", type=str,
                        help=("Only index the given audio file (e.g. example" +
                              " in example.wav) that's in src_dir"))
    parser.add_argument("-m", "--model", type=str,
                        help=("Model that'd be used for Watson, default is" +
                              " en-US_BroadbandModel"),
                        default="en-US_BroadbandModel")
    parser.add_argument("-v", "--verbose", help="print stage of the program",
                        action='store_true')
    loadsave.add_argument("-f", "--save_data", type=str, help=(
        "abs path to the file which will contain the indexed data"))
    loadsave.add_argument("-l", "--load_data", type=str, help=(
        "abs path to the file which contains the indexed data"))
    args = parser.parse_args()
    assert (args.username and args.password and args.src_dir) or (
        args.load_data), (
        "Either enter your IBM credentials, or load indexed data"
    )
    if args.load_data:
        args.username = None
        args.password = None
        args.src_dir = None

    return (args.username, args.password, args.src_dir, args.search,
            args.regexp, args.show_timestamps, args.audio_name, args.model,
            args.verbose, args.save_data, args.load_data)


def Main():
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from SimpleAudioIndexer import SimpleAudioIndexer

    (username, password, src_dir, word, pattern, show_timestamps,
     audio_name, model, verbose, save_data, load_data) = argument_handler()

    def cli_script_wrapped(indexer):
        if not load_data:
            if audio_name is None:
                indexer.index_audio(model=model)
            else:
                indexer.index_audio(model=model, name=audio_name)
        if save_data:
            indexer.save_indexed_audio(save_data)
        if show_timestamps:
            pprint(indexer.get_timestamped_audio())
        if audio_name is not None:
            if word is not None:
                pprint(indexer.search_all(
                    word, audio_basename="{}.wav".format(audio_name)))
            else:
                pprint(indexer.search_regexp(
                    pattern, audio_basename="{}.wav".format(audio_name)))
        else:
            if word is not None:
                pprint(indexer.search_all(word))
            else:
                pprint(indexer.search_regexp(pattern))

    if load_data is not None:
        indexer = SimpleAudioIndexer(username, password, src_dir,
                                     verbose=verbose)
        indexer.load_indexed_audio(load_data)
        cli_script_wrapped(indexer)
    else:
        with SimpleAudioIndexer(username, password,
                                src_dir, verbose=verbose) as indexer:
            cli_script_wrapped(indexer)


if __name__ == '__main__':
    Main()
