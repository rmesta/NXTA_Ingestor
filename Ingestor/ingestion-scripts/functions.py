#!/usr/bin/env python

# author Andrew Galloway
# contact with questions/additions/etc (use Github)

import os

def verify_bundle_directory(script_name, directory):
    if os.path.isdir(directory):
        return True
    else:
        print script_name + ": directory " + directory + " is not a valid directory."
        return False

def append_file(filename, message):
    with open(filename, "a") as af:
        af.write(message)

def bytes_format(orig_bytes):

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
    unit_num = 0
    work_bytes = int(orig_bytes)

    while work_bytes > 1024:
        work_bytes = work_bytes / 1024
        unit_num = unit_num + 1

    work_bytes = round(work_bytes, 2)
    
    return str(work_bytes) + units[unit_num]
