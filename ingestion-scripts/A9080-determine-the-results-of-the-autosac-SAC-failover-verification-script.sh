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
# Task: determine the results of the autosac SAC failover verification script
    echo  "$C_BLUE===== SAC Status Detection =====$C_RESET" >> $outfile
        # TODO if autosac date was within a day or two, perform verification of autosac results
        # this may be black magic
        # autosac by wkettler started being used around April 8, 2015. Any system installed prior to this isn't likely to have had auto-sac run.
    if [[ -e "$path_autosaclog" ]]; then
        echo  >> $outfile
        echo  "* Auto-SAC was run at some point."  >> $outfile
    	# TODO make this actually look up collector for sac, possibly other info
        echo  >> $outfile
    else 
        echo   >> $outfile
        echo  "* Unable to detect SAC status. If SAC was performed, it predated the current SAC." >> $outfile
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
