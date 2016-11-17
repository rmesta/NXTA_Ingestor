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
# Task: flag any potential performance issues
    if [[ ${#perf_pre[@]} > "1" ]]; then 
        echo  "$C_BLUE=== Sparta Performance Related Requirements/Notes ===$C_RESET" >> $outfile
        #echo "The weighted likelihood that Sparta should be run is: TBD%"
        #$(echo "scale=3; (20 - $pweight)*5 " |bc | sed -e 's/\..*//' )% "
        echo  >> $outfile
        echo  "These items must be addressed prior to running Sparta:" >> $outfile
        echo  >> $outfile
        for ((i=1;i<${#perf_pre[@]};i++)); do
            echo  -e "  * ${perf_pre[$i]}" >> $outfile
        done
        echo  >> $outfile
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
