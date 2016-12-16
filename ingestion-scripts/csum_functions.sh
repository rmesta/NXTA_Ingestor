#!/usr/bin/env bash
# functions for csummary
# 2016-11-01 - Benjamin Hodgens - initial 
# PERF related
# a weight of 20 makes no assumptions about issues; and TODO or higher is "go ahead and run Sparta".
# We subtract when issues are encountered which need to be resolved prior to running Sparta, printing results at the end
# array of strings/checklist of perf analysis prereqs to be printed at the end
# NOTE, we should be able to just 'source' this to use it from bash if we don't mess it up

# 'output' function for ingestor scripts (and ingestor debugging). Be sure to define DEBUG and/or SQUELCH in your script(s)
# DEBUG=1 # global/defaults - modify at risk
# SQUELCH=0 # for running automatically, and not outputting anything - probably not desirable

# NXTA_INGESTOR is defined in .nxrc of the root of the ingestor tool directory
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }

function output () {
	if [[ $DEBUG == "1" ]]; then
		echo "$1" 	
    elif [[ -o $outfile ]]; then # TODO implement this into the various scripts instead of "echo"
        echo "$1" &> $outfile
    elif [[ $SQUELCH == "1" ]]; then
        echo "$1" > /dev/null
    elif [[ -o $1 && -o $2 && $1 == "debug" ]]; then
        echo "$0 LOG: $1 ln ${BASH_LINENO[*]}"
    else
        echo $0: ERROR: please define output type.
        exit
    fi
}
function debug () { 
	output debug "$2"
}

# add a PERF req
perf_pre=('')
function perf_req() {
    # perf_pre=("${perf_pre[@]}" "$1") # old pre-ingestor way
	echo $1 >> "${BUNDLE_DIR}/ingestor/checks/A9999-perf_req.out"
}
#pweight="20"
SCRIPT_BASE="$NXTA_INGESTOR/ingestion-scripts"
#SCRIPT_BASE="/home/bhodgens/scripts"
PATH=$PATH:$SCRIPT_BASE:$SCRIPT_BASE/subscripts
BUNDLE_DIR=$1
my_pwd=$1

# Color (from ingestor)
C_UND=$(tput sgr 0 1)
C_RESET=$(tput sgr0)
C_BOLD=$(tput bold)
C_RED=$(tput setaf 1)
C_GREEN=$(tput setaf 2)
C_YELLOW=$(tput setaf 3)
C_BLUE=$(tput bold;tput setaf 4)
C_MAGENTA=$(tput setaf 5)
C_CYAN=$(tput setaf 6)
C_WHITE=$(tput setaf 7)

# NULL def for unavailable data files 
NULL="NULL" # TODO this variable should perhaps instead be an error redirected to stderr

# input: date of license expiration, human readable string
# output: a warning, if we're due a renewal
license_countdown () { 
    month_secs=2628000 # roughly how many seconds are in a month
    lic_epoch=$(date --date="$1" +%s)
    lic_tleft=$(echo "$lic_epoch - $(date +%s)" | bc )
    if [[ $lic_tleft -lt "0" ]]; then
        echo  "***$C_UND ALL STOP:$C_RESET This license $C_RED expired already$C_RESET at $1!" >> $outfile
        echo  >> $outfile
        echo  "  Hostname: $my_hostname" >> $outfile
        echo  "  License: $my_license" >> $outfile
        echo  "  Appliance: $appl_version" >> $outfile
        echo  >> $outfile
        echo  "  - Please address with TAM as to whether this is a special case." >> $outfile
        if [[ $mgmt_override != "yes" ]]; then
            exit            
        fi
    elif [[ $lic_tleft -lt $month_secs ]]; then
        echo  "***$C_RED DANGER!$C_RESET License expires in $(date --date="$lic_tleft" +%d) days on $(date --date="$1" +%u) " >> $outfile
        echo  "      - Alert customer appliance management will become inoperable." >> $outfile
    elif [[ $lic_tleft -lt $(echo "$month_secs * 2" | bc ) ]]; then
        echo  "* WARNING:$C_YELLOW license will expire in the next two months:$C_RESET $1" >> $outfile
    else
        echo  "* License expiration: $1" >> $outfile
    fi
}
col_version () {
    if [[ -f $BUNDLE_DIR/collector.stats ]]; then 
        version_collector=$(grep "^Collector" $BUNDLE_DIR/collector.stats | cut -f 2 -d "(" | cut -f 1 -d ")")
    elif [[ -f $BUNDLE_DIR/bundle.log ]]; then
        echo  "This is a Bundle for NexentaStor 5" >> $outfile
        version_collector=""
    else
        echo  "This isn't a valid Collector!" >> $outfile
        exit
    fi
    case $version_collector in
        # As of 2016-06-28, current version is 1.5.3
        1.5.[3-5])
        #    echo "Collector ($version_collector) is current."
        ;;
        1.5.[0-2])
            out="Collector ($version_collector) is (slightly)$C_YELLOW out of date$C_RESET. Please upgrade."
        ;;
        1.[1-2].[0-0])
            out="WARNING: Holy bats, cowman.$C_RED Upgrade the Collector $C_RESET (from stock $version_collector)!"
        ;;
        *) 
            if [[ -x $collector_version ]]; then
                out="WARNING: Collector ($version_collector) is$_RED SIGNIFICANTLY out of date$C_RESET . Please upgrade!"
            fi
        ;;
    esac
    echo  $out >> $outfile
}
appl_version="NULL"
get_appl_version () { 
    if [[ -f "$BUNDLE_DIR/collector.stats" ]]; then
        appl_version=$(grep ^"Appliance version" $BUNDLE_DIR/collector.stats | cut -f 2 -d "(" | cut -f 1 -d ")" | sed -e 's/v//')
    elif [[ -f "$BUNDLE_DIR/bundle.json" ]]; then # TODO assume for now 
        appl_version="5.0"
#        echo  "NexentaStor 5.x bundle detected. Functionality is limited." >> $outfile
    fi
}
# ---------------------------
# determine whether collector or bundle 
# per-format reusable and file path definitions go here!
# need a variable definition for every filetype in either collector.conf (3,4) or collector.json (5)
filename_init () {
    case $1 in 
        collector)
        ctype="collector"

        path_messages="$BUNDLE_DIR/kernel/messages"
        path_modparams="$BUNDLE_DIR/kernel/modparams.out"
        path_system="$BUNDLE_DIR/kernel/system"
        path_prtconf_v="$BUNDLE_DIR/pci_devices/prtconf-v.out"
        path_prtconf_v_stats="$BUNDLE_DIR/pci_devices/prtconf-v.stats"
        path_zfs_get_all="$BUNDLE_DIR/zfs/zfs-get-p-all.out"
        path_zpool_list="$BUNDLE_DIR/zfs/zpool-list-o-all.out"
        path_zpool_status="$BUNDLE_DIR/zfs/zpool-status-dv.out"
        path_zpool_history="$BUNDLE_DIR/zfs/zpool-history-il.out"
        path_echo_spa_c_mdb_k="$BUNDLE_DIR/zfs/echo-spa-c-mdb-k.out"
        path_kstat="$BUNDLE_DIR/kernel/kstat-p-td-10-6.out"
        path_autosaclog="$BUNDLE_DIR/go-live/nexenta-autosac.log"
        path_hddisco="$BUNDLE_DIR/disk/hddisco.out"
        path_iostat_en="$BUNDLE_DIR/disk/iostat-en.out"
        path_sasinfo_hba_v="$BUNDLE_DIR/hbas/sasinfo-hba-v.out"
        path_sasinfo_expander_tv="$BUNDLE_DIR/hbas/sasinfo-expander-tv.out"
        path_pkglist="$BUNDLE_DIR/system/dpkg-l.out"
        path_fcinfo_hba_port_l="$BUNDLE_DIR/hbas/fcinfo-hba-port-l.out"
        path_sesctl_enclosure="$BUNDLE_DIR/enclosures/sesctl-enclosure.out"
        path_echo_arc_mdb="$BUNDLE_DIR/zfs/echo-arc-mdb-k.out"
        path_sharectlgetnfs="$BUNDLE_DIR/nfs/sharectl-get-nfs.out"
        path_showmount_a_e="$BUNDLE_DIR/nfs/showmount-a-e.out"
        path_nfsstat_s="$BUNDLE_DIR/nfs/nfsstat-s.out"
		path_rsfcli_i0_stat="$BUNDLE_DIR/plugins/opthacrsf-1binrsfcli-i0-stat.out"
        path_svcs_a="$BUNDLE_DIR/services/svcs-a.out"
        path_ptree_a="$BUNDLE_DIR/system/ptree-a.out"
        path_ifconfig_a="$BUNDLE_DIR/network/ifconfig-a.out"
        path_appl_replication="$BUNDLE_DIR/services/nmc-c-show-auto-sync-v.out"
        path_fmdump_evt_nday="$BUNDLE_DIR/fma/fmdump-evt-30day.out.gz"
        path_fmdump_evt_nday_stats="$BUNDLE_DIR/fma/fmdump-evt-30day.stats"
        path_echo_taskq_mdb_k="$BUNDLE_DIR/appliance/echo-taskq-mdb-k.out"
        path_stmfadm_list_target_v="$BUNDLE_DIR/comstar/stmfadm-list-target-v.out"
        path_sbdadm_list_lu="$BUNDLE_DIR/comstar/sbdadm-list-lu.out"
        path_sasinfo_hba_v="$BUNDLE_DIR/hbas/sasinfo-hba-v.out"
        path_sharectl_get_smb="cifs/sharectl-get-smb.out"
        path_fmadm_faulty="$BUNDLE_DIR/fma/fmadm-faulty.out"
        path_stmfadm_list_lu_v="$BUNDLE_DIR/comstar/stmfadm-list-lu-v.out"
        path_appliance_runners="$BUNDLE_DIR/appliance/nmc-c-show-appliance-runners.out"
        path_stmfadm_list_state="$BUNDLE_DIR/comstar/stmfadm-list-state.out"
        path_retire_store="$BUNDLE_DIR/fma/retire_store"
        path_lun_smartstat="$BUNDLE_DIR/disk/nmc-c-show-lun-smartstat.out"
        path_dladm_show_phys="$BUNDLE_DIR/network/dladm-show-phys.out"
        ;;
        bundle)
        ctype="bundle"
        path_messages="$BUNDLE_DIR/rootDir/var/adm/messages"
        path_modparams="$BUNDLE_DIR/kernel/modparams.out"
        path_system="$BUNDLE_DIR/rootDir/etc/system"
        path_prtconf_v="$BUNDLE_DIR/pci_devices/prtconf-v.out"
        path_prtconf_v_stats="$NULL"
        path_zfs_get_all="$BUNDLE_DIR/zfs/zfs_get-p_all.out"
        path_zpool_list="$BUNDLE_DIR/zfs/zpool_list-o_all.out"
        path_zpool_status="$BUNDLE_DIR/zfs/zpool_status-Dv.out"
        path_zpool_history="$BUNDLE_DIR/zfs/zpool_history-il.out"
        path_echo_spa_c_mdb_k="$BUNDLE_DIR/zfs/mdb-spa-c.out"
        path_kstat="$BUNDLE_DIR/kernel/kstat-p-Td.out"
        path_autosaclog="$BUNDLE_DIR/system/nexenta-autosac.log"
        path_hddisco="$NULL"
        path_iostat_en="$BUNDLE_DIR/disk/iostat-En.out"
        path_sasinfo_hba_v="$NULL"
        path_sasinfo_expander_tv="$NULL"
        path_pkglist="$BUNDLE_DIR/system/pkg_list.out"
        path_fcinfo_hba_port_l="$BUNDLE_DIR/hbas/fcinfo_hba-port-l.out"
        path_sesctl_enclosure="$NULL"
        path_echo_arc_mdb="$BUNDLE_DIR/zfs/mdb-arc.out"
        path_sharectlgetnfs="$BUNDLE_DIR/nfs/sharectl_get_nfs.out"
        path_showmount_a_e="$BUNDLE_DIR/nfs/showmount-a-e.out"
        path_nfsstat_s="$BUNDLE_DIR/nfs/nfsstat-s.out"
        path_rsfcli_i0_stat="$BUNDLE_DIR/ha/opt_HAC_RSF-1_bin_rsfcli-i0_stat.out"
        path_svcs_a="$BUNDLE_DIR/services/svcs-a.out"
        path_ptree_a="$BUNDLE_DIR/system/ptree-a.out"
        path_ifconfig_a="$BUNDLE_DIR/network/ifconfig-a.out"
        path_appl_replication="$BUNDLE_DIR/analytics/hprStats.json" # v5 exclusive
        path_fmdump_evt_nday="$BUNDLE_DIR/fma/fmdump-eVt_30day.out"
        path_fmdump_evt_nday_stats="$NULL"
        path_echo_taskq_mdb_k="$BUNDLE_DIR/kernel/mdb-taskq.out"
        path_stmfadm_list_target_v="$BUNDLE_DIR/comstar/stmfadm_list-target-v.out"
        path_sbdadm_list_lu="$BUNDLE_DIR/comstar/sbdadm_list-lu.out"
        path_sasinfo_hba_v="$NULL"
        path_nefclient_sas_select="$BUNDLE_DIR/disk/nefclient-sas_select.json" # v5 exclusive, all sasinfo stuff? 
        path_sharectl_get_smb="$BUNDLE_DIR/cifs/sharectl_get_smb.out"
        path_fmadm_faulty="$BUNDLE_DIR/fma/fmadm_faulty.out"
        path_stmfadm_list_lu_v="$NULL"
        path_appliance_runners="$BUNDLE_DIR/nef/workers.json"
        path_stmfadm_list_state="$NULL"
        path_retire_store="$NULL"
        path_lun_smartstat="$NULL"
        path_dladm_show_phys="$BUNDLE_DIR/network/dladm_show-phys.out"
        ;;
    esac 
}
# ==== actual stuff here ==== #
col_version
get_appl_version # TODO rewrite these perhaps
#echo "appl_version $appl_version"
case $appl_version in
    5.*)
        echo  "Hey look, version 5.0." >> $outfile
        filename_init "bundle"
        echo  "*** Note: diagnostic ability is limited due to Bundle format." >> $outfile
        my_license_features=$(python -m json.tool $BUNDLE_DIR/nef/license.json | sed -e "1,/features/d" -e '/\}/,$d' -e 's/\"//g')
        license_expire=$(python -m json.tool $BUNDLE_DIR/nef/license.json | grep ends | cut -f 4 -d \")
        my_license_type="" # needed for other node detection, perhaps not needed here
        my_hostname=$( cat $BUNDLE_DIR/system/hostname.out )
        my_domain=$( cat $BUNDLE_DIR/network/domainname.out )
        my_date=$(python -m json.tool bundle.json | grep created | cut -f 4 -d \")
        arc_meta_used=$(grep 'arc_meta_used' $path_echo_arc_mdb)
        arc_meta_limit=$(grep 'arc_meta_limit' $path_echo_arc_mdb)
        arc_meta_max=$(grep 'arc_meta_max' $path_echo_arc_mdb)
        uptime=$(cat system/uptime.out)
        col_terminated="$NULL"
		syspool_name="rpool"
		dumpd=$(grep -e '^DUMPADM_DEVICE' rootDir/etc/dumpadm.conf)
    ;;
    "4.0.4"*|"3.1.6"*|"4.0.5"*) 
        if [[ -x $version_collector ]]; then
            echo  "Unable to identify bundle/collector, exiting but defining static variables." >> $outfile
            exit
        fi
        filename_init "collector"
        # other variables we have defined historically 
        my_license=$(grep "^License key" $BUNDLE_DIR/collector.stats | awk '{print $3}') # TODO check to see if this is a valid license for a supported system?
        my_license_type=$(echo $my_license | awk -F- '{print $1}') # only used for finding other node bundle
        license_expire=$($SCRIPT_BASE/subscripts/keycheck.pl $(echo $my_license) | cut -f 2,3,4 -d ":")
        # TODO may also need to do something here about hostname case, it appears to differ shomehow between Collectors and filenames, and between hosts
        my_hostname=$(grep ^Host $BUNDLE_DIR/collector.stats | awk '{print $2}' | sed 's/.*/\L&/' )
        my_domain=$(cat $BUNDLE_DIR/nfs/domainname.out) # TODO this may be incorrect for non-NFS installs
        my_date=$(echo $my_pwd | awk -F_ '{print $3}' | sed -e 's/\(20[0-9]\{2\}-[0-1][0-9]-[0-3][0-9]\).*/\1/') # TODO my_date appears to sometimes be wrong on old Collectors
        arc_meta_used=$(grep 'arc_meta_used' $BUNDLE_DIR/zfs/echo-arc-mdb-k.out)
        arc_meta_limit=$(grep 'arc_meta_limit' $BUNDLE_DIR/zfs/echo-arc-mdb-k.out)
        arc_meta_max=$(grep 'arc_meta_max' $BUNDLE_DIR/zfs/echo-arc-mdb-k.out)
        arc_meta_used_num=$(echo $arc_meta_used | awk '{print $3}')
        arc_meta_limit_num=$(echo $arc_meta_limit| awk '{print $3}')
        arc_meta_max_num=$(echo $arc_meta_max | awk '{print $3}')
        uptime=$(cat $BUNDLE_DIR/system/uptime.out)
        dumpd=$(grep -e '^DUMPADM_DEVICE' $BUNDLE_DIR/kernel/dumpadm.conf)
        col_terminated=$(grep -H terminated $BUNDLE_DIR/*/*.stats | grep -v smbstat | wc -l)
		syspool_name="syspool"
        ;;
    *)
        echo  "Something went sideways with appliance version detection: appl_version $appl_version" >> $outfile
        exit
    ;;
esac



# misc variables, hopefully universal but we shall see won't we?
arc_meta_used_num=$(echo $arc_meta_used | awk '{print $3}')
arc_meta_limit_num=$(echo $arc_meta_limit| awk '{print $3}')
arc_meta_max_num=$(echo $arc_meta_max | awk '{print $3}')
mpt_sas_patch=$(grep driver-storage-mpt-sas $path_pkglist | awk '{print $3}' | awk -F. '{print $2}')

















