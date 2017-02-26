from __future__ import print_function
import os
import sys
import subprocess
import warnings

box_url = "ftp.box.com"

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


def iter_dir_tree(top, nohidden=True):
    for root, dirs, files in os.walk(top):
        if nohidden:
            remove_hidden_files(dirs)
            remove_hidden_files(files)
        for f in files:
            yield os.path.join(root, f)


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


def _find_missing_remote_files_recursive(localdir, remotedir):
    # Get the listing of all files in the remote directory
    lftp_cmd = "find {0}; bye".format(remotedir)
    try:
        lsremote = subprocess.check_output(["lftp", "-e", lftp_cmd, box_url])
    except subprocess.CalledProcessError as err:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore") # CalledProcessError uses the deprecated message field
            raise RuntimeError("Problem with lftp command {0}: {1}".format(lftp_cmd, err.message))

    lsremote = lsremote.splitlines()
    # The way we do this we need to remove the top directory in the remote list
    for i in range(len(lsremote)):
        lsremote[i] = _remove_path_head(lsremote[i], remotedir)

    while '' in lsremote:
        lsremote.remove('')

    missing_files = []
    for flocal in iter_dir_tree(localdir):
        flocal = _remove_path_head(flocal, localdir)
        if flocal not in lsremote:
            missing_files.append(flocal)

    return missing_files

