#!/usr/bin/env bash

# Author: kirill.davydychev@nexenta.com
# Created On: 2013-09-30
# Last Updated On: 2013-09-30
# Description:
#   dump check

# include generic functions file
source /root/Collector/Ingestor/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A2-check-zeusram-firmware.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
    WARN_FILE=${BUNDLE_DIR}/ingestor/warnings/check-zeusram-firmware

    if [ -f "${BUNDLE_DIR}/disk/hddisco.out" ]; then
        grep ZeusRAM ${BUNDLE_DIR}/disk/hddisco.out

        if [ "$?" -eq 0 ]; then
            grep -B2 -A4 ZeusRAM ${BUNDLE_DIR}/disk/hddisco.out | grep ^revision | grep C023 >/dev/null 2>&1

            if [ "$?" -gt 0 ]; then
                echo "ZeusRAM's with firmware other than C023 possibly detected." > $WARN_FILE
            fi
        fi
    fi
}

# this runs first, and does sanity checking before invoking main() function

# check for necessary directory argument
if [ -z "$1" ]; then
    echo "${SCRIPT_NAME} failed, no directory specified."
    exit 1
else
    if [ -d "$1" ]; then
        # begin execution
        main $1
    else
        # not a valid directory
        echo "${SCRIPT_NAME} failed, invalid directory $1 specified."
        exit 1
    fi
fi
