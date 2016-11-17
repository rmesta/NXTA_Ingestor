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
# Task: check logs for presence of drive controller impacting issues
    mpt_sas=$(grep WARNING $path_messages | grep "(mpt_sas" | cut -f 2 -d "(" | cut -f 1 -d ")" | less | sort | uniq -c)
    if [[ $mpt_sas ]]; then
        perf_req "mpt_sas warnings in system messages. Recommendation: investigate problematic hardware."
        pweight=$(echo $pweight - 1 | bc )
        echo  ""  >> $outfile
        echo  "$C_YELLOW mpt_sas related warnings$C_RESET in /var/adm/messages:" >> $outfile
        printf  "$mpt_sas\n" >> $outfile
    echo  "" >> $outfile
    fi
    # TODO: check for ifaces on same subnet
    echo   >> $outfile

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
