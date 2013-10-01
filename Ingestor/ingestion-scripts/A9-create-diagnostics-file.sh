#!/usr/bin/env bash

# Author: andrew.galloway@nexenta.com
# Created On: 2013-09-26
# Last Updated On: 2013-09-26
# Description:
#   creates and initially seeds a summary/diagnostics file similar to old support bundle 'diag' file

# include generic functions file
source /root/Collector/Ingestor/ingestion-scripts/functions.sh

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

    CPU=`cat ${BUNDLE_DIR}/system/kstat-p-td-10-6.out | grep cpu_info | grep 'vendor_id\|brand' | head -2 | awk -F' ' '{$1="";printf $0}'`
    RAM=`grep 'Physical' ${BUNDLE_DIR}/system/echo-memstat-mdb-k-tail-n2.out | awk '{print int($3/1024+0.5)" GB"}'`
    ZPOOLS=`grep -v '^NAME\|^syspool' ${BUNDLE_DIR}/zfs/zpool-list-o-all.out | wc | awk '{printf $1}'`
    NUM_DATASETS=`grep -v '^NAME\|@' ${BUNDLE_DIR}/zfs/zfs-get-p-all.out | awk '{print $1}' | sort -n | uniq | wc | awk '{printf $1}'`
    NUM_SNAPSHOTS=`grep '@' ${BUNDLE_DIR}/zfs/zfs-get-p-all.out | awk '{print $1}' | sort -n | uniq | wc | awk '{printf $1}'`
    NUM_DRIVES=`grep '^=' ${BUNDLE_DIR}/hddisco.out | wc | awk '{printf $1}'`
    DRIVE_BREAKDOWN=$(for DISK in `grep '^=' ${BUNDLE_DIR}/hddisco.out`; do VENDOR=`grep -A16 $DISK ${BUNDLE_DIR}/hddisco.out | grep ^vendor | awk -F' ' '{$1="";printf $0}'`; PRODUCT=`grep -A16 $DISK ${BUNDLE_DIR}/hddisco.out | grep ^product | awk -F' ' '{$1="";printf $0}'`; echo "$VENDOR $PRODUCT"; done | sort -n | uniq -c)

    echo "CPU Type: ${CPU}           Total Physical RAM: ${RAM}" >> $DIAG
    echo "Number Pools: ${ZPOOLS}, Total Datasets: ${NUM_DATASETS}, Total Snapshots: ${NUM_SNAPSHOTS}" >> $DIAG
    echo "Drive Count: ${NUM_DRIVES}" >> $DIAG
    echo "" >> $DIAG
    echo "Drive Type Breakdown" >> $DIAG
    echo "--------------------" >> $DIAG
    OLDIFS=$IFS;IFS='\n'; for DISK in $DRIVE_BREAKDOWN; do echo $DISK; done; IFS=$OLDIFS

    # waarnings
    echo $SEPERATOR >> $DIAG
    echo "Warnings" >> $DIAG
    echo $SEPERATOR >> $DIAG

    cat ${BUNDLE_DIR}/ingestor/warnings/* >> $DIAG

    echo $SEPERATOR >> $DIAG

    # diagnostics info
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
