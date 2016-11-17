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
# Task: check licensing status etc
    case $appl_version in
        5.*)
            echo  "Appliance ($appl_version) is supported but doesn't provide sufficient data for csummary. Functionality is reduced." >> $outfile
        ;;
        "4.0.4"*|"3.1.6"*)
            echo  "Appliance ($appl_version) is supported!" >> $outfile
        ;;
        "3."*|"4.0."*) # all other versions, basically
            echo  "Warning: Appliance $appl_version is no longer supported (or isn't a valid version)! Direct customer to upgrade and to review the portal." >> $outfile
            echo  "Please involve your TAM and manager in supportability decisions." >> $outfile
            echo  >> $outfile
            if [[ ! ($force_run = "yes") ]]; then
                echo  $0 >> $outfile
                exit
            fi
        ;;
        *)
        echo  "Unable to detect appliance version ($appl_version)!" >> $outfile
        exit
        ;;
    esac
    
    license_countdown "$license_expire"
    
    printf  "*** Hostname: $my_hostname\n" >> $outfile
    printf  "*** Domain: $my_domain\n" >> $outfile
    if [[ $appl_version =~ 5.* ]]; then
        printf  "$my_license_features" >> $outfile
    fi
    #printf "\n*** License: $license_expire\n\n"
    
    #mpt_sas patch check
    # TODO This can be globalized via checklet for all NEX patches, potentially 
    # /home/support/ingested/2016-09-23/collector-G036-3EC0CE0621-6BDC9H8GJ-BLIFDL_XEPAY90705_2016-09-23.15-32-08EST
    # /home/support/ingested/2016-09-22/collector-P040-A74FF76046-449DIF8CN-HFIJKE_m-nxt-c03n01_2016-09-22.12-34-25CDT
    mpt_sas_patch=$(grep driver-storage-mpt-sas $path_pkglist | awk '{print $3}' | awk -F. '{print $2}')
    if [[ ! -z $mpt_sas_patch ]]; then
        echo  "* NEX-${mpt_sas_patch}: PATCH Installed for mpt-sas." >> $outfile
    fi
    
    echo  >> $outfile
    echo  $uptime >> $outfile
    echo  "" >> $outfile

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
