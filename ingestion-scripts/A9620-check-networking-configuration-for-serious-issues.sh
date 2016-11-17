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
# Task: check networking configuration for serious issues
    echo  "$C_BLUE=== Networking Problem Indicators ===$C_RESET" >> $outfile
    # netstat -s processing, using Jason's nic-check.pl instead because he already did the hard work  
    echo  "" >> $outfile
    retrans=$($SCRIPT_BASE/subscripts/nic-check.pl -d $path_dladm_show_phys -k $path_kstat | egrep "retransmission" | sed -r "s/\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[mGK]//g") # nocolor
    net_errors=$($SCRIPT_BASE/subscripts/nic-check.pl -d $path_dladm_show_phys -k $path_kstat | egrep "errors =" | sed -r "s/\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[mGK]//g") # nocolor
    echo  "* $retrans" >> $outfile
    net_duplicate=$(grep "^[a-zA-Z0-9]\+\: " $path_ifconfig_a -A1 | grep broadcast | awk '{print $6}' | sort | uniq -c | awk '{print $1}' | sort | head -n1)
    if [[ $net_duplicate -gt "1" ]]; then
        printf  "* Duplicate broadcast networks detected!\n" >> $outfile
    fi
    net_dupe_possible=$(grep "^[a-zA-Z0-9]\+\: " $path_ifconfig_a -A1 | grep broadcast | awk '{print $6}' | awk -F "." '{print $1 $2 $3 $4}' | sort | uniq -c | awk '{print $1}' | sort | head -n1)
    if [[ $net_dupe_possible -gt "1" ]]; then
        printf  "* Possible overlapping subnets detected. Check ifconfig.\n" >> $outfile
    fi
    echo  >> $outfile
    # TODO do we want to have large segment offload (LSO) detection? and if so, how?
    # $path_kstat:tcp:0:tcpstat:tcp_lso_disabled       0 <-- disabled
    
    

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
