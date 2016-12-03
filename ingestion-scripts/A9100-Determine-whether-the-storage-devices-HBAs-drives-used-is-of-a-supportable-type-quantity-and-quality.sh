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
# Task: Determine whether the storage devices (HBAs, drives) used is of a supportable type, quantity, and quality
    # Disk models
    # TODO we want to do some sort of detection of the type of disk as it may become more of a factor re: SSDs, eg. nocacheflush
    echo  "$C_BLUE===== Disk Models =====$C_RESET" >> $outfile
    if [[ $(cat $path_hddisco | wc -l) -gt "0" ]]; then
        grep -E '^(vendor|product|revision|is_ssd)' $path_hddisco | perl -pe '/^(vendor|product|revision)/ && s/\n/,/s' | sed -e 's/vendor/\n/g' | sed -e '/^$/d' -e 's/,$//' -e 's/product//' -e 's/,is_ssd no//' -e 's/,is_ssd yes/ \t(SSD)/' | sort | uniq -c >> $outfile
    # TODO 
    else 
        echo  "*$C_RED WARNING: no hddisco$C_RESET output!" >> $outfile
    fi
    is_sata=$(grep ATA $path_iostat_en |  wc -l)
    if [[ $is_sata -gt 0 ]]; then
           echo  "" >> $outfile
           echo  "* WARNING! $is_sata $C_YELLOW SATA disks$C_RESET are installed" >> $outfile
       perf_req "SATA drives are historically prone to cause performance issues and are not recommended for use in general but permitted for syspool."
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
