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
# Task: misc issues
    echo  "$C_BLUE=== Misc. Issues ===$C_RESET" >> $outfile
    
    # Task : verify no mailer errors are occurring
    sendmail_crit=$(grep sendmail $path_messages | grep mail.crit | cut -f 3 -d "]" | tail -n3)
    sendmail_crit_count=$(grep sendmail $path_messages | grep mail.crit | cut -f 3 -d "]" | wc -l)
    if [[ $(echo $sendmail_crit) != "" ]]; then
        echo  "*$C_RED $sendmail_crit_count critical$C_RESET sendmail/mailer failures:" >> $outfile
        printf  "$sendmail_crit" >> $outfile
        echo  "" >> $outfile
    fi
    # Task : check for nocacheflush
    zfs_nocacheflush=$(grep "zfs:zfs_nocacheflush" $path_system)
    if [[ $zfs_nocacheflush != "" ]]; then 
        echo  "*$C_YELLOW zfs_nocacheflush is enabled!$C_RESET This is a potential risk for corruption in the event of power loss, but may be required for certain SSDs." >> $outfile
    fi
    echo  >> $outfile
    # Task : verify c-states are disabled
    CSTATE=0
    for i in $(grep supported_max_cstates $path_kstat | awk '{print $2}'); do
        if [[ $i -gt  1 ]]; then
           if [[ $i -gt $CSTATE ]]; then
               CSTATE=$i
           fi
        fi
    done
    if [[ $CSTATE -gt 0 ]]; then
        echo  >> $outfile
        echo  "* Deep C-STATES are enabled: max_cstate = $CSTATE!" >> $outfile
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
