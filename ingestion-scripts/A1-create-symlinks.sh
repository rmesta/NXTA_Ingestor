#!/usr/bin/env bash
#
# Author:	andrew.galloway@nexenta.com
# Created On:	2013-09-26
# Last Updated:	2016-11-09
# Description:
#   creates an ingestor/links dir in the bundle and symlinks all .out* files in it for ease of location
#   - could be used by other scripts to prevent having to know exact dirs to look in, perhaps

#
# include generic functions file
#
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }
source ${NXTA_INGESTOR}/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A1-create-symlinks.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity

    mkdir -p ${BUNDLE_DIR}/ingestor/links/

    cd ${BUNDLE_DIR}/ingestor/links

    # all .out files is easy:
    for OUT_FILE in `ls -1 -R ../../*/*.out*`; do
        ln -s ${OUT_FILE}
    done

    # /var/adm/messages is a commonly desired one, find it (depending on version of Collector could be in 2 places)
    MDIR="os"
    if [ -f ../../kernel/messages ]; then
        MDIR="kernel"
    fi

    for FILE in `ls -1 ../../${MDIR}/messages*`; do
        ln -s $FILE
    done
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
