#!/usr/bin/env bash
#
# Author:	kirill.davydychev@nexenta.com
# Created On:	2013-09-30
# Last Updated:	2016-11-09
# Description:	zeusram firmware check
#

#
# include generic functions file
#
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }
source ${NXTA_INGESTOR}/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A2-check-zeusram-firmware.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
    WARN_FILE=${BUNDLE_DIR}/ingestor/warnings/check-zeusram-firmware
    CHECK_FILE=${BUNDLE_DIR}/ingestor/checks/check-zeusram-firmware

    echo "ZeusRAM Firmware Check | zeusramfirmcheck" > ${CHECK_FILE}

    if [ -f "${BUNDLE_DIR}/ingestor/links/hddisco.out" ]; then
        grep ZeusRAM ${BUNDLE_DIR}/ingestor/links/hddisco.out

        if [ "$?" -eq 0 ]; then
            for ENTRY in `grep -B2 -A4 ZeusRAM ${BUNDLE_DIR}/ingestor/links/hddisco.out | grep ^revision | awk '{print $2}'`; do
                FIRMWARE=$(echo $ENTRY | sed 's/^C//')
                
                if [ "$FIRMWARE" -gt "22" ]; then
                    echo "<li>ZeusRAM detected with firmware >= C023 (firmware was: C${FIRMWARE})</li>" >> $CHECK_FILE
                else
                    echo "<li>ZeusRAM detected with firmware < C023 (firmware was: C${FIRMWARE})</li>" >> $WARN_FILE
                fi
            done
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
