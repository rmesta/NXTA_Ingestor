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
