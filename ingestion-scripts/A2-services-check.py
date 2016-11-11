#!/usr/bin/env python

"""
services_check.py

Check service states.

Copyright (C) 2013  Nexenta Systems
William Kettler <william.kettler@nexenta.com>
"""

import functions
import sys
import re

def check_svcs(p):
    """
    Check for services in maintenance or degraded state.

    Inputs:
        p (str): Path to collector
    Outputs:
        None
    """
    svcs = functions.svcs(p)
    state = re.compile('maintenance|degraded')

    for s in svcs:
        if state.search(s[0]):
            print '%s %s' % (s[0].upper(), s[2])
    
def main(p):
    try:
        check_svcs(p)
    except Exception as e:
        print e
        sys.exit(1)
                        
if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print sys.argv[0] + ": no directory specified."
    else:
        main(sys.argv[1])