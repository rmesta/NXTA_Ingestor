#!/usr/bin/env python

"""
ses_check.py

Check enclosures sensors.

Copyright (C) 2013  Nexenta Systems
William Kettler <william.kettler@nexenta.com>
"""

import functions
import sys

def check_ses(p):
    """
    Check enclosure status and warn of non-OK state.

    Inputs:
        p (str): Path to collector
    Outputs:
        None
    """
    sesctl = functions.sesctl(p)

    # Check the status of every element
    for encl_id in sesctl:
        for e_type in sesctl[encl_id]:
            for e_num in sesctl[encl_id][e_type]:
                status = sesctl[encl_id][e_type][e_num]['status']
                if status  != 'OK' and status != 'NOT-INSTALLED':
                    print '%s %s %s has status %s' % \
                          (encl_id, e_type, e_num, status)
    
def main(p):
    try:
        check_ses(p)
    except Exception as e:
        print e
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print sys.argv[0] + ": no directory specified."
    else:
        main(sys.argv[1])