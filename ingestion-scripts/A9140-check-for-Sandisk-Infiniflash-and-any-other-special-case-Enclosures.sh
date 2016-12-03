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
# Task: check for Sandisk Infiniflash and any other special case Enclosures.

	if [[ -e $path_sesctl_enclosure ]]; then
	    ENCLOSURES=($(awk {'print $4'} $path_sesctl_enclosure | sort | uniq | grep -v "LID"))
	else
	    echo  "No enclosures defined/detected! Did this pass SAC?" >> $outfile
	fi
	if [[ ${#ENCLOSURES[@]} -ne "0" ]]; then
	    echo  "$C_BLUE==== Enclosure(s) ====$C_RESET" >> $outfile
	    echo  "Total of$C_BOLD ${#ENCLOSURES[@]} enclosures.$C_RESET" >> $outfile
	    for enclosure_sas in ${ENCLOSURES[@]}; do
	        enclosure_name=$(grep $enclosure_sas $path_sesctl_enclosure | head -n1 | cut -f 1 -d ":")
	        enclosure_status=$(grep $enclosure_sas $path_sesctl_enclosure | head -n1 | awk {'print $5'})
	        enclosure_paths=$(grep $enclosure_sas $path_sesctl_enclosure | wc -l)
	        case $enclosure_name in
	            "SANDISK-SDIFHS01")
	                echo  "* JBOD: Sandisk IF100, $enclosure_sas with $enclosure_paths paths" >> $outfile
	            ;;
	            "SANDISK-SDIFHS02")
	                echo  "* JBOD: Sandisk IF150, $enclosure_sas with $enclosure_paths paths" >> $outfile
	            ;;
	            *)
	                echo  "* JBOD: $enclosure_name, $enclosure_sas with $enclosure_paths paths" >> $outfile
	            ;;
	        esac
	        if [[ $enclosure_status -ne "OK" ]]; then
	            echo  "  *$C_RED$C_BOLD WARNING!$C_RESET The JBOD error status is $enclosure_status" >> $outfile
	        fi
	    done
	    echo  >> $outfile
	elif [[ $ctype = "collector" ]]; then
	    echo  "Enclosure detection problem." >> $outfile
	else
	    echo  "* Bundle in use - functionality not yet supported." >> $outfile
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
