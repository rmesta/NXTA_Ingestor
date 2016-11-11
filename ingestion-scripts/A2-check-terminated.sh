#!/usr/bin/env bash
#
# Author:	andrew.galloway@nexenta.com
# Created On:	2013-09-26
# Last Updated:	2016-11-09
# Description:
#   check for terminated list in collector.stats

#
# include generic functions file
#
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }
source ${NXTA_INGESTOR}/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A2-check-terminated.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
    WARN_FILE=${BUNDLE_DIR}/ingestor/warnings/check-terminated

    if [ -f "${BUNDLE_DIR}/collector.stats" ]; then
        grep 'Terminated List' ${BUNDLE_DIR}/collector.stats >/dev/null 2>&1

        if [ "$?" -eq 0 ]; then
            echo " - There are potentially Collector commands that errored/timed out rather than complete, check collector.stats for list." > $WARN_FILE
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
