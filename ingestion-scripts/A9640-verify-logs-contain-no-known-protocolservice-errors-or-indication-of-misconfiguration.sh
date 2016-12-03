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
# Task: verify logs contain no known protocol/service errors or indication of misconfiguration

	echo  "$C_BLUE=== Misc. messages issues ===$C_RESET" >> $outfile
	messages_smb=$(egrep -i "ntp|smbd|idmap" $path_messages | egrep -v "guest|share	not found|IPC only")
	# TODO make this less stupid
	if [[ $messages_smb ]]; then
	    echo  ""  >> $outfile
	    echo  "* Possible SMB issues, see messages" >> $outfile
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
