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
