#!/usr/bin/env bash
# generated from legacy csummary automatically by Ben Hodgens 2016-11-11

BUNDLE_DIR=$1
SCRIPT_NAME=$(echo $0 | sed -e 's/.*\///')
outfile=$(echo "${BUNDLE_DIR}/ingestor/checks/$(echo $SCRIPT_NAME)" | sed -e 's/.sh$/.out/')
if [[ -e $outfile ]]; then
	rm $outfile
fi
source "$NXTA_INGESTOR/ingestion-scripts/csum_functions.sh"

main () {
# Task: determine existence of multiple pools on the system
    if [[ $poolcount > 0 ]]; then
        snap_count=$(grep "type.*snapshot" $path_zfs_get_all  | wc -l)
        if [[ $snap_count -gt "500" ]]; then
            printf  "* There are $snap_count snapshots! Please consider disabling the check runners to decrease impact this may have on NMS.\n" >> $outfile
        fi
        if [[ $snap_count -gt "1500" ]]; then
            perf_req "$snap_count snapshots present is (potentially) enough to degrade system performance. Recommendation: analyze snapshot retention policy." 
            pweight=$(echo $pweight +1 | bc )
        fi
        echo  >> $outfile
        echo  "Pool Block/Record Sizes:" >> $outfile
        egrep "blocksize|recordsize" $path_zfs_get_all | grep -v $syspool_name |  awk '{print $3}' | sort | uniq -c
    fi

	# cleanup 
	if [[ $(wc -w $outfile | awk {'print $1'}) -lt "1" ]]; then 
		rm $outfile
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
