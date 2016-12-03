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
# Task: verify all software systems and standard diagnostic commands return successfully
    # preliminary Collector 'health' # TODO 5 adaptation 
    if [[ $col_terminated -gt "0" && $ctype = "collector" ]]; then 
        echo  "*$C_RED Warning:$C_RESET multiple Collector subcommands$C_RED terminated while running!$C_RESET" >> $outfile
        if [[ $long_output ]]; then
            grep -H terminated */*.stats | grep -v smbstat  
        elif [[ $cytpe="bundle" ]]; then
            echo  "WARNING! We can't detect whether all commands were collected properly."  >> $outfile
        else
            printf   "\t * Terminated procesess: $col_terminated\n" >> $outfile
        fi
        echo  >> $outfile
    elif [[ $(find */*.stats 2>/dev/null | wc -l) -gt 0 ]]; then
        echo  "No terminated processes."  >> $outfile
    else 
        echo  "WARNING: No bundle audit information on system health available." >> $outfile
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
