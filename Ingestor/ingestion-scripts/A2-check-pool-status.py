#!/usr/bin/env python

# Author: andrew.galloway@nexenta.com
# Created On: 2013-09-26
# Last Updated On: 2013-09-26
# Description:
#   Runs a number of checks against zpool status and outputs warnings to warning files.

import sys
import functions  # local functions.py file
import re

# name of this script - could be filename, or something unique people will recognize
script_name = 'A2-check-pool-status.py'

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
def main(bundle_dir):

    if verify_bundle_directory(script_name, bundle_dir):
        warning_file = bundle_dir + "/ingestor/warnings/check-pool-status"
        with open(bundle_dir + "/zfs/zpool-status-dv.out") as f:
            
            # there's probably a way better way to do this
            pool = ""
            vdev = ""
            reading_config = False
            in_vdev = False
            vdev_count = 0

            for line in f:
                if line[0:7] == '  pool:':
                    pool = line[8:]
                    continue

                if line[0:7] == ' state:':
                    state = line[8:]

                    if state != 'ONLINE':
                        append_file(warning_file, "Pool '" + pool + "' has state '" + state + "'.\n")

                    continue

                if line[0:6] == ' scan:':
                    # TODO: check for recent scrub by date and alert if recent
                    continue

                if line[0:7] == 'config:':
                    continue
                
                if line[0:40] == '        NAME                       STATE':
                    reading_config = True
                    continue

                if line in ['\n', '\r\n']:
                    if reading_config == True:
                        reading_config == False
                if line[0:12] == 'logs' or line[0:12] == 'spar':
                    if reading_config == True:
                        reading_config == False

                if reading_config == True:
                    if line[0:15] != 'raidz' and line[0:15] != 'mirro':
                        append_file(warning_file, "Pool '" + pool + "' might have no-parity disks in it!\n")

                    if line[0:15] == 'raidz' or line[0:15] == 'mirro':
                        in_vdev == True
                        continue

                    if in_vdev == True:
                        
                        
                
    else:
        print script_name + ": directory (" + bundle_dir + ") not valid."
        sys.exit(1)


# no reason to touch
if __name__ == '__main__':

    if len(sys.argv) <= 1:
        print script_name + ": no directory specified."
    else:
        main(sys.argv[1])
