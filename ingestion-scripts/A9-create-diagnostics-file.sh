#!/usr/bin/env bash
#
# Author:	andrew.galloway@nexenta.com
# Created On:	2013-09-26
# Last Updated:	2016-11-09
# Description:
#   creates and initially seeds a summary/diagnostics file similar to old support bundle 'diag' file

#
# include generic functions file
#
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }
source ${NXTA_INGESTOR}/ingestion-scripts/functions.sh

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
    echo "Hostname:   $HOST" > $DIAG
    echo "License Key: $LICENSE_KEY" >> $DIAG
    echo "Version:     $VERSION" >> $DIAG
    echo "" >> $DIAG

    # summary
    echo $SEPERATOR >> $DIAG
    echo "System Summary" >> $DIAG
    echo $SEPERATOR >> $DIAG

    CPU=`cat ${BUNDLE_DIR}/system/kstat-p-td-10-6.out | grep cpu_info | grep 'vendor_id\|brand' | head -2 | awk -F' ' '{$1="";printf $0}'`
    RAM=`grep 'Physical' ${BUNDLE_DIR}/system/echo-memstat-mdb-k-tail-n2.out | awk '{print int($3/1024+0.5)" GB"}'`
    ZPOOLS=`grep -v '^NAME\|^syspool' ${BUNDLE_DIR}/zfs/zpool-list-o-all.out | wc | awk '{printf $1}'`
    NUM_DATASETS=`grep -v '^NAME\|@\|^syspool' ${BUNDLE_DIR}/zfs/zfs-get-p-all.out | awk '{print $1}' | sort -n | uniq | wc | awk '{printf $1}'`
    NUM_SNAPSHOTS=`grep '@' ${BUNDLE_DIR}/zfs/zfs-get-p-all.out | grep -v ^syspool | awk '{print $1}' | sort -n | uniq | wc | awk '{printf $1}'`
    NUM_DRIVES=`grep '^=' ${BUNDLE_DIR}/disk/hddisco.out | wc | awk '{printf $1}'`
    DRIVE_BREAKDOWN=$(for DISK in `grep '^=' ${BUNDLE_DIR}/disk/hddisco.out`; do VENDOR=`grep -A16 $DISK ${BUNDLE_DIR}/disk/hddisco.out | grep ^vendor | awk -F' ' '{$1="";printf $0}'`; PRODUCT=`grep -A16 $DISK ${BUNDLE_DIR}/disk/hddisco.out | grep ^product | awk -F' ' '{$1="";printf $0}'`; echo "$VENDOR $PRODUCT"; done | sort -n | uniq -c)

    echo "Total Physical RAM: ~${RAM}, CPU Type:${CPU}" >> $DIAG
    echo "" >> $DIAG
    echo "Number of Data Pools: ${ZPOOLS}, Total Datasets: ${NUM_DATASETS}, Total Snapshots: ${NUM_SNAPSHOTS}" >> $DIAG
    echo "Drive Count: ${NUM_DRIVES}" >> $DIAG
    echo "" >> $DIAG
    echo "Zpool                                                       Size      Capacity %" >> $DIAG
    echo "--------------------------------------------------------------------------------" >> $DIAG
    
    cat ${BUNDLE_DIR}/zfs/zpool-list-o-all.out | grep -v ^NAME | awk '{printf "%-60s %-10s %-4s\n",$1,$2,$3}' >> $DIAG
    echo "" >> $DIAG

    echo "Drive Type Breakdown" >> $DIAG
    
    echo "--------------------" >> $DIAG
    OLDIFS=$IFS
    IFS=$'\n'
    for DTYPE in $DRIVE_BREAKDOWN; do 
        echo $DTYPE >> $DIAG
    done
    
    IFS=$OLDIFS

    echo "" >> $DIAG

    # waarnings
    echo $SEPERATOR >> $DIAG
    echo "Warnings" >> $DIAG
    echo $SEPERATOR >> $DIAG

    cat ${BUNDLE_DIR}/ingestor/warnings/* >> $DIAG

    echo "" >> $DIAG
    echo $SEPERATOR >> $DIAG
    echo "Diagnostics Info" >> $DIAG
    echo $SEPERATOR >> $DIAG
    echo "" >> $DIAG

    echo "Installed Plugins" >> $DIAG
    echo "-----------------" >> $DIAG
    NMS_PLUGINS='autocdp autosmart autosync cloudarchive comstar-fc confguard ns-cluster rsf-cluster simple-failover vmdc worm'
    NMC_PLUGINS='bonnie-benchmark iperf-benchmark storagelink iozone-benchmark oracle-backup clamav-antivirus ups'
    PLUGINS='remoterep'

    for PLUGIN in $NMS_PLUGINS; do
        grep -i nms-${PLUGIN} ${BUNDLE_DIR}/appliance/dpkg-l.out | grep ^ii | sed 's/nms-//g' | awk '{printf "%-25s %s\n",$2,$3}' >> $DIAG
    done

    for PLUGIN in $NMC_PLUGINS; do
        grep -i nmc-${PLUGIN} ${BUNDLE_DIR}/appliance/dpkg-l.out | grep ^ii | sed 's/nmc-//g' | awk '{printf "%-25s %s\n",$2,$3}' >> $DIAG
    done

    for PLUGIN in $PLUGINS; do
        grep -i ${PLUGIN} ${BUNDLE_DIR}/appliance/dpkg-l.out | grep ^ii | awk '{printf "%-25s %s\n",$2,$3}' >> $DIAG
    done    

    echo "" >> $DIAG
    echo "On-Board Devices" >> $DIAG
    echo "----------------" >> $DIAG

    cat ${BUNDLE_DIR}/system/prtdiag-v.out | awk '/==== On-Board Devices/,/==== Upg/' | grep -v '====' >> $DIAG

    echo "Upgradeable Slots" >> $DIAG
    echo "-----------------" >> $DIAG

    cat ${BUNDLE_DIR}/system/prtdiag-v.out | awk '/==== Upgrad/,0' | grep -v '====' >> $DIAG
    echo "" >> $DIAG

    echo "/etc/resolv.conf" >> $DIAG
    echo "----------------" >> $DIAG

    cat ${BUNDLE_DIR}/network/resolv.conf >> $DIAG
    echo "" >> $DIAG

    echo "ifconfig -a" >> $DIAG
    echo "-----------" >> $DIAG

    cat ${BUNDLE_DIR}/network/ifconfig-a.out >> $DIAG
    echo "" >> $DIAG

    echo "dladm show-link" >> $DIAG
    echo "---------------" >> $DIAG

    cat ${BUNDLE_DIR}/network/dladm-show-link.out >> $DIAG
    echo "" >> $DIAG

    echo "dladm show-aggr" >> $DIAG
    echo "---------------" >> $DIAG

    cat ${BUNDLE_DIR}/network/dladm-show-aggr.out >> $DIAG
    echo "" >> $DIAG
    cat ${BUNDLE_DIR}/network/dladm-show-aggr-x.out >> $DIAG
    echo "" >> $DIAG
    cat ${BUNDLE_DIR}/network/dladm-show-aggr-l.out >> $DIAG
    echo "" >> $DIAG

    echo "netstat -rn" >> $DIAG
    echo "-----------" >> $DIAG

    cat ${BUNDLE_DIR}/network/netstat-rn.out >> $DIAG
    echo "" >> $DIAG

    echo "Last 20 lines of root .bash_history" >> $DIAG
    echo "-----------------------------------" >> $DIAG

    cat ${BUNDLE_DIR}/os/.bash_history | tail -n20 >> $DIAG
    echo "" >> $DIAG
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
