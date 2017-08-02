from __future__ import print_function
import copy
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

def shell_error(msg, exitcode=1):
    """
    Prints an error message to the shell.
    :param msg: The message to print
    :param exitcode: The exit status to use. Default is 1
    :return: nothing, exits program
    """
    print(msg, file=sys.stderr)
    exit(exitcode)

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

def are_remote_files_missing(localdir, remotedir, doprint=False, filepat=".*"):
    missing = find_missing_remote_files_recursive(localdir, remotedir, filepat=filepat)
    if DEBUG_LEVEL > 0:
        if len(missing) > 0:
            print("Summary of files missing from remote:")
            for f in missing:
                print("  {0}".format(f))
        else:
            print("No files missing from remote")

    if doprint:
        # Print the missing files as one line - intended for use with a bash's $() syntax (or equivalent) to store
        # missing files in a shell variable
        print(" ".join(missing))

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

def _make_remote_dir_if_needed(remotedir, verbosity=0):
    remote_dir_exists = subprocess.Popen(["lftp", "-e", "cd {0}; bye".format(remotedir), box_url], stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait() == 0

    if remote_dir_exists:
        if verbosity > 2:
            shell_msg("Remote directory {0} already exists, no need to create it".format(remotedir))
    else:
        if verbosity > 2:
            shell_msg("Creating remote directory {0}".format(remotedir))

        child = subprocess.Popen(["lftp", "-e", "mkdir -p {0}; bye".format(remotedir), box_url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if child.wait() != 0:
            raise RuntimeError("mkdir -p failed on remote: {0}".format(child.communicate()[1]))


def find_missing_remote_files_recursive(localdir, remotedir, filepat=".*"):
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

def mirror_local_to_remote(localdir, remotedir, max_num_files=None, number_attempts=10, verbosity=0):
    # Input checking
    if not os.path.isdir(localdir):
        raise ValueError('localdir must be a directory (not a file)')
    if max_num_files is not None and (max_num_files <= 0 or not isinstance(max_num_files, int)):
        raise ValueError('max_num_files must be a positive integer, if given')

    localdir = localdir.rstrip('/\\')
    remotedir = remotedir.strip('/')

    # Are we actually missing any files? We need to make the root remote directory before doing this operation
    _make_remote_dir_if_needed(remotedir)
    missing_files = find_missing_remote_files_recursive(localdir, remotedir)
    # Limit the number of files we'll try to mirror at once, if requested
    if max_num_files is not None:
        missing_files = missing_files[:max_num_files]

    files_to_transfer = copy.copy(missing_files)  # may not need to copy here, since I reassign the whole missing files
                                                  # array later, but can't hurt (except for using more memory)
    if verbosity > 0:
        shell_msg("{0} files to transfer (max requested is {1})".format(
            len(files_to_transfer), 'unlimited' if max_num_files is None else max_num_files))

    while len(missing_files) > 0 and number_attempts > 0:
        for f in missing_files:
            file_subdir = os.path.dirname(f)
            file_remote_path = remotedir + "/" + file_subdir
            _make_remote_dir_if_needed(file_remote_path, verbosity=verbosity)
            file_local_path = os.path.join(localdir, f)
            if verbosity > 1:
                shell_msg("Transferring file {0} of {1}: {2}".format(missing_files.index(f)+1, len(missing_files), file_local_path))
            lftp_cmd = ["lftp", "-e", "put -O '{0}' {1}; bye".format(file_remote_path, file_local_path), box_url]
            shell_msg("LFTP command = {0}".format( ' '.join(lftp_cmd)))
            child = subprocess.Popen(lftp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return_code = child.wait()
            if return_code != 0 and verbosity > 1:
                shell_msg("  Transfer failed; will try again after trying all other files")
                if verbosity > 2:
                    shell_msg("    From lftp: {0}".format(child.communicate()[1]))

        tmp_missing_files = find_missing_remote_files_recursive(localdir, remotedir)
        missing_files = [f for f in files_to_transfer if f in tmp_missing_files]

        number_attempts -= 1

        if len(missing_files) == 0:
            if verbosity > 0:
                shell_msg("Transfer of {0} files successful".format(len(files_to_transfer)))
            break
        elif verbosity > 0 and number_attempts > 0:
            shell_msg("{0} of {1} files did not transfer, I will try {2} more times".format(
                len(missing_files), len(files_to_transfer), number_attempts
            ))
        elif verbosity > 0:
            shell_msg("{0} of {1} files did not transfer, but I am out of attempts. Stopping".format(
                len(missing_files), len(files_to_transfer)
            ))

    return len(missing_files) == 0
