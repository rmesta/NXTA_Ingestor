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
# Task: check for any additional services configured for future record keeping
    services_other=$(egrep "rsync|ndmp|ldap|nis|ftp|collectd" $path_svcs_a | egrep "online|maint") 
    services_other_count=$(egrep "rsync|ndmp|ldap|nis|ftp|collectd" $path_svcs_a | egrep "online|maint" | wc -l | awk {'print $1'}) 
    if [[ $services_other_count -gt "0"  ]]; then 
        echo  >> $outfile
        echo  "* $services_other_count other notable services running/configured:" >> $outfile
        printf  "$services_other" >> $outfile
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
