#!/usr/bin/env bash

# Author: andrew.galloway@nexenta.com - contact with questions

# This script is designed to be run by cron on a regular basis. It has locking to keep it from overrunning
# itself if called by cron again before finishing a prior run. This script monitors the upload directory
# for Collector tarballs and migrates them from there to the working directory for Support, untarring them
# in the process. It adds a file to untarred Collector bundles for tracking purposes, letting other
# scripts know the newly untarred bundle has just arrived.

# modify these only if you know why
UPLOAD_DIR=/mnt/mercury/upload/caselogs
WORKING_DIR=/mnt/mercury/working
ARCHIVE_DIR=/mnt/mercury/archive
LOCK_FILE=/tmp/.initial-ingestor.lock
LOG_FILE=/var/log/initial-ingestor.log

# set up functions
log () {
    echo "`date`|$1" > $LOG_FILE
}

# verify prior run isn't still ongoing, if lock file exists just die silently
if [ -e $LOCK_FILE ]; then
    log "unable to run, lock file exists"
    exit 1
else
    echo "`date`" > $LOCK_FILE
fi

# get list of potentially finished collector uploads in upload directory
for MD5_FILE in `ls -1 ${UPLOAD_DIR}*.md5`; do
    # pre-set some variables we'll need
    TAR_FILE=`echo ${MD5_FILE} | sed -e 's/.md5$//g'`
    UNTAR_DIR=`echo ${TAR_FILE} | sed -e 's/.tar.gz$//g'`
    # we use the date from the bundle to prevent confusion - it is possible that due to timezone
    # differences or misconfiguration on appliance box that the date does not match this server's
    # date, and while we could just use this server's date, it would make locating the tarball
    # more difficult - by using the tarball's date, we make it easier for humans to locate
    # the tarball if they know its filename (which they almost always should)
    TAR_DATE=`echo ${UNTAR_DIR} | awk -F'_' '{printf $NF}' | sed 's/[^0-9.-]//g' | awk -F'.' '{printf $1}'`

    # calculate the md5sums
    GIVEN_MD5=`head -1 ${MD5_FILE} | awk '{printf $1}'`
    PROVEN_MD5=`md5sum ${TAR_FILE} | awk '{printf $1}'`

    if [ "$GIVEN_MD5" == "$PROVEN_MD5" ]; then
        # the md5sums match, so this file has uploaded completely and correctly, we
        # won't bother noting later if it doesn't because it is expected that if the
        # file is still uploading or such that these may not match

        # first, make sure target date directories exists (probably does)
        mkdir ${ARCHIVE_DIR}/${TAR_DATE}
        mkdir ${WORKING_DIR}/${TAR_DATE}

        # copy to the archive location 
        cp ${TAR_FILE} ${ARCHIVE_DIR}/${TAR_DATE}/

        # move to the working location
        mv ${TAR_FILE} ${WORKING_DIR}/${TAR_DATE}/

        # untar in the working location
        cd ${WORKING_DIR}/${TAR_DATE}/ && tar -x --strip=1 -f ${TAR_FILE}

        if [ $? > 0 ]; then
            # something went wrong
            log "some sort of failure untarring ${TAR_FILE}"
            exit 1
        else
            # success!
            # create a file that indicates this is a fresh untar
            echo "`date`" > ${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR}/.just_ingested
            log "untarred ${TAR_FILE}|${WORKING_DIR}/${TAR_DATE}/"
        fi
    fi
done
