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
# Task: general workload summarization of services and client connectivity for CIFS
    pool_smb=$(grep sharesmb $path_zfs_get_all | grep -v "sharesmb *off" | grep -v syspool | wc -l)
    if [[ $pool_smb -gt 0 ]]; then 
        printf  " * SMB filesystems: $pool_smb\n" >> $outfile
        smb_workers_cur=$(grep smb_workers $path_echo_taskq_mdb_k  | awk {'print $3'} | cut -f 1 -d "/")
        smb_workers_hwat=$(grep smb_workers $path_echo_taskq_mdb_k  | awk {'print $4'})
        smb_workers_max=$(grep max_workers $path_sharectl_get_smb | cut -f 2 -d "=")
        printf  "\t * $smb_workers_cur current SMB workers \n" >> $outfile
        printf  "\t * $smb_workers_hwat high water SMB workers \n" >> $outfile
        if [[ "$smb_workers_hwat" -gt "$smb_workers_max" ]]; then
            printf  "\t * $smb_workers_hwat exceeds configured dynamic maximum server availability, consider adjusting." >> $outfile
        elif [[ $smb_workers_cur -gt $(echo "scale=3;$smb_workers_max * 0.8" | bc | sed -e 's/\..*//')  ]]; then
            printf  "\t * $smb_workers_cur/$smb_workers_max configured dynamic workers in use, consider increasing smb_workers.\n" >> $outfile
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
