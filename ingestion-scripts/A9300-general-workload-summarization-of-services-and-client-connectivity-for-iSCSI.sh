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
# Task: general workload summarization of services and client connectivity for iSCSI
    #iscsi checks
    pool_vol=$(grep "type.*volume" $path_zfs_get_all | grep -v $syspool_name | wc -l)
    if [[ $pool_vol -gt 0 ]]; then
        echo  >> $outfile
        echo  " * Block volumes: $pool_vol" >> $outfile
        lu_count=$(grep '/' $path_sbdadm_list_lu | wc -l) 
        if [[ $lu_count -gt "0" ]]; then
            printf  "\t* $lu_count LU configured\n" >> $outfile
        else 
            printf  "\t* NO LU configured\n" >> $outfile
        fi
        initiator_iscsi_count=$(grep Initiator $path_stmfadm_list_target_v | grep -v wwn | sort | uniq -c | wc -l)
        initiator_fc_count=$(grep Initiator $path_stmfadm_list_target_v | grep wwn | sort | uniq -c | wc -l)
        case $initiator_iscsi_count in
        0) 
            printf  "\t* There are no iSCSI initiators configured in hostgroups.\n" >> $outfile
            ;;
        *)
            printf  "\t* Unique iSCSI initiators: $initiator_iscsi_count\n" >> $outfile
            lu_writeback_cnt=$(grep "Writeback.*Enabled" $path_stmfadm_list_lu_v | wc -l)
            if [[ $lu_writeback_cnt > 0 ]]; then
                printf  "\t* WARNING: there are $lu_writeback_cnt LUNs with$C_YELLOW writeback enabled!$C_RESET" >> $outfile
                
            fi
            lu_offlining_cnt=$(grep Offlining $path_stmfadm_list_lu_v | wc -l)
            
            if [[ $lu_offlining_cnt > 0 ]]; then
                printf  "\t* WARNING: there are $lu_offlining_cnt$C_YELLOW LUNs with 'Offlining' status!$C_RESET" >> $outfile
            fi
            ;;
        esac
        if [[ $initiator_fc_count -gt "0" ]] ; then 
            printf  "\t* Unique FC initiators: $initiator_fc_count\n" >> $outfile
        fi
        fc_hba_init=$(grep "Initiator" $path_fcinfo_hba_port_l | sort | uniq -c | wc -l)
        fc_hba_target=$(grep "Target" $path_fcinfo_hba_port_l | sort | uniq -c | wc -l)
        
        if [[ $fc_hba_init -gt "0" ]]; then
            printf  "\t* $fc_hba_init fibrechannel HBA initiator in use.\n" >> $outfile
        fi
        if [[ $fc_hba_target -gt "0" ]]; then
            printf  "\t* $fc_hba_target fibrechannel HBA target in use.\n" >> $outfile
        fi
        aluaenabled=$(grep "ALUA Status" $path_stmfadm_list_state | awk '{print $4}')
        if [[ $aluaenabled == "enabled" && $initiator_iscsi_count -gt 0 ]]; then
            printf  "\t** NEX-3089: WARNING:$C_RED ALUA is enabled, as is iSCSI!$C_RESET These are incompatible." # don't move this, important to have it as a part of iscsi stuff >> $outfile
            echo   >> $outfile
        fi
    else
        echo  "* No block volumes configigured (iSCSI/FC)."   >> $outfile
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
