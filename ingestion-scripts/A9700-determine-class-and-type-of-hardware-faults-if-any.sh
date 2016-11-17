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
# Task: determine class and type of hardware faults, if any
    echo  "$C_BLUE=== Unique system errors and faults ===$C_RESET" >> $outfile
    # Task : see if FMD is broken first
    if [[ ! $(grep "/usr/lib/fm/fmd/fmd" $path_ptree_a) ]]; then
        echo  "WARNING: $C_RED fmd is not currently running!$C_RESET" >> $outfile
    fi
    echo  >> $outfile
    mapfile -t errors < <(zgrep 'class = ' $path_fmdump_evt_nday | sort | uniq -c)
    
    if [[ $(grep terminated $path_fmdump_evt_nday_stats) ]]; then
        echo  >> $outfile
        echo  "WARNING:" >> $outfile
        echo  "WARNING:$C_RED fmdump terminated, all FMA data may not be present!$C_RESET" >> $outfile
        echo  "WARNING: Not processing FMA data until investigated." >> $outfile
        echo  "WARNING:" >> $outfile
        echo  >> $outfile
        pweight=$(echo $pweight - 1 | bc )
    fi
    # this is arbitrary, fuzzy, and not likely to have been hit
    if [[ ${#errors[@]} -gt "500" ]]; then 
        perf_req "Very high number of FMA events. Recommendation: mitigate underlying hardware issues before running Sparta."
        pweight=$(echo $pweight - 2 | bc)
    elif [[ ${#errors[@]} -eq "0" ]]; then
        echo  "* Odd - we don't actually see any errors in fmdump." >> $outfile
        echo  >> $outfile
    fi
    unsummarized=()
    for error in "${errors[@]}" ; do
    
        class=${error#*class = }
        # TODO we really need to be markedly more alarmed about pciex/pci/fabric errors. 
        case "$class" in
    	ereport.io.scsi.cmd.disk.tran | \
    	ereport.io.scsi.cmd.disk.dev.rqs.merr | \
    	ereport.io.scsi.cmd.disk.slow-io | \
    	ereport.io.pci.fabric) 
                # This applies to other error classes as well so use fallthrough;
    	    echo  "$error" | perl -pe 's/^ +//' >> $outfile
    	    #zgrep -A6 "class = ${class}" $path_fmdump_evt_nday | grep device-path | sort | uniq -c | sort -n
    	    zgrep -A8 "class = ${class}" $path_fmdump_evt_nday | grep device-path | sort | uniq -c | sort -n
    	    echo  >> $outfile
    	    ;;
    #	ereport.io.scsi.cmd.disk.dev.rqs.derr)
    #            # TODO do something here so ereport.io.scsi.cmd.disk.dev.rqs.derr output does not include op-code 0x15
    #            zgrep -A12 "class = ${class}" $path_fmdump_evt_nday | egrep "device-path|op-code" | grep -v -B1 "op-code = 0x15"
    #            ;; 
    	ereport.io.scsi.disk.predictive-failure)
    	    echo  "$error" | perl -pe 's/^ +//' >> $outfile
    	    zgrep -A8 "class = ${class}" $path_fmdump_evt_nday | grep serial | sort | uniq -c | sort -n
    	    echo  >> $outfile
    	    ;;
            ereport.io.scsi.cmd.disk.dev.rqs.derr)
    	    echo  "$error" | perl -pe 's/^ +//' >> $outfile
                DISKS=$(zgrep -A15 ereport.io.scsi.cmd.disk.dev.rqs.derr $path_fmdump_evt_nday | grep device-path | awk -F@ '{print $NF}' | sort | uniq)
                for disk in $(echo $DISKS); do
                    zgrep -A20 ereport.io.scsi.cmd.disk.dev.rqs.derr $path_fmdump_evt_nday | grep $disk | uniq -c
                    if [[ $long_output ]]; then
                        zgrep -A20 ereport.io.scsi.cmd.disk.dev.rqs.derr $path_fmdump_evt_nday | grep $disk -A9 | grep op-code | sort | uniq -c
                    fi
                done
                echo  >> $outfile
                ;;
            ereport.io.scsi.cmd.disk.dev.serr)
    	    echo  "$error" | perl -pe 's/^ +//' >> $outfile
                DISKS=$(zgrep -A15 ereport.io.scsi.cmd.disk.dev.serr $path_fmdump_evt_nday | grep device-path | awk -F@ '{print $NF}' | sort | uniq)
                for disk in $(echo $DISKS); do
                    zgrep -A20 ereport.io.scsi.cmd.disk.dev.serr $path_fmdump_evt_nday | grep $disk | uniq -c
                    if [[ $long_output ]]; then
                        zgrep -A20 ereport.io.scsi.cmd.disk.dev.serr $path_fmdump_evt_nday | grep $disk -A11 | grep op-code | sort | uniq -c
                    fi
                done
                echo  >> $outfile
                ;;
    	ereport.fs.zfs.timeout | \
    	ereport.fs.zfs.checksum | \
    	ereport.fs.zfs.vdev.open_failed)
    	    echo  "$error" | perl -pe 's/^ +//' >> $outfile
    	    zgrep -A16 "class = ${class}" $path_fmdump_evt_nday | grep vdev_path | sort | uniq -c | sort -n
    	    echo  >> $outfile
    	    ;;	    
            
            ereport.io.pciex.rc.ce-msg | \
            ereport.io.pciex.pl.re | \
            ereport.io.pciex.dl.bdllp)
    	    echo  "$error" | perl -pe 's/^ +//' >> $outfile
    	    zgrep -B5 "class = ${class}" $path_fmdump_evt_nday | grep device-path | sort | uniq -c | sort -n
    	    echo  >> $outfile
                ;;
        	*)
    	    unsummarized+=("${error}")
    	    ;;
        esac
    
    done
    
    if [[ ${#unsummarized[@]} -gt 0 ]] ; then
        echo  "The following error classes were not automatically summarized:" >> $outfile
        printf  "  %s\n" "${unsummarized[@]}" >> $outfile
        echo   >> $outfile
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
