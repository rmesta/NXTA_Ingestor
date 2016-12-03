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
# Task: verify the lack of any recent kernel panics
    panic_recent=$(grep -A1 "reboot after panic" $path_messages | sed -e 's/savecore.*]//g' -e 's/reboot after //g')
    if [[ $panic_recent != "" ]]; then 
        printf  "\n* WARNING! Recent$C_RED system panics have occurred$C_RESET, please verify these are not important!\n" >> $outfile
        printf  "$panic_recent\n" >> $outfile
#    	$SCRIPT_BASE/subscripts/panichash.sh $my_pwd # TODO this isn't working consistently /home/support/ingested/2016-08-03/collector-GP02-E1F8655275-9D9FIL8MN-GGQFMF_nxprod01_2016-08-03.08-22-28EDT
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
