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
# Task: verify SMART is disabled on all drives
    smart_present=$(grep smart $path_appliance_runners | grep enabled)
    if [[ $smart_present ]]; then 
        echo  ""  >> $outfile
        echo  "* $C_YELLOW SMART is enabled$C_RESET and should not be!" >> $outfile
        printf  "$smart_present\n" >> $outfile
        echo   >> $outfile
    fi
    smart_count=$(grep Enabled $path_lun_smartstat | grep -v GUID | wc -l)
    if [[ $smart_count ]]; then 
        if [[ $smart_count -gt 0 ]]; then
            echo  "SMART enabled on $smart_count disks." >> $outfile
            echo  >> $outfile
        fi
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
