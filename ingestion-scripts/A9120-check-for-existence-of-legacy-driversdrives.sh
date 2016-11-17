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
	# Task: check for existence of legacy drivers/drives
	if [[ $(grep cmdk $path_hddisco | wc -l) -ne "0" ]]; then
	    echo  "* WARNING: $C_YELLOW cmdk$_RESET disk driver present!" >> $outfile
	fi
	echo   >> $outfile
	# TODO perhaps some magic to find out which disks/jbods are hanging off which HBAs, or which are unused.
	echo  "" >> $outfile
	echo  "$C_BLUE===== SAS HBAs ====$C_RESET" >> $outfile
	# TODO want to read this into an array but perhaps not necessary
	grep -E '^(HBA|    Model|    Firmware Version)' $path_sasinfo_hba_v >> $outfile
	
	hba_ir_present=$(grep Model.*IR $path_sasinfo_hba_v | wc -l)
	if [[ $hba_ir_present -gt "0" ]]; then
	    echo  "* Warning! IR firmware is present but not supported!" >> $outfile
	    perf_req "IR HBA firmware is present but not supported. It can cause performance problems due to spurious interrupts."
	fi
	
	# TODO need to more clearly define what it is we're testing for the MegaRAID controllers
	
	if [[ $(grep mr_sas $path_hddisco | wc -l) -gt "2" ]]; then
	    printf  "\t* mr_sas in use on this system on non-syspool drives.\n" >> $outfile
	    mr_sas_lsidriver=$(grep driver-storage-mr-sas-nexenta $path_pkglist)
	    if [[ $mr_sas_lsidriver = "" ]]; then
	        printf  "\t* However, the correct LSI/Nexenta driver is not in use!\n" >> $outfile
	        perf_req "The Nexenta driver-storage-mr-sas-nexenta package must be installed for proper performance with mr_sas."
	    else
	        printf  "\t* driver-storage-mr-sas-nexenta is in use.\n" >> $outfile
	    fi
	fi
	if [[ $(grep Initiator $path_fcinfo_hba_port_l ) ]]; then
	    echo  >> $outfile
	    echo  "$C_BLUE==== FC HBAs ====$C_RESET" >> $outfile
	    grep -E '(HBA Port|Model|Firmware|State)' $path_fcinfo_hba_port_l
	fi
	echo  >> $outfile
	

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
