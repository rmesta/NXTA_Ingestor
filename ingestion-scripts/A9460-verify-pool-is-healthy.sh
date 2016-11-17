#!/usr/bin/env bash
# generated from legacy csummary automatically by Ben Hodgens 2016-11-11

BUNDLE_DIR=$1
SCRIPT_NAME=$(echo $0 | sed -e 's/.*\///')
outfile=$(echo "${BUNDLE_DIR}/ingestor/checks/$(echo $SCRIPT_NAME)" | sed -e 's/.sh$/.out/')
if [[ -e $outfile ]]; then
	rm $outfile
fi
source "/home/bhodgens/scripts/csum_functions.sh"

main () {
# Task: verify pool is healthy
    degraded=$(egrep "DEGRADED|FAULT|OFFLINE|UNKN" $path_zpool_list)
    if [[ $degraded ]]; then 
        echo   >> $outfile
        echo  "Pool in degraded state: " >> $outfile
        echo  $degraded  >> $outfile
        ppweight=$(echo $pweight - 3 | bc ) 
        perf_req 'Pool is in a degraded state. This must be corrected before Sparta can be run.'
        echo  >> $outfile
    fi
    zpool_prob=$(egrep "DEGRADE|OFFLINE|UNAVAIL" $path_zpool_status | sed -e 's/.*\(c[0-9]\+t[0-9A-Za-z]\+d[0-9]\+\).*/\1/')
    if [[ $zpool_prob ]]; then 
        echo  ""  >> $outfile
        echo  "Problems with the pool disks!" >> $outfile
        pweight=$(echo $pweight - 1 | bc )
        printf  "$zpool_prob\n" >> $outfile
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
