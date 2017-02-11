from pprint import pprint
import argparse
import os
import sys


def argument_handler():
    parser = argparse.ArgumentParser()
    loadsave = parser.add_mutually_exclusive_group()
    search = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument("-d", "--src_dir", type=str,
                        help="Absolute path to location of audio files")
    parser.add_argument("-m", "--mode", help="The speech to text engine",
                        type=str, choices=["ibm", "cmu"], required=True)
    parser.add_argument("-u", "--username_ibm",
                        help="IBM Watson API Username", type=str)
    parser.add_argument("-p", "--password_ibm",
                        help="IBM Watson API Password", type=str)
    search.add_argument("-s", "--search", type=str,
                        help="Search for a word within the audios of src_dir")
    search.add_argument("-r", "--regexp", type=str,
                        help="Match regex patterns")
    parser.add_argument("-t", "--timestamps", action='store_true',
                        help="prints a timestamp of the audio")
    parser.add_argument("-n", "--audio_name", type=str,
                        help=("Only index the given audio file (e.g. example" +
                              " in example.wav) that's in src_dir"))
    parser.add_argument("-z", "--language", type=str,
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

    assert ((args.username_ibm and args.password_ibm and args.src_dir) or
            (args.load_data) or (args.mode == "cmu")), (
        "Either enter your IBM credentials, or load indexed data"
    )
    if args.load_data or args.mode == "cmu":
        args.username_ibm = None
        args.password_ibm = None
        if args.mode != "cmu":
            args.src_dir = None

    assert (
        (args.mode == "ibm") or
        ((args.mode == "cmu") and (args.language == "en-US_BroadbandModel"))
    ), ("You cannot choose an IBM language model if the chosen mode is `cmu`")

    return (args.src_dir, args.mode, args.username_ibm, args.password_ibm,
            args.search, args.regexp, args.timestamps, args.audio_name,
            args.language, args.verbose, args.save_data, args.load_data)


def Main():
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from SimpleAudioIndexer import SimpleAudioIndexer

    (src_dir, mode, username_ibm, password_ibm, word, pattern, timestamps,
     audio_name, language, verbose, save_data, load_data) = argument_handler()

    def cli_script_wrapped(indexer):
        if not load_data:
            if audio_name is None:
                if mode == "ibm":
                    indexer.index_audio(model=language)
                else:
                    indexer.index_audio()
            elif mode == "ibm":
                indexer.index_audio(model=language, basename=audio_name)
            else:
                indexer.index_audio(basename=audio_name)
        if save_data:
            indexer.save_indexed_audio(save_data)
        if timestamps:
            pprint(indexer.get_timestamps())
        if audio_name is not None:
            if word is not None:
                pprint(indexer.search_all(
                    word, audio_basename=audio_name))
            else:
                pprint(indexer.search_regexp(
                    pattern, audio_basename=audio_name))
        else:
            if word is not None:
                pprint(indexer.search_all(word))
            else:
                pprint(indexer.search_regexp(pattern))

    with SimpleAudioIndexer(src_dir=src_dir, mode=mode,
                            username_ibm=username_ibm,
                            password_ibm=password_ibm,
                            verbose=verbose) as indexer:
        if load_data is not None:
            indexer.load_indexed_audio(load_data)
        cli_script_wrapped(indexer)


if __name__ == '__main__':
    Main()
