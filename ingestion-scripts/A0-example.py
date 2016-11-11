#!/usr/bin/env python
#
# Author:       andrew.galloway@nexenta.com
# Created On:   2013-09-26
# Last Updated: 2016-11-10
# Description:  ingestor python script template
#
import sys
import os
from functions import *             # include generic functions file

#
# name of this script
# could be filename, or something unique and recognizable
#
script_name = 'A0-example.py'

#
# put your actual code within this function, be
# sure to exit 0 if successful and exit 1 if not
#
def main(bundle_dir): 

    if verify_bundle_directory(script_name, bundle_dir):
        # put code here
        print script_name + ": directory (" + bundle_dir + ") seems valid."
    else:
        print script_name + ": directory (" + bundle_dir + ") not valid."
        sys.exit(1)

#
# no reason to touch
#
if __name__ == '__main__':

    try:
        os.environ['NXTA_INGESTOR']
    except KeyError:
        print "NXTA_INGESTOR var MUST be set !"
        sys.exit(1)

    if len(sys.argv) <= 1:
        print script_name + ": no directory specified."
    else:
        main(sys.argv[1])
