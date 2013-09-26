#!/usr/bin/env bash

# Author: andrew.galloway@nexenta.com - contact with questions

# this script is expected to be run by cron, it will not overrun itself if run while still running
# this script checks for just ingested files

WORKING_DIR=/mnt/mercury/working
LOCK_FILE=/tmp/.ingestor.lock
LOG_FILE=/var/log/ingestor.log
INGESTION_SCRIPTS_DIR=./ingestion-scripts
INITIAL_LOG_FILE=/var/log/initial-ingestor.log
ITER_START=1
ITER_END=99

# check if we're already running
if [ -e $LOCK_FILE ]; then

    # check if the pid still exists for the existing lock file
    if ps -p `cat ${LOCK_FILE}` > /dev/null
    then
        log "unable to run, lock file exists and pid active"
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
    # this basically runs all the scripts in ingestion-scripts dir, but does so
    # o nly if they start with an A (that way we can disable scripts by renaming, and
    # it runs them in sequential order from 1 to 99 -- and then whatever order ls
    # wants within a specific number combo -- but this should be ok, the only reason
    # for the iteration is for script chains that REQUIRE another script have run
    # first
    for (( ITERATION=$ITER_START; ITERATION<=$ITER_END; ITERATION++ )); do
        for SCRIPT in `ls -1 ${INGESTION_SCRIPTS_DIR}/A${ITERATION}*`; do
            echo "`date`|${SCRIPT}|started" > $1/.ingestor_activity_log

            # ingestion scripts get 1 cmd line arg sent to them - the directory
            # of the bundle they're being run against
            ./${SCRIPT} "$1"

            echo "`date`|${SCRIPT}|done|$?" > $1/.ingestor_activity_log
        done
    done
}

# check if ingestor.sh was called with an argument, and if so, use that for the directory to
# run on, and otherwise use initial log file - usually initial log file is right
if [ -z "$1" ]; then
    # checks initial ingestor log for last 100 entries, it is safe as it won't re-run on one it has
    # already started on. if somehow more than 100 bundles show up between runs, we would
    # unfortunately miss them - but it is possible to manually invoke this script with a directory
    # name, so there's a workaround there
    for UNTAR_DIR in `tail -n 100 ${INITIAL_LOG_FILE} | grep untarred | awk -F'|' '{printf $3}'`; do
        # is this an untouched bundle - if so, do stuff, otherwise just ignore it as finished/started already
        if [ -e ${UNTAR_DIR}/.just_ingested ]; then
            mv ${UNTAR_DIR}/.just_ingested ${UNTAR_DIR}/.initial_ingested_at
            echo "`date`" > ${UNTAR_DIR}/.ingestor_running

            ingest ${UNTAR_DIR}
        fi
    done
else
    # if we're here, someone passed uas an argument, which we will assume is a directory
    if [ -d "$1" ]; then
        if [ -e $1/.just_ingested ]; then
            mv $1/.just_ingested $1/.initial_ingested_at
            echo "`date`" > $1/.ingestor_running
    
            ingest $1
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
