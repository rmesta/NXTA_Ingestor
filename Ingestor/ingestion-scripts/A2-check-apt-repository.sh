#!/usr/bin/env bash

# Author: andrew.galloway@nexenta.com
# Created On: 2013-09-26
# Last Updated On: 2013-09-26
# Description:
#   just prepares a warning directory to put various warnings into

# include generic functions file
source /root/Collector/Ingestor/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A2-check-apt-repository.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
    WARN_FILE=${BUNDLE_DIR}/ingestor/warnings/check-apt-repository

    if [ -f "${BUNDLE_DIR}/appliance/sources.list" ]; then
        LIC_MD5=`cat ${BUNDLE_DIR}/collector.stats | grep 'License key:' | awk -F':' '{print $2}'`

        for APT_MD5 in `cat ${BUNDLE_DIR}/appliance/sources.list | grep -v '^#' | awk -F'/' '{print $5}' | uniq`; do
            if [ "${LIC_MD5}" == "${APT_MD5}" ]; then
                # do nothing
            else
                echo "License key may not match an entry in /etc/apt/sources.list." >> ${WARN_FILE}
            fi
        done
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
