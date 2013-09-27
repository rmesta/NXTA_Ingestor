#!/usr/bin/env bash

# Author: andrew.galloway@nexenta.com
# Created On: 2013-09-26
# Last Updated On: 2013-09-26
# Description:
#   creates and initially seeds a summary/diagnostics file

# include generic functions file
source /root/Ingestor/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A9-create-diagnostics-file.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
    
    DIAG=${BUNDLE_DIR}/ingestor/diag-file
    SEPERATOR="----------------------------------------------------------------------------------------------------"
    HOST=`cat ${BUNDLE_DIR}/collector.stats | grep '^Hostname:' | awk -F':' '{first = $1; $1 = ""; print $0}'`
    LICENSE_KEY=`cat ${BUNDLE_DIR}/collector.stats | grep '^License' | awk -F':' '{print $2}'`
    VERSION=`cat ${BUNDLE_DIR}/collector.stats | grep '^Appliance' | awk -F':' '{print $2}'`

    # excepts 100 lines across at least
    echo "Hostname: $HOST | License Key: $LICENSE_KEY" > $DIAG
    echo "Version: $VERSION" >> $DIAG

    # summary
    echo $SEPERATOR >> $DIAG
    echo "Summary" >> $DIAG
    echo $SEPERATOR >> $DIAG


    # waarnings
    echo $SEPERATOR >> $DIAG
    echo "Warnings" >> $DIAG
    echo $SEPERATOR >> $DIAG

    cat ${BUNDLE_DIR}/ingestor/warnings/* >> $DIAG

    echo $SEPERATOR >> $DIAG
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
