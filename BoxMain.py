from __future__ import print_function
import BoxUtils as utils
import argparse
import pdb

def get_args():
    parser = argparse.ArgumentParser(description="Determine whether Box has all the files it should")
    parser.add_argument("localdir", help="The local directory to be mirrored")
    parser.add_argument("remotedir", help="The remote directory that should equal the local one. Do not start with /")
    parser.add_argument("--pattern", default=None, help="A regular express to match against file names")
    parser.add_argument("--verbose","-v", action="count", help="Increase verbosity; will print missing files or indicate what files are being checked ")

    return parser.parse_args()

def main():
    args = get_args()
    localdir = args.localdir
    remotedir = args.remotedir
    filepattern = args.pattern
    utils.DEBUG_LEVEL = args.verbose

    if isinstance(filepattern, str):
        are_missing = utils.are_remote_files_missing(localdir, remotedir, filepat=filepattern)
    else:
        are_missing = utils.are_remote_files_missing(localdir, remotedir)

    if are_missing:
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    main()