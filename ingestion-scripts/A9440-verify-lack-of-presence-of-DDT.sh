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
# Task: verify lack of presence of DDT
    ddt=$(grep "DDT.*on disk" $path_zpool_status)
    if [[ $ddt ]]; then
        echo  "DDT present!" >> $outfile
        pweight=$(echo $pweight + 1 | bc ) # will probably need to demonstrate to user observable negative performance
        perf_req 'DDT present! Recommendation: migrate data from volumes with DDT and recreate. DDT has a marked negative metadata performance.'
        salt=$((RANDOM%999+1))
        grep "DDT.*on disk" $path_zpool_status > /tmp/ddt_$salt.out
        while read dedupe; do
            echo  $dedupe >> $outfile
            entries=($(echo $dedupe | sed -e 's/.*DDT entries \([0-9]*\), size \([0-9]*\) on disk, \([0-9]*\) in core/\1 \2 \3/'))
            ddt_disk=$((${entries[1]}*${entries[0]}/1024/1024))
            ddt_memory=$((${entries[2]}*${entries[0]}/1024/1024))
            echo  DDT table size: $ddt_disk MB on disk >> $outfile
            echo  DDT table size: $ddt_memory MB in memory >> $outfile
        done < <(cat /tmp/ddt_$salt.out)
        rm /tmp/ddt_$salt.out
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
