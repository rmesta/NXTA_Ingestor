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
# Task: verify whether system memory, ARC, dump, and swap are configured appropriately for the role
    # Memory and dump device size
    # PERF TODO - if arc_meta_used closely approaches arc_meta_limit (say, within 10%), and we can, we want to increase arc_meta_limit first. Positive weight gets assigned for not being required.
    
    # ARC metadata etc. are defined in csum_functions.sh 
    
    # TODO arc_max detection is wrong (is it?), also need to determine overhead related to NEX-1760/NEX-6611
    if [[ -e $path_modparams ]]; then
        arc_max=$(echo "$(grep 'zfs_arc_max' $path_modparams | awk '{print $2'}) /1024/1024/1024" | bc) # in GB 
    else 
        if [[ $(grep zfs_arc_max $path_system ) ]]; then
            arc_max=$(echo "$(grep 'zfs_arc_max' $path_system | awk '{print $4'}) /1024/1024/1024" | bc) # in GB 
        else
            arc_max=0
        fi
    fi
    
    
    if [[ ! $(grep terminated $path_prtconf_v_stats | awk '{print $4}') = "terminated" ]]; then
        memr=$(grep -E '^Memory size' $path_prtconf_v | awk '{print $3}')
        mem=$(( $memr / 1024 + 1 ))
        echo  "Memory Size = $mem GB" >> $outfile
    elif ($appl_version =~ 5.*); then
        echo  "Bundle format lacks sufficient verbosity."  >> $outfile
    else 
        echo  "* Warning: problem with Collector data, we failed to determine system memory"  >> $outfile
    fi
    
    if [[ $(echo $dumpd|awk -F= '{print $2}') != 'swap' ]]; then
        dumpr=$(grep -E 'syspool/dump +volsize ' $path_zfs_get_all | awk '{print $3}')
        if [[ $dumpr ]]; then
            dump=$(( $dumpr / 1024 ** 3 + 1 ))
            echo  "Dump Size   = $dump GB" >> $outfile
            if [[ $dump ]]; then
                if [[ $(( $dump * 2 )) -lt $mem ]]; then
                    echo  "* Dump should be at least $(( $mem / 2 )) GB" >> $outfile
                fi
            fi
        fi
    fi
    mapfile -t swaps < <(grep swap $path_zfs_get_all | grep volsize | awk '{print $3}')
    for ((i=0;i<${#swaps[@]};i++)); do
        swapr=$(( $swapr + ${swaps[$i]} ))
    done
    swap=$(( $swapr / 1024 ** 3 ))
    echo  "Swap Size   = $swap GB" >> $outfile
    if [[ $swap ]]; then
        if [[ $mem -lt 8 ]]; then
            if [[ $swap -lt 1 ]]; then
                echo  "* Swap should be at least 1 GB" >> $outfile
            fi
        elif [[ $mem -lt 16 ]]; then
            if [[ $swap -lt 2 ]]; then
                echo  "* Swap should be at least 2 GB" >> $outfile
            fi
        elif [[ $mem -le 128 ]]; then
            if [[ $swap -lt 4 ]]; then
                echo  "* Swap should be at least 4 GB" >> $outfile
            fi
        elif [[ $mem -gt 128 ]]; then
            if [[ $(( $swap * 4 )) -lt $mem ]]; then
                echo  "* Swap should be at least $(( $mem / 4 )) GB" >> $outfile
            fi
        fi
    fi
    
    echo  "" >> $outfile
    echo  $dumpd >> $outfile
    
    # TODO the bytes -> MB/GB/byte stuff should be turned into a function for reuse. 
    if [[ $long_output ]]; then
        printf  "\n===== ARC =====\n" >> $outfile
        # Output the current ARC size, target, max and min
        mapfile -t arcstats < <(egrep "zfs:0:arcstats:(c|p|size)" $path_kstat | egrep -v "fetch|time|class" | tail -5 | awk '{print $2}')
        if [[ ${arcstats[0]} -lt 1073741824 ]]; then
            arc_target_size="$(echo ${arcstats[0]} /1024/1024 | bc) MB"
        else
            arc_target_size="$(echo ${arcstats[0]} /1024/1024/1024 | bc) GB"
        fi
        if [[ ${arcstats[0]} -lt 1073741824 ]]; then
            arc_max_size="$(echo ${arcstats[1]} /1024/1024 | bc) MB"
        else
            arc_max_size="$(echo ${arcstats[1]} /1024/1024/1024 | bc) GB"
        fi
        if [[ ${arcstats[0]} -lt 1073741824 ]]; then
            arc_min_size="$(echo ${arcstats[2]} /1024/1024 | bc) MB"
        else
            arc_min_size="$(echo ${arcstats[2]} /1024/1024/1024 | bc) GB"
        fi
        #arc_mru_size=$(echo ${arcstats[3]} /1024/1024/1024 | bc) # size in GB
        if [[ ${arcstats[4]} -lt 1073741824 ]]; then
            arc_size_size="$(echo ${arcstats[4]} /1024/1024 | bc) MB"
        else
            arc_size_size="$(echo ${arcstats[4]} /1024/1024/1024 | bc) GB"
        fi
    
        echo  "ARC Target Size  (arcstats:c)     = $arc_target_size" >> $outfile
        echo  "ARC Max Size     (arcstats:c_max) = $arc_max_size" >> $outfile
        echo  "ARC Min Size     (arcstats:c_min) = $arc_min_size" >> $outfile
        echo  "ARC Current Size (arcstats:size)  = $arc_size_size" >> $outfile
        echo  "" >> $outfile
    fi
   	# if arc_max is zero AND arc_meta_used is high, AND ARC c is high (say,
   	# within 10% of max memory, or perhaps sans-20G or...) TODO   
    if [[ ($arc_max = "0") ]]; then
        printf  "* Warning:$C_YELLOW zfs_arc_max is not set$C_RESET. This is potentially dangerous as we can overrun system processes. See: NEX-1760, NEX-6611\n"  >> $outfile
    fi
    # TODO arc_max detection is wrong, also need to determine overhead related to NEX-1760/NEX-6611
    if [[ ! ($arc_max = "0") ]]; then
        printf  "\n* zfs_arc_max is set in /etc/system.\n" >> $outfile
        echo  "zfs_arc_max = $arc_max GB" >> $outfile
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
