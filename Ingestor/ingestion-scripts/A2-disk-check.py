#!/usr/bin/env python

"""
disk_check.py

Parse kstat for scsi device errors.

Copyright (C) 2013  Nexenta Systems
William Kettler <william.kettler@nexenta.com>
"""

import functions
import sys


# The error types can be individually tracked.
errors = {
    'Soft Errors': False,
    'Hard Errors': True,
    'Transport Errors': True,
    'Device Not Ready': False,
    'Illegal Request': False,
    'Media Error': True,
    'No Device': True,
    'Predictive Failure Analysis': True,
    'Recoverable': False
}

def check_disks(p):
    """
    Print disk errors.

    Inputs:
        p (str): Path to collector
    Outputs:
        None
    """
    # Determine tracked errors
    global errors
    errors = [k for k in errors.keys() if errors[k]]

    # Only interested in a single timestamp
    kstat = functions.kstat(p)
    kstat = kstat[kstat.keys()[0]]

    # Check each scsi device for any error count greater then 0
    for d in kstat['sderr']:
        for e in errors:
            count = kstat['sderr'][d]['sd%s,err' % d][e]
            if int(count) > 0:
                print 'sd%s %s: %s' % (d, e, count)
    
def main(p):
    try:
        check_disks(p)
    except Exception as e:
        print e
        sys.exit(1)
                        
if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print sys.argv[0] + ": no directory specified."
    else:
        main(sys.argv[1])