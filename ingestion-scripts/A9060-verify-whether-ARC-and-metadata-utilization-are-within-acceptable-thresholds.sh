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
# Task: verify whether ARC and metadata utilization are within acceptable thresholds
    if [[ $arc_meta_limit_num -lt $arc_meta_used_num ]]; then 
        perf_req 'ARC metadata currently used exceeds the limit. Recommendation: Increase arc_meta_limit up to 60% of arc_max to allow headroom.'
        pweight=$(echo $pweight - 2 | bc )
    elif [[ $arc_meta_use_num -gt $(echo "scale=3;$arc_meta_limit_num * 0.9" | bc |  sed -e 's/\..*//') ]]; then
        perf_req 'ARC metadata use is currently within 10\% of arc_meta_limit. Recommendation: incrase arc_meta_limit up to as much as 60\% of arc_max to allow headroom.'
        pweight=$(echo $pweight - 1 | bc )
    fi
    if [[ $arc_meta_max_num -gt $(echo "scale=3;$arc_meta_limit_num * 1.2" | bc | sed -e 's/\..*//') ]]; then 
        perf_req 'ARC metadata has exceeded its limit at some point in the past by a significant margin of over 20%. Recommendation: reduce aggressive periodically run storage jobs.'
        pweight=$(echo $pweight - 1 | bc )
    elif [[ $arc_meta_max_num -gt $arc_meta_limit_num ]]; then
        perf_req 'Note: ARC metadata has exceeded the limit at some point since boot. This may be indicative of impending or historic performance issues.'
    fi
    if [[ $(grep zfs_arc_meta_limit $path_system) ]]; then
        arc_meta_limit_setting=$(echo $(grep zfs_arc_meta_limit $path_system | awk '{print $4}') /1024/1024/1024 | bc) #in GB
    else
        arc_meta_limit_setting=0
    fi
    if [[ $arc_meta_limit_setting -ne 0 ]]; then
        printf  "\n* zfs_arc_meta_limit is set in /etc/system.\n" >> $outfile
        echo  "zfs_arc_meta_limit = $arc_meta_limit_setting GB" >> $outfile
    fi
    echo  "" >> $outfile
    echo  "$arc_meta_used" >> $outfile
    echo  "$arc_meta_limit" >> $outfile
    echo  "$arc_meta_max" >> $outfile
    echo  "" >> $outfile

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
