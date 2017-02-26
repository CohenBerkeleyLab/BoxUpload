from __future__ import print_function
import sys
import re
import pdb
import difflib
import argparse

def gen_diffable_file(file_in):
    file_out = file_in+"_cut"
    with open(file_in, 'r') as fin:
        with open(file_out, 'w') as fout:
            for line in fin:
                # Find the fourth instance of whitespace between words, truncate up to and including that
                # This will remove the permissions, owner, and group, but leave the size, modification time,
                # and name (hopefully)
                m = re.findall('\S+\s+', line)
                # m[0] should be the permissions, m[1] some number, m[2] the owner, m[3] the group.
                if len(m) >= 4:
                    cutline = line[line.find(m[3])+len(m[3]):]
                else:
                    cutline = line
                fout.write(cutline)
    return file_out

def gen_diff_list(local_file, remote_file):
    with open(local_file, 'r') as fl:
        local = fl.readlines()

    with open(remote_file, 'r') as fr:
        remote = fr.readlines()

    differ = difflib.ndiff(local,remote)
    return ''.join(differ).splitlines()

def list_missing_files(difflist, file_pat):
    missing = []
    i=0
    while i<len(difflist):
        if file_pat not in difflist[i]:
            i += 1
            continue
        
        if difflist[i][0] == "-": # this indicates a line missing in the remote file, e.g. a file not transferred
            # If might just have a different modification time. Check if the next line has a + and the same file
            thisline = difflist[i].split(" ")
            if difflist[i+1][0] == "+":
                nextline = difflist[i+1].split(" ")
                if nextline[-1] == thisline[-1]:
                    # File was uploaded, modification time differed. Can skip next line as well
                    i += 1
                else:
                    missing.append(thisline[-1])
            else:
                missing.append(thisline[-1])
        i += 1

    return missing

def get_args():
    parser = argparse.ArgumentParser(description="List files in the local ls missing from the remote ls")
    parser.add_argument("local_ls", help="File containing the result of ls -l on the local computer.")
    parser.add_argument("remote_ls", help="File containing the result of ls -l on the remote lftp computer")
    parser.add_argument("-l", action='store_true', help="List missing files one per line")

    return parser.parse_args()

def main():
    args = get_args()

    file_local = args.local_ls
    file_remote = args.remote_ls

    local_ls = gen_diffable_file(file_local)
    remote_ls = gen_diffable_file(file_remote)

    differ = gen_diff_list(local_ls, remote_ls)
    missing = list_missing_files(differ, 'wrfout')

    if args.l:
        out = '\n'.join(missing)
    else:
        out = ' '.join(missing)

    print(out)

if __name__ == "__main__":
    main() 
