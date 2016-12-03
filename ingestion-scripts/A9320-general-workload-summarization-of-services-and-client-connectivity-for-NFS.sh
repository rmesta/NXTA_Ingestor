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
# Task: general workload summarization of services and client connectivity for NFS
    # nfs checks
    pool_nfs=$(grep sharenfs $path_zfs_get_all | grep -v "sharenfs *off" | grep -v syspool | wc -l)
    if [[ $pool_nfs -gt 0 ]]; then
        echo  >> $outfile
        echo  " * NFS filesystems: $pool_nfs" >> $outfile
        nfsshares=$(grep -v "export" $path_showmount_a_e | cut -f 1 -d :  | sort | uniq | grep -v "/" | wc -l)
    #    nfsshares=$(grep -v "export" $path_showmount_a_e | cut -f 2 -d :  | sort | uniq -c | grep -v "/" | wc -l)
        nfs_servers=$(grep ^servers= $path_sharectlgetnfs | cut -f 2 -d =)
        nfs_lockd=$(grep ^lockd_servers= $path_sharectlgetnfs | cut -f 2 -d =)
        nfsmaxver=$(grep server_versmax $path_sharectlgetnfs | cut -f 2 -d =)
        nfs4calls=$(grep -A2 "Server NFSv4" $path_nfsstat_s | grep ^[0-9] | awk {'print $1'})
        nfs4_delegation=$(grep server_delegation $path_sharectlgetnfs)
        printf  "\t* Unique NFSv3 clients connected (does not include v4): $nfsshares\n" >> $outfile
        printf  "\t* nfs servers=$nfs_servers\n" >> $outfile
        printf  "\t* lockd_servers=$nfs_lockd\n" >> $outfile
        if [[ ($nfsmaxver -eq "4") && ($nfs4calls -gt "0") ]]; then
            printf  "\t* Caution: NFSv4 enabled and in use: $nfs4calls total NFSv4 calls.\n" >> $outfile
            if [[ $nfs4_delegation -eq "nfs_delegation=on" ]]; then
                printf  "\t* NFSv4 delegation is enabled (OK in most situations).\n" >> $outfile
            else
                printf  "\t* NFSv4 delegation is disabled.\n" >> $outfile
            fi
        fi
        if [[ $(grep rpcmod $path_system) ]] ; then
            printf  "\t* rpcmod /etc/system entries present.\n" >> $outfile
        fi
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
