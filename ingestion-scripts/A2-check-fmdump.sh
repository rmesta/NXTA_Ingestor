#!/usr/bin/env bash
#
# Author:	andrew.galloway@nexenta.com
# Created On:	2013-09-26
# Last Updated:	2016-11-09
# Description:
#   simple fmadm checks

#
# include generic functions file
#
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }
source ${NXTA_INGESTOR}/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A2-check-fmdump.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
    WARN_FILE=${BUNDLE_DIR}/ingestor/warnings/check-fmdump

    if [ -f "${BUNDLE_DIR}/system/fmdump-evt-30day.out.gz" ]; then
        NUM_30DAY_ENTRIES=`zcat ${BUNDLE_DIR}/system/fmdump-evt-30day.out.gz | grep '\ 201.\ ' | wc | awk '{print $1}'`

        if [ "$NUM_30DAY_ENTRIES" -gt 0 ]; then
            echo " - There are ${NUM_30DAY_ENTRIES} fmdump entries in the last 30 days." > ${WARN_FILE}
        fi
    fi

    if [ -f "${BUNDLE_DIR}/system/fmadm-faulty.out" ]; then
        NUM_FMADM_FAULTY_ENTRIES=`cat ${BUNDLE_DIR}/system/fmadm-faulty.out | grep TIME | wc | awk '{print $1}'`

        if [ "$NUM_FMADM_FAULTY_ENTRIES" -gt 0 ]; then
            echo " - There are ${NUM_FMADM_FAULTY_ENTRIES} 'fmadm faulty' entries." >> ${WARN_FILE}
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
