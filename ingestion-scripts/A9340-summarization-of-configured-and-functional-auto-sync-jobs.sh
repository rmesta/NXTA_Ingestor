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
# Task: summarization of configured and functional auto sync jobs

	services_autosync=$(grep "status" $path_appl_replication | egrep "online|maint")
	services_autosync_count=$(grep "status" $path_appl_replication | egrep "online|maint" | wc -l | awk {'print $1'})
	
	if [[ $services_autosync_count -gt "0" ]]; then
	    if [[ $long_output ]]; then
	        printf  "* $services_autosync_count Auto-Sync services running/configured and 'online':\n" >> $outfile
	        egrep -B10 online $path_appl_replication | grep instance | cut -f 2 -d ":"
	    else
	        printf  "* $services_autosync_count Auto-Sync jobs configured\n" >> $outfile
	    fi
	    echo  >> $outfile
	else
	    echo  >> $outfile
	    echo  "* no auto-sync configured." >> $outfile
	fi
	services_autosnap=$(egrep "auto-snap" $path_svcs_a | egrep "online|maint" | awk {'print $3'})
	services_autosnap_count=$(egrep "auto-snap" $path_svcs_a | egrep "online|maint" | awk {'print $3'} | wc -l )
	
	if [[ $services_autosnap_count -gt "0" ]]; then
	    if [[ $long_output ]]; then
	        printf  "* $services_autosnap_count Auto-Snap services running/configured and 'online':\n" >> $outfile
	        printf  "services_autosnap" >> $outfile
	    else
	        printf  "* $services_autosnap_count Auto-Snap jobs configured\n" >> $outfile
	    fi
	    echo  >> $outfile
	else
	    echo  >> $outfile
	    echo  "* no Auto-Snap configured." >> $outfile
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
