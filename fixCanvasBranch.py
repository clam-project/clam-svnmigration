#!/usr/bin/env python3
import sys

# IMPORTANT: This processing has to be done in binary,
# eventhough the portions to be corrected are plain text,
# otherwise binary files inside the dump get corrupted.

SRC = b"branches/GraphicsViewNetworkCanvas/"
DST = b"branches/GraphicsViewNetworkCanvas/NetworkEditor/"

isBranchCommit = False
for line in sys.stdin.buffer:
    if line.startswith(b"Node-copyfrom-path: "):
        if isBranchCommit:
            line = line.replace(b"/NetworkEditor",b"")
        isBranchCommit = False
    if line.startswith(b"Node-path: "):
        line = line.replace(SRC, DST)
    if line.startswith(b"Node-copyfrom-rev: 13368"):
        isBranchCommit = True

    sys.stdout.buffer.write(line)

