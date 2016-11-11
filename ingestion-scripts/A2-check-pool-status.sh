#!/usr/bin/env bash
#
# Author:	andrew.galloway@nexenta.com
# Created On:	2013-09-26
# Last Updated:	2016-11-09
# Description:
#   checks if the pool has any obvious warning signs

#
# include generic functions file
#
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }
source ${NXTA_INGESTOR}/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A2-check-pool-status.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
    WARN_FILE=${BUNDLE_DIR}/ingestor/warnings/check-pool-status

    if [ -f "${BUNDLE_DIR}/zfs/zpool-status-dv.out" ]; then
        grep 'DEGRADED\|FAULTED\|OFFLINE' ${BUNDLE_DIR}/zfs/zpool-status-dv.out >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo " - There is a DEGRADED, FAULTED, or OFFLINE status on a disk, vdev, or zpool." > ${WARN_FILE}
        fi

        grep 'INUSE' ${BUNDLE_DIR}/zfs/zpool-status-dv.out >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo " - There is an INUSE spare in a zpool." >> ${WARN_FILE}
        fi

        grep 'in progress' ${BUNDLE_DIR}/zfs/zpool-status-dv.out >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo " - There is a resilver or scrub in progress on a zpool." >> ${WARN_FILE}
        fi

        grep 'spare-' ${BUNDLE_DIR}/zfs/zpool-status-dv.out >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo " - There is a spare pseudo device on a pool." >> ${WARN_FILE}
        fi
    fi

    if [ -f "${BUNDLE_DIR}/zfs/zpool-list-o-all.out" ]; then
        cat ${BUNDLE_DIR}/zfs/zpool-list-o-all.out | awk '{print $12}' | grep -v 'FAILMODE\|panic' >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            grep 'No such file or directory' ${BUNDLE_FILE}/plugins/tar-czf-opthac.err >/dev/null 2>&1
    
            if [ $? -eq 1 ]; then
                echo " - A pool contains a failmode other than panic, but RSF-1 is installed. Verify pool is not part of HA service." >> ${WARN_FILE}
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
