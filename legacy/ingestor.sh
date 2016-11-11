#!/usr/bin/env bash

# Author: andrew.galloway@nexenta.com - contact with questions

# this script is expected to be run by cron; it
# won't overrun itself if run while still running
# this script checks for just ingested files

source ../.nxrc
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }

WORKING_DIR=/mnt/carbon-steel/ingested/
LOCK_FILE=/tmp/.ingestor.lock
LOG_FILE=/var/log/ingestor.log
INGESTION_SCRIPTS_DIR=${NXTA_INGESTOR}/ingestion-scripts/
ITER_START=1
ITER_END=10
FOWNER=ftp
FGROUP=nexentians

# log function
log () {
    echo "`date`|$1" >> $LOG_FILE
}

# check if we're already running
if [ -e $LOCK_FILE ]; then

    # check if the pid still exists for the existing lock file
    if ps -p `cat ${LOCK_FILE}` > /dev/null
    then
        # commented out for now to avoid cron-based spam
        # log "unable to run, lock file exists and pid active"
        exit 1
    else
        log "lock file still existed, but no active pid, choosing to run"
        echo -n "$$" > $LOCK_FILE
    fi
else
    echo -n "$$" > $LOCK_FILE
fi

# set up ingest function
ingest() {
    TO_INGEST_DIR=$1
    # this basically runs all the scripts in ingestion-scripts dir, but does so
    # o nly if they start with an A (that way we can disable scripts by renaming, and
    # it runs them in sequential order from 1 to 99 -- and then whatever order ls
    # wants within a specific number combo -- but this should be ok, the only reason
    # for the iteration is for script chains that REQUIRE another script have run
    # first
    log "running|${TO_INGEST_DIR}"

    if [ -d "${TO_INGEST_DIR}/ingestor" ]; then
        rm -rf "${TO_INGEST_DIR}/ingestor" >/dev/null 2>&1
        rm -rf "${TO_INGEST_DIR}/.ingestor_logs" >/dev/null 2>&1
    fi

    for (( ITERATION=$ITER_START; ITERATION<=$ITER_END; ITERATION++ )); do
        cd ${INGESTION_SCRIPTS_DIR}

        for SCRIPT in `ls -1 A${ITERATION}*`; do
            BNAME_SCRIPT=`basename ${SCRIPT}`
            echo "`date`|${SCRIPT}|started" >> ${TO_INGEST_DIR}/.ingestor_activity_log

            mkdir "${TO_INGEST_DIR}/.ingestor_logs" >/dev/null 2>&1

            # ingestion scripts get 1 cmd line arg sent to them - the directory
            # of the bundle they're being run against, we also pipe all
            # stdout and stderr to a file, just for completion sake
            ./${SCRIPT} "${TO_INGEST_DIR}" > ${TO_INGEST_DIR}/.ingestor_logs/${BNAME_SCRIPT}.log 2>&1

            echo "`date`|${SCRIPT}|done|$?" >> ${TO_INGEST_DIR}/.ingestor_activity_log
        done
    done

    chown -R ${FOWNER}:${FGROUP} ${TO_INGEST_DIR} >/dev/null 2>&1
    find ${TO_INGEST_DIR} -type d -print0 | xargs -0 chmod 770
    find ${TO_INGEST_DIR} -type f -print0 | xargs -0 chmod 660

    log "finished|${TO_INGEST_DIR}"
}

# check if ingestor.sh was called with an argument, and if so, use that for the directory to
# run on, and otherwise use a search of the working directory for untouched bundle dirs
if [ -z "$1" ]; then
    for UNTAR_DIR in `ls -1 ${WORKING_DIR}*/*/.just_ingested | sed 's/.just_ingested//g'`; do
        # is this an untouched bundle - if so, do stuff, otherwise just ignore it as finished/started already
        if [ -e ${UNTAR_DIR}/.just_ingested ]; then
            mv ${UNTAR_DIR}/.just_ingested ${UNTAR_DIR}/.initial_ingested_at
            mkdir ${UNTAR_DIR}/.ingestor_logs

            echo `date` > ${UNTAR_DIR}/.ingestor_started

            ingest ${UNTAR_DIR}

            echo `date` > ${UNTAR_DIR}/.ingestor_finished
        fi
    done
else
    # if we're here, someone passed uas an argument, which we will assume is a directory
    if [ -d "$1" ]; then
        if [ -e $1/.just_ingested ]; then
            mv $1/.just_ingested $1/.initial_ingested_at
            mkdir $1/.ingestor_logs

            echo `date` > $1/.ingestor_started
    
            ingest $1

            echo `date` > $1/.ingestor_finished
        else
            # if we're here, there's a directory, but no .just_ingested
            if [ -z "$2" ]; then
                if [ "$2" == "-f" ]; then
                    # if we're here, -f was passed, so we run anyway
                    ingest $1
                else
                    # warn caller there's a problem because .just_ingested didn't exist
                    echo -n "Directory specified appears to have already had ingestor run on it, or the"
                    echo -n " argument passed to us was not a valid collector directory. If the former and"
                    echo -n " you wish to run anyway, you must specify a '-f' as a second argument to"
                    echo " ingestor.sh."
                fi
            fi
        fi
    else
        # $1 was not a directory
        echo "ingestor.sh must be passed a directory as first argument if called with arguments"
    fi
fi

rm -f ${LOCK_FILE}
