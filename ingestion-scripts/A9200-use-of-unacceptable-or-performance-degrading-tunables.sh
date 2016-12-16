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
# Task: use of unacceptable or performance degrading tunables
	primary_cache_none=$(grep primarycache.*none $path_zfs_get_all | grep -v @ | awk {'print $1'})
	if [[ $primary_cache_none != "" ]]; then
	    printf  "\t* primarycache is set to \'$primary_cache_none\'!\n" >> $outfile
	    perf_req "Primary cache set to 'none' effectively disables ZIL and ARC! Performance will not be good. Please remedy."
	    pweight=$(echo $pweight - 1 | bc )
	fi
	primary_cache_meta=$(grep primarycache.*metadata $path_zfs_get_all | grep -v @ | awk {'print $1'})
	if [[ $primary_cache_meta != "" ]]; then
	    printf  "\t * primarycache is set to \'primary_cache_meta\'!\n" >> $outfile
	    perf_req "Primary cache set to 'metadata' effectively disable ARC for non-ZIL ! Performance will not be good. Please remedy."
	    pweight=$(echo $pweight - 1 | bc )
	fi
	compression_state_off=$(grep " compression " $path-zfs_get_all | awk {'print $1,$2,$3'} | grep -v $syspool_name | grep off$) 
	if [[ $(printf "$compression_state_off" | wc -l) -gt 0 ]]; then
		printf "\t * compression is set to 'off' on the following volumes. This will cause buffers in L2 ARC to be uncompressed and may consume more memory than anticipated.\n" >> $outfile
		printf "$compression_state_off\n" >> $outfile
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
