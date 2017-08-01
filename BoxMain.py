from __future__ import print_function
import BoxUtils as utils
import argparse
import pdb
import re

def get_args():
    parser = argparse.ArgumentParser(description="Determine whether Box has all the files it should")
    parser.add_argument("localdir", help="The local directory to be mirrored")
    parser.add_argument("remotedir", help="The remote directory that should equal the local one. Do not start with /")
    parser.add_argument("--verbose","-v", action="count", help="Increase verbosity; will print missing files or indicate what files are being checked ")
    parser.add_argument("-l", action="store_true", help="List missing files so that the shell receives the list.")

    filepatgrp = parser.add_mutually_exclusive_group()
    filepatgrp.add_argument("--pattern", default=None, help="A regular expression (using the Python re syntax) to match against file names")
    filepatgrp.add_argument("--glob", default=None, help="A shell glob to match against file names (only * and ? wildcards allowed)")

    return parser.parse_args()

def main():
    args = get_args()
    localdir = args.localdir
    remotedir = args.remotedir

    if args.glob:
        filepattern = args.glob
        if re.search("[^\w.\*\-?]", filepattern):
            utils.shell_error("A value for the --glob option must include only alphanumeric characters plus the following: - _ . * ?")

        # Transform the glob into its equivalent python regular expression
        filepattern = filepattern.replace(".", "\.")
        filepattern = filepattern.replace("*", ".*")
        filepattern = filepattern.replace("?", ".")

    else:
        filepattern = args.pattern

    if args.verbose > 0 and args.l:
        utils.shell_msg("Warning: verbosity > 0 and -l flag present; values printed may include more than file names")

    utils.DEBUG_LEVEL = args.verbose

    if isinstance(filepattern, str):
        are_missing = utils.are_remote_files_missing(localdir, remotedir, doprint=args.l, filepat=filepattern)
    else:
        are_missing = utils.are_remote_files_missing(localdir, remotedir, doprint=args.l)

    if are_missing:
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    main()