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
# Task: qualify the pool configuration as supportable
    echo  "$C_BLUE==== Configured pool filesystems/volumes ====$C_RESET" >> $outfile
    echo  >> $outfile
    poolpresent=$(egrep -v "^NAME|^$syspool_name" $path_zpool_list | awk {'print $1'})
    poolcount=$(echo $poolpresent | wc -w) 
    if [[ "$poolcount" -gt "1" ]]; then
        echo  "* There are $poolcount data pools present on this system!" >> $outfile
        echo  >> $outfile
    #    echo "$poolpresent" not modifying this variable as its used later/in a different fashion
        awk {'print $1"\t" $2"\t"$3'} $path_zpool_list | grep -v $syspool_name >> $outfile
        echo  >> $outfile
        perf_req "There is more than 1 pool on this system. This is sub-optimal for ARC metadata performance. Please move a pool to the other node, if appropriate, to balance workload."
        pweight=$(echo $pweight - 1 | bc )
    elif [[ $poolcount -eq "1" ]]; then 
        # don't bother with these tests if there's more than 1 pool imported (for the time being, may change later)
        # pool_create_date=$(grep "zpool create" $path_zfs_history | grep $poolpresent | cut -f 1 -d ".") # doesn't work if the pool's been renamed
        pool_create_date=$(grep "zpool create" $path_zpool_history | grep -v $syspool_name | cut -f 1 -d ".") 
    
        awk {'print $1"\t" $2"\t"$3'} $path_zpool_list | grep -v $syspool_name >> $outfile
        echo  "Created $pool_create_date" >> $outfile
        echo  >> $outfile
    # TODO sed instead of perl    vdev_count_mirror=$(sed -n '/\$poolpresent/,/\(^$\|logs\|spares\|cache\)/p' $path_zpool_status | grep c[0-9] | wc -l)
    # TODO also I think we fall on the $syspool_name vdevs with the mirror test
        if [[ -e $path_echo_spa_c_mdb_k ]]; then
            vdev_count_mirror=$(perl -00ne 'if ($_ =~ /$poolpresent/) {chomp($_); printf "%s\n",$_}' $path_echo_spa_c_mdb_k | grep "mirror" |wc -l)
            vdev_count_raidz=$(perl -00ne 'if ($_ =~ /$poolpresent/) {chomp($_); printf "%s\n",$_}' $path_echo_spa_c_mdb_k | grep "raidz" |wc -l)
        else 
            echo  "* Very old version of Collector, no ::spa output." >> $outfile
        fi
        if [[ $vdev_count_mirror -gt "0" && $vdev_count_raidz -gt "0" ]]; then
            echo  "* There are both RAIDZ and mirrored vdevs!" >> $outfile
        fi
        if [[ $vdev_count_mirror -gt "0" ]]; then 
            echo  "* $vdev_count_mirror mirrored vdevs" >> $outfile
        fi
        if [[ $vdev_count_raidz -gt "0" ]]; then 
            echo  "* $vdev_count_raidz raidz vdevs" >> $outfile
        fi
        zil=$(sed -n '/logs/,/\(^$\|spares\|cache\)/p' $path_zpool_status | grep c[0-9] | awk '{print $1}')
        zil_present=$(sed -n '/logs/,/\(^$\|spares\|cache\)/p' $path_zpool_status | grep c[0-9] | awk '{print $1}' | wc -l)
        zil_present_mirror=$(sed -n '/logs/,/\(^$\|spares\|cache\)/p' $path_zpool_status | grep mirror | wc -l)
        if [[ $zil_present =~ ^\d*[02468]$ ]]; then
            echo  "* $zil_present log drives in $zil_present_mirror mirrors" >> $outfile
        elif [[ $zil_present -eq "1" ]]; then
            echo  "*$C_RED Severe WARNING! Un-mirrored ZIL present!$C_RESET See: NEX-2940, NEX-4523" >> $outfile
        else 
            echo  "* no ZIL present" >> $outfile
        fi
        # TODO we're mis-determining cache vs. mirror drives /home/support/ingested/2016-10-04/collector-G048-8800EC1011-5G3IE689J-CEKBID_san02_2016-10-04.11-20-35MDT
        # 
        cache=$(sed -n '/cache/,/\(^$\|spares\)/p' $path_zpool_status | grep c[0-9] | awk '{print $1}')
        cache_present=$(sed -n '/logs/,/\(^$\|spares\|cache\)/p' $path_zpool_status | grep c[0-9] | awk '{print $1}' | wc -l)
        if [[ $cache_present -gt "0" ]]; then
            echo  "* $cache_present cache drives" >> $outfile
        fi
        bad_hb=""
        hb_disks_to_check="$zil $cache"
        for i in $hb_disks_to_check; do
            hb_true=$(grep $i $path_rsfcli_i0_stat)
            if [[ $hb_true ]]; then
                bad_hb="$bad_hb $i"
            fi
            hb_true=""
        done
        if [[ $bad_hb ]]; then
            echo  "" >> $outfile
            echo  -e "*$C_RED Severe warning!$C_RESET The following disks are configured as HA heartbeat disks and are ZIL/cache devices." >> $outfile
            echo  "  $bad_hb" >> $outfile
        fi
    else
        echo  "NOTE: no data pools currently imported!" >> $outfile
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
