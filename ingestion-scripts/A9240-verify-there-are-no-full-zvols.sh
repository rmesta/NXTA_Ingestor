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
# Task: verify there are no full zvols
    if [[ $FULL_ZV -eq 1 ]]; then
        echo  -e "* ALERT! One or more$C_RED zvols are OUT OF SPACE!$C_RESET Check 'zfs get all' for more details." >> $outfile
        for i in $(echo $FILESYSTEMS); do
            AVAILABLE=$(grep "$i " $path_zfs_get_all | grep available | awk '{print $3}')
            if [[ $AVAILABLE -eq "0" ]]; then
    #            if [[ $long_output ]]; then
                    echo  -e "\t* ZVOL $i has NO space left." >> $outfile
    #            fi
            fi
        done
        echo  "" >> $outfile
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
