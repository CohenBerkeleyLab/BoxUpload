from __future__ import print_function
import sys
import re
import pdb

if len(sys.argv) < 3:
    print("Usage: {0} <file_in> <file_out>".format(sys.argv[0]), file=sys.stderr)
    exit(1)

file_in = sys.argv[1]
file_out = sys.argv[2]

if file_in == file_out:
    print("Overwriting the input file may cause issues, please write to a different file", file=sys.stderr)
    exit(1)

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
