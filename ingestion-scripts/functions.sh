#!/usr/bin/env bash

# Author: andrew.galloway@nexenta.com
# contact with questions or additions/changes (use Github)

# this file contains generic functions for use in other ingestion scripts

# colors, if you should want to use. To use, simply call the variables you want, and be SURE to call $C_RESET when
# you reach the end of what you want to colorize. Here's an example line that would work:
# echo -e "Testing color. ${C_UND}${C_BOLD}${C_BLUE}Blue${C_RESET}. ${C_RED}Red${C_RESET}." > file
C_UND=$(tput sgr 0 1)
C_RESET=$(tput sgr0)
C_BOLD=$(tput bold)
C_RED=$(tput setaf 1)
C_GREEN=$(tput setaf 2)
C_YELLOW=$(tput setaf 3)
C_BLUE=$(tput setaf 4)
C_MAGENTA=$(tput setaf 5)
C_CYAN=$(tput setaf 6)
C_WHITE=$(tput setaf 7)

# sigh, our versions. this attempts to create a 4-digit (I hope we never releases a 5 digit version) number by ripping off
# the .'s in our version and right padding with 0's. So if you want any version in 3.x line, you'd check for 3000-3999.
# if you want specific version 3.1.4.2, you'd look for 3142. If you want version 3.1.5 or greater, you'd look for > 3150.
# if you want specifically 3.0.3, you'd look for 3030, etc, etc.
function check_nexenta_version()
{
    local BD=$1

    local RESULT=$(grep 'Appliance version:' ${BD}/collector.stats | awk -F'(' '{print $2}' | sed 's/)//' | sed 's/^v//' | sed 's/\.//g' | sed -e :a -e 's/^.\{1,3\}$/&0/;ta')

    echo ${RESULT}
}
