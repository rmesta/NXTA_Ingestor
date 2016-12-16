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
# Task: determine whether the pool is unacceptably full
    poolfull=$(grep "[6-9][0-9]%" $path_zpool_list | grep -v $syspool_name | awk '{print $1"\t"$2"\t" $3}')
    poolfull_percent=$(echo $poolfull | awk "{print $3}")
    if [[ $long_output = "yes" && $pool_full ]]; then
        if [[ $poolfull_percent =~ [6-7][0-9]*  ]]; then
            echo ""
            echo "Pool$C_YELLOW capacity$C_YELLOW approaching recommended limit$C_RESET of 80%:"
            echo $poolfull
            echo ""
            perf_req "Recommended pool capacity of 80% for optimal performance is being approached:\n$poolfull"
            pweight=$(echo $pweight - 1 | bc )
        elif [[ $poolfull_percent =~ [8-9][0-9]* ]]; then
            perf_req 'Reduce pool utilization. Capacity should typically be kept below 80%. In some instances, degraded performance may occur before pool capacity reaches this capacity.'
            pweight=$(echo $pweight - 2 | bc )
        fi
    elif [[ $poolfull_percent =~ [8-9][0-9]* ]] ; then
            perf_req 'Reduce pool utilization. Capacity should typically be kept below 80%. In some instances, degraded performance may occur before pool capacity reaches this capacity.'
            pweight=$(echo $pweight - 2 | bc )
    fi
    
    FILESYSTEMS=$(grep "type.*volume" $path_zfs_get_all | grep -v $syspool_name | grep -v "nza[-_]reserve" | awk '{print $1}')
    for i in $FILESYSTEMS; do
        AVAILABLE=$(grep "$i " $path_zfs_get_all | grep available | awk '{print $3}')
        USED=$(grep "$i " $path_zfs_get_all | grep " used " | awk '{print $3}')
        if [[ $AVAILABLE -eq 0 ]]; then
            FULL_ZV=1
        fi
    done

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
