#!/usr/bin/env bash
#
# Author:	andrew.galloway@nexenta.com
# Created On:	2013-09-26
# Last Updated:	2016-11-09
# Description:
#   checks if the pool utilization is greater than 70% on any pool and reports
#   that if it is

#
# include generic functions file
#
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }
source ${NXTA_INGESTOR}/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A2-check-pool-utilization.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
    OLDIFS=$IFS
    IFS=$'\n'

    WARN_FILE=${BUNDLE_DIR}/ingestor/warnings/check-pool-utilization
    CHECK_FILE=${BUNDLE_DIR}/ingestor/checks/check-pool-utilization

    if [ -f "${BUNDLE_DIR}/ingestor/links/zpool-list-o-all.out" ]; then
        for LINE in `cat ${BUNDLE_DIR}/ingestor/links/zpool-list-o-all.out | grep -v '^NAME'`; do
            ZPOOL=`echo ${LINE} | awk '{print $1}'`
            UTIL=`echo ${LINE} | awk '{print $3}' | sed 's/%//g'`
    
            if [ $UTIL -gt 69 ]; then
                echo "<li>Volume ${ZPOOL} is ${UTIL}% utilized</li>" >> ${WARN_FILE}
            else
                echo "<li>Volume ${ZPOOL} is ${UTIL}% utilized</li>" >> ${CHECK_FILE}
            fi
        done
    fi

    IFS=$OLDIFS
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
