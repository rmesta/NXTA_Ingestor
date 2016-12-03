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
# Task: verify cluster state is operational and we have data from both nodes
    echo  >> $outfile
    echo  "$C_BLUE=== HA Cluster State ===$C_RESET" >> $outfile
	# WARNING: we have to have a decompressed 
    cluster_state=$(grep configured $path_rsfcli_i0_stat)
    if [[ $cluster_state && $ctype = "collector" ]]; then
        echo  "ctype is $ctype" >> $outfile
        if [[ $(echo $cluster_state | awk '{print $1}') -gt 1 ]]; then
            printf  "$cluster_state\n" >> $outfile
            echo  >> $outfile
            echo  "Checking for recent other-node Collector..."  >> $outfile
            # listcol only checks the first 10 matches.
            chost_rsf_service_name=$(grep "^0 Service" $path_rsfcli_i0_stat | awk '{print $3}' | sed -s 's/,//')
            
            chost_other=$(grep Host $path_rsfcli_i0_stat |  awk {'print $2'} | sed 's/.*/\L&/' | sed "/^$my_hostname$/d")
            chost_other_col_list=$($SCRIPT_BASE/subscripts/listcol -c=collector-${my_license_type}.*${chost_other} -t=5)
			path_rsfcli_base=$(echo $path_rsfcli_i0_stat | sed -s "s!$BUNDLE_DIR!!") 
            for i in $(echo $chost_other_col_list); do
                chost_other_rsf_temp_service_name=$(grep "^0 Service" $i/$path_rsfcli_base | awk '{print $3}' | sed -s 's/,//')
                if [[ "$chost_rsf_service_name" == "$chost_other_rsf_temp_service_name" ]]; then
                    chost_other_rsf_service_name=$chost_other_rsf_temp_service_name
                    chost_other_col=$i
                    break
                fi
            done
            if [[ ! -z $chost_other_col ]]; then
                echo  "Collector for other node $chost_other: " >> $outfile
                echo  $chost_other_col >> $outfile
                echo  >> $outfile
            else 
                echo  "Warning: no Collector found for other node $chost_other ($chost_other_col)" >> $outfile
                echo  >> $outfile
            fi
        else
            echo  >> $outfile
            echo  "*** System is NOT a part of a cluster." >> $outfile
            echo  >> $outfile
        fi
    elif [[ $cluster_state && $ctype = "bundle" ]]; then
        printf  "$cluster_state\n" >> $outfile
        echo  >> $outfile
        echo  "*** Other-node bundle detection not currently possible." >> $outfile
    else 
        echo  >> $outfile
        echo  "*** System is NOT a part of a cluster." >> $outfile
        echo  >> $outfile
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
