#!/usr/bin/env bash

# Author: andrew.galloway@nexenta.com - contact with questions

# This script is designed to be run by cron on a regular basis. It has locking to keep it from overrunning
# itself if called by cron again before finishing a prior run. This script monitors the upload directory
# for Collector tarballs and migrates them from there to the working directory for Support, untarring them
# in the process. It adds a file to untarred Collector bundles for tracking purposes, letting other
# scripts know the newly untarred bundle has just arrived.

# modify these only if you know why
UPLOAD_DIR=/mnt/carbon-steel/upload/caselogs/
WORKING_DIR=/mnt/carbon-steel/ingested/
SYMLINK_DIR=/mnt/carbon-steel/ingested/links/
ARCHIVE_DIR=/mnt/carbon-steel/collector_archive/
LOCK_FILE=/tmp/.initial-ingestor.lock
LOG_FILE=/var/log/initial-ingestor.log
FOWNER=ftp
FGROUP=nexentians

CMDARGS=$1

# set up functions
log () {
    echo "`date`|$1" >> $LOG_FILE
}

# only do this if not calling with specific tarball
if [[ "$CMDARGS" == "md5" ]]; then
    # verify prior run isn't still ongoing, if lock file exists just die silently
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
       # lock file doesn't exist, yay, make it and throw our pid in it
       echo -n "$$" > $LOCK_FILE
    fi
fi

# directory globals existence checks
if [ ! -d "${UPLOAD_DIR}" ]; then
    log "upload directory (${UPLOAD_DIR}) nonexistent, dying"
    rm -f ${LOCK_FILE}
    exit 1
fi

if [ ! -d "${ARCHIVE_DIR}" ]; then
    log "archive directory (${ARCHIVE_DIR}) nonexistent, dying"
    rm -f ${LOCK_FILE}
    exit 1
fi

if [ ! -d "${WORKING_DIR}" ]; then
    log "working driectory (${WORKING_DIR}) nonexistent, dying"
    rm -f ${LOCK_FILE}
    exit 1
fi

# meh, if symlink dir doesn't exist by this point, just make the damn thing
mkdir -p ${SYMLINK_DIR} >/dev/null 2>&1

ingest() {
    FP_TAR_FILE=$1
    CE_PREFIX=""

    if [[ "${FP_TAR_FILE}" == *EVAL* ]]; then
        # we have a CE tarball, stick it in Community edition dir
        CE_PREFIX="community/"
    fi

    TAR_FILE=`basename ${FP_TAR_FILE}`

    tar -tvzf ${FP_TAR_FILE} | head -n1 | awk '{print $6}' | grpe 'var\/tmp\/c' > /dev/null
    rc=$?

    if [ $rc -eq 0 ]; then
        UNTAR_DIR=`tar -tvf ${FP_TAR_FILE} | head -n1 | awk '{print $6}' | awk -F'/' '{print $3}'`
    else
        UNTAR_DIR=`tar -tvf ${FP_TAR_FILE} | tail -n1 | awk '{print $6}' | awk -F'/' '{print $2}'`
    fi

    # we use the date from the bundle to prevent confusion - it is possible that due to timezone
    # differences or misconfiguration on appliance box that the date does not match this server's
    # date, and while we could just use this server's date, it would make locating the tarball
    # more difficult - by using the tarball's date, we make it easier for humans to locate
    # the tarball if they know its filename (which they almost always should)
    TAR_DATE=`echo ${UNTAR_DIR} | awk -F'_' '{printf $NF}' | sed 's/[^0-9.-]//g' | awk -F'.' '{printf $1}'`

    # first, make sure target date directories exists (probably does)
    mkdir ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE} >/dev/null 2>&1
    chown ${FOWNER}:${FGROUP} ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE} >/dev/null 2>&1

    if [[ "${FP_TAR_FILE}" != *EVAL* ]]; then
        mkdir ${WORKING_DIR}/${TAR_DATE} >/dev/null 2>&1
        chown ${FOWNER}:${FGROUP} ${ARCHIVE_DIR}/${TAR_DATE} >/dev/null 2>&1
    fi

    # move to the archive location 
    mv ${FP_TAR_FILE} ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/

    if [ $? -gt 0 ]; then
        log "some sort of failure moving ${TAR_FILE} to archive"
        continue
    fi

    chmod 660 ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE} >/dev/null 2>&1
    # untar in the working location, if not eval

    if [[ "${FP_TAR_FILE}" != *EVAL* ]]; then
        NUM_STRIP=1

        tar -tzvf ${ARCHIVE_DIR}/${TAR_DATE}/${TAR_FILE} | head -n1 | grep 'var\/tmp\/c' > /dev/null
        rc=$?

        if [ $rc -eq 0 ] ; then
            NUM_STRIP=2
        fi

        cd ${WORKING_DIR}/${TAR_DATE}/ && tar -x --strip=${NUM_STRIP} -f ${ARCHIVE_DIR}/${TAR_DATE}/${TAR_FILE}

        if [ $? -gt 0 ]; then
            # something went wrong
            log "some sort of failure untarring ${ARCHIVE_DIR}/${TAR_DATE}/${TAR_FILE} to ${WORKING_DIR}/${TAR_DATE}/"
            continue
        else
            # success!
            # create a file that indicates this is a fresh untar
            echo "`date`" > ${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR}/.just_ingested
             chown -R ${FOWNER}:${FGROUP} ${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR} >/dev/null 2>&1
             log "untarred|${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR}"
            # symlink to a symlink dir, making it easier to find, maybe
            ln -s ${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR} ${SYMLINK_DIR}
        fi
    fi
}

if [[ $CMDARGS == "md5" ]]; then
    # get list of potentially finished collector uploads in upload directory
    # the 2013_2014 is dirty
    for MD5_FILE in `ls -1 ${UPLOAD_DIR}*.md5 | grep collector- | grep '_2011-\|_2012-\|_2013-\|_2014-\|_2015-\|_2016-\|_2017-\|_2018-'`; do
        # pre-set some variables we'll need
        FOUND_FP_TAR_FILE=`echo ${MD5_FILE} | sed -e 's/.md5$//g'`

        # calculate the md5sums
        GIVEN_MD5=`head -1 ${MD5_FILE} | awk '{printf $1}'`
        PROVEN_MD5=`md5sum ${FOUND_FP_TAR_FILE} | awk '{printf $1}'` 2>/dev/null

        if [ "$GIVEN_MD5" == "$PROVEN_MD5" ]; then
            ingest ${FOUND_FP_TAR_FILE}
            rm -f ${MD5_FILE}
        fi
    done
else
    if [ -f "$1" ]; then
        GIVEN_FP_TAR=$1
        ingest ${GIVEN_FP_TAR}
    fi
fi

rm -f ${LOCK_FILE}
