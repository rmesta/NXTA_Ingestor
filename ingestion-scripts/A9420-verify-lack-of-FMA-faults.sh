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
# Task: verify lack of FMA faults
    fmadmfaulty_cnt=$(grep -A2 TIME $path_fmadm_faulty | egrep -v "^TIME|^-" | wc -l)
    if [[ $fmadmfaulty_cnt > 0 ]]; then
        ###if [[ $my_date ]]; then
            echo  "* fmadm faulty has $fmadmfaulty_cnt entries!" >> $outfile
            if [[ $long_output ]]; then
                grep -A2 TIME $path_fmadm_faulty | egrep -v "^TIME|^-"
            fi
            echo  >> $outfile
            ###for i in {0..6};do
                ###collector_date=$(date --date="$my_date -${i} day" +"%b %d")
                ###grep -A2 TIME $path_fmadm_faulty | egrep -v "^TIME|^-" | grep "$collector_date" | grep -v " $(date --date="-1 year" +%Y) | $(date --date="-2 years" +%Y) | $(date --date="-3 years" +%Y) | $(date --date="-4 years" +%Y) | $(date --date="-5 years" +%Y) "
            ###done
            ###echo
        ###else
            #fmadmfaulty=$(grep -A2 TIME $path_fmadm_faulty | egrep -v "^TIME|^-" | head -n3)
            ###echo "* fmadm faulty has $fmadmfaulty_cnt entries! Three most recent:"
            #printf "$fmadmfaulty"
            ###grep -A2 TIME $path_fmadm_faulty | egrep -v "^TIME|^-" | head -n3
            ###echo
        ###fi
    fi
    # Check retire_store for obvious entries
    if [[ -s $state_retire_store ]]; then
        retire_store_cnt=$(strings $state_retire_store | egrep -v rio | wc -l)
        if [[ $retire_store_cnt > 0 ]]; then
                echo  "* retire_store has $retire_store_cnt entries!" >> $outfile
                if [[ $long_output ]]; then
                    strings $state_retire_store | egrep -v rio
                fi
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
