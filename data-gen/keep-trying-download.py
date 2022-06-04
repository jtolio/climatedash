#!/usr/bin/env python3

import os, subprocess, time


def filecount():
    return len([x for x in os.listdir("data") if x.endswith(".nc")])


def allsame(vals):
    if len(vals) == 0:
        return True
    for v in vals[1:]:
        if v != vals[0]:
            return False
    return True


filecounts = [1, 2, 3]

while not allsame(filecounts[-3:]):
    subprocess.check_call(["./download.sh"])
    filecounts.append(filecount())
    time.sleep(10)
