from __future__ import print_function
import os
import sys
import subprocess
import warnings
import re

box_url = "ftp.box.com"
DEBUG_LEVEL = 0

#The Data Transfer Node uses an old version of Python where subprocess does not have the
#check_output function, therefore we need to revert to an older syntax in that case
modern_subproc = hasattr(subprocess,"check_output")

def shell_msg(msg):
    """
    Prints a message to the shell on stderr to ensure it doesn't get put into a shell variable
    :param msg: the message to print
    :return: nothing
    """
    print(msg, file=sys.stderr)

def remove_hidden_files(files):
    """
    Given a list of strings, removes any that represent hidden files/directories (start with ".")
    :param files: a list of files/directories as strings
    :return: nothing, files edited in place
    """
    hidden = []
    for f in files:
        if f.startswith("."):
            hidden.append(f)

    for h in hidden:
        files.remove(h)


def iter_dir_tree(top, nohidden=True, pattern=".*"):
    """
    A generator that iterates over the directories within top and yields each file one-by-one
    :param top: the directory to walk
    :param nohidden: whether to include hidden files; default = True
    :param pattern: a regular expression to be applied against file names (default = ".*"). Only matching files will be returned
    :return: iteration over all files within top.
    """
    for root, dirs, files in os.walk(top):
        if nohidden:
            remove_hidden_files(dirs)
            remove_hidden_files(files)
        for f in files:
            if re.match(pattern, f):
                yield os.path.join(root, f)

def are_remote_files_missing(localdir, remotedir, filepat=".*"):
    missing = _find_missing_remote_files_recursive(localdir, remotedir, filepat=filepat)
    if DEBUG_LEVEL > 0:
        if len(missing) > 0:
            print("Summary of files missing from remote:")
            for f in missing:
                print("  {0}".format(f))
        else:
            print("No files missing from remote")

    return len(missing) > 0

def _remove_path_head(path, head):
    """
    Given a path head, removes it and ensures that the path does not start with "/" unless head not removed
    :param path: the path to modify
    :param head: the head to remove, may or may not include trailing "/"
    :return: path with head removed
    """
    if path.startswith(head):
        path = path.replace(head, '')
        if path.startswith('/'):
            path = path[1:]

    return path


def _find_missing_remote_files_recursive(localdir, remotedir, filepat=".*"):
    # Get the listing of all files in the remote directory
    lftp_cmd = "find {0}; bye".format(remotedir)
    if modern_subproc:
        try:
            lsremote = subprocess.check_output(["lftp", "-e", lftp_cmd, box_url])
        except subprocess.CalledProcessError as err:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore") # CalledProcessError uses the deprecated message field
                raise RuntimeError("Problem with lftp command {0}: {1}".format(lftp_cmd, err.message))
    else:
        lproc = subprocess.Popen(["lftp", "-e", lftp_cmd, box_url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        lsremote, lsstderr = lproc.communicate()

    lsremote = lsremote.splitlines()
    # The way we do this we need to remove the top directory in the remote list
    for i in range(len(lsremote)):
        lsremote[i] = _remove_path_head(lsremote[i], remotedir)

    while '' in lsremote:
        lsremote.remove('')

    missing_files = []
    for flocal in iter_dir_tree(localdir, pattern=filepat):
        flocal = _remove_path_head(flocal, localdir)
        foundstr = "Found"
        if flocal not in lsremote:
            missing_files.append(flocal)
            foundstr = "MISSING"

        if DEBUG_LEVEL > 1:
            print("Checking for {0} on remote... {1}".format(flocal, foundstr))

    return missing_files

