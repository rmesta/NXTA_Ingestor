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
CHECKTGZ=/root/checktgz.pl
FOWNER=ftp
FGROUP=nexentians

CMDARGS=$1

# set up functions
log () {
    echo "logging: `date`|$1"
    echo "`date`|$1" >> $LOG_FILE
}

function is_collector_bundle()
{
    local IBUNDLE=$1

    echo "running is_collector_bundle() on $IBUNDLE"

    # exists
    if [ -f $IBUNDLE ]; then
        # GPG decryption
        gpg -d ${IBUNDLE} > ${IBUNDLE}.unencrypted
        if [ $? -ne 0 ]; then
            # was not GPG encrypted or we lack the key to decrypt it here, seemingly; remove any crap we may have made
            rm -f ${IBUNDLE}.unencrypted >/dev/null 2>&1
        else
            # we appear to have decrypted it
            mv ${IBUNDLE}.unencrypted ${IBUNDLE} >/dev/null 2>&1
        fi

        if [ ${IBUNDLE: -2} == "z2" ]; then
            # the return code of this will be what the tar command returned
            tar -tjf $IBUNDLE | grep collector.stats >/dev/null 2>&1
            return
        elif [ ${IBUNDLE: -2} == "gz" ]; then
            tar -tzf $IBUNDLE | grep collector.stats >/dev/null 2>&1
            return
        fi
    fi

    return 1
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

    echo "ingest() running on ${FP_TAR_FILE}"

    if [ -z "${FP_TAR_FILE}" ]; then
        echo "failure, FP_TAR_FILE unset"
        return 1
    fi

    if [[ "${FP_TAR_FILE}" == *EVAL* ]]; then
        # we have a CE tarball, stick it in Community edition dir
        CE_PREFIX="community/"
    fi

    TAR_FILE=`basename ${FP_TAR_FILE}`

    echo "determined TAR_FILE to be $TAR_FILE"

    if [ -z "${TAR_FILE}" ]; then
        echo "failure, TAR_FILE unset"
        return 1
    fi

    tar -tvzf ${FP_TAR_FILE} 2>/dev/null | grep collector.stats | head -n1 | awk '{print $6}' | sed 's/^\///' | grep 'var\/tmp\/c' > /dev/null
    if [ $? -gt 0 ]; then
        UNTAR_DIR=`tar -tvzf ${FP_TAR_FILE} 2>/dev/null | head -n1 | awk '{print $6}' | sed 's/^\///' | awk -F'/' '{print $2}'`
    else
        UNTAR_DIR=`tar -tvzf ${FP_TAR_FILE} 2>/dev/null | head -n1 | awk '{print $6}' | sed 's/^\///' | awk -F'/' '{print $3}'`
    fi

    echo "determined UNTAR_DIR to be $UNTAR_DIR"

    if [ -z "${UNTAR_DIR}" ]; then
        echo "couldn't determine, UNTAR_DIR unset"
        return 1
    fi

    # we use the date from the bundle to prevent confusion - it is possible that due to timezone
    # differences or misconfiguration on appliance box that the date does not match this server's
    # date, and while we could just use this server's date, it would make locating the tarball
    # more difficult - by using the tarball's date, we make it easier for humans to locate
    # the tarball if they know its filename (which they almost always should)
    TAR_DATE=`echo ${UNTAR_DIR} | awk -F'_' '{printf $NF}' | sed 's/[^0-9.-]//g' | awk -F'.' '{printf $1}'`

    echo "determined TAR_DATE to be $TAR_DATE"

    if [ -z "${TAR_DATE}" ]; then
        echo "couldn't determine, TAR_DATE unset"
        return 1
    fi

    # first, make sure target date directories exists (probably does)
    mkdir ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE} >/dev/null 2>&1
    chown ${FOWNER}:${FGROUP} ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE} >/dev/null 2>&1

    echo "created ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE} if nonexistent"

    if [[ "${FP_TAR_FILE}" != *EVAL* ]]; then
        mkdir ${WORKING_DIR}/${TAR_DATE} >/dev/null 2>&1
        chown ${FOWNER}:${FGROUP} ${ARCHIVE_DIR}/${TAR_DATE} >/dev/null 2>&1
    fi

    echo "created ${WORKING_DIR}/${TAR_DATE} if nonexistent"

    echo "checking for existing archived tarball"
    if [ -f "${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE}" ]; then
        echo "found existing tarball, comparing md5sums"

        if [ ${FP_TAR_FILE: -2} == "z2" ]; then
            bzcat ${FP_TAR_FILE} | $CHECKTGZ | bzip2 > ${FP_TAR_FILE}.new
        else
            zcat ${FP_TAR_FILE} | $CHECKTGZ | gzip > ${FP_TAR_FILE}.new
        fi

        rm -f ${FP_TAR_FILE}
        mv ${FP_TAR_FILE}.new ${FP_TAR_FILE} >/dev/null 2>&1

        NEW_MD5=`md5sum ${FP_TAR_FILE} | awk '{printf $1}'` 2>/dev/null
        OLD_MD5=`md5sum ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE} | awk '{printf $1}'` 2>/dev/null

        if [ "$NEW_MD5" == "$OLD_MD5" ]; then
            echo "md5sums match, rm'ing new bundle and skipping to next run"
            rm -f ${FP_TAR_FILE}
            log "deleted|${FP_TAR_FILE}|md5sum_match"
            if [ -d "${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR}" ]; then
                echo "found existing ingested bundle, not doing it again"
                return 0
            fi
        else
            echo "md5sums mismatch! archiving new bundle with changed name, but not ingesting"
            # deal with bz2 or not
            mv ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE} ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE}.mm_md5.${OLD_MD5} >/dev/null 2>&1
            chmod 660 ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE}.mm_md5.${OLD_MD5} >/dev/null 2>&1
            mv ${FP_TAR_FILE} ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE} >/dev/null 2>&1
            log "archived|${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE}|md5sum_mismatch"
            if [ -d "${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR}" ]; then
                echo "found existing ingested bundle, not going it again"
                return 0
            fi
        fi
    fi

    # move to the archive location, checking for malformed tarballs
    echo "attempting zcat ${FP_TAR_FILE} . ${CHECKTGZ} . gzip to ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE}"

    # deal with bz2 or not
    if [ ${FP_TAR_FILE: -2} == "z2" ]; then
        bzcat ${FP_TAR_FILE} | $CHECKTGZ | bzip2 > ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE}
    else
        zcat ${FP_TAR_FILE} | ${CHECKTGZ} | gzip > ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE}
    fi

    rm -f ${FP_TAR_FILE}
    #mv ${FP_TAR_FILE} ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/

    if [ $? -gt 0 ]; then
        log "some sort of failure moving ${TAR_FILE} to archive"
        return 1
    else
        log "archived|${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE}"
    fi

    chmod 660 ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE} >/dev/null 2>&1
    chown ${FOWNER}:${FGROUP} ${ARCHIVE_DIR}/${CE_PREFIX}${TAR_DATE}/${TAR_FILE} >/dev/null 2>&1
    # untar in the working location, if not eval

    if [[ "${FP_TAR_FILE}" != *EVAL* ]]; then
        echo "not an EVAL ball, doing untar work"

        if [ ${TAR_FILE: -2} == "z2" ]; then
            tar -tjvf ${ARCHIVE_DIR}/${TAR_DATE}/${TAR_FILE} 2>/dev/null | head -n1 | grep 'var\/tmp\/c' > /dev/null
        else
            tar -tzvf ${ARCHIVE_DIR}/${TAR_DATE}/${TAR_FILE} 2>/dev/null | head -n1 | grep 'var\/tmp\/c' > /dev/null
        fi

        if [ $? -gt 0 ] ; then
            NUM_STRIP=1
        else
            NUM_STRIP=2
        fi

        echo "determined NUM_STRIP to be ${NUM_STRIP}"
        echo "running: cd ${WORKING_DIR}/${TAR_DATE}/ and tar -x --strip=${NUM_STRIP} -f ${ARCHIVE_DIR}/${TAR_DATE}/${TAR_FILE}"

        if [ ${TAR_FILE: -2} == "z2" ]; then
            cd ${WORKING_DIR}/${TAR_DATE}/ && tar -xj --strip=${NUM_STRIP} -f ${ARCHIVE_DIR}/${TAR_DATE}/${TAR_FILE}
        else
            cd ${WORKING_DIR}/${TAR_DATE}/ && tar -xz --strip=${NUM_STRIP} -f ${ARCHIVE_DIR}/${TAR_DATE}/${TAR_FILE}
        fi

        if [ $? -gt 0 ]; then
            # something went wrong
            log "some sort of failure untarring ${ARCHIVE_DIR}/${TAR_DATE}/${TAR_FILE} to ${WORKING_DIR}/${TAR_DATE}/|strip=${NUM_STRIP}"
            continue
        else
            # success!
            # create a file that indicates this is a fresh untar
            echo "success, adding initial .just_ingested file to untarred ingested/ dir"
            echo "`date`" > ${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR}/.just_ingested
             chown -R ${FOWNER}:${FGROUP} ${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR} >/dev/null 2>&1
             log "untarred|${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR}"
            # symlink to a symlink dir, making it easier to find, maybe
            echo "Creating symlink: ln -s ${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR} ${SYMLINK_DIR}"
            ln -s ${WORKING_DIR}/${TAR_DATE}/${UNTAR_DIR} ${SYMLINK_DIR}
        fi
    fi
}

if [[ $CMDARGS == "md5" ]]; then
    # get list of potentially finished collector uploads in upload directory
    # the 2013_2014 is dirty
    echo "md5 called, starting for loop"
    for MD5_FILE in `ls -1 ${UPLOAD_DIR}*.md5 | grep collector- | grep '_2010-\|_2011-\|_2012-\|_2013-\|_2014-\|_2015-\|_2016-\|_2017-\|_2018-'`; do
        # pre-set some variables we'll need
        FOUND_FP_TAR_FILE=`echo ${MD5_FILE} | sed -e 's/.md5$//g'`

        echo "determined FOUND_FP_TAR_FILE to be $FOUND_FP_TAR_FILE"

        # calculate the md5sums
        GIVEN_MD5=`head -1 ${MD5_FILE} | awk '{printf $1}'`
        PROVEN_MD5=`md5sum ${FOUND_FP_TAR_FILE} | awk '{printf $1}'` 2>/dev/null

        echo "determined GIVEN_MD5 and PROVEN_MD5 to be $GIVEN_MD5 and $PROVEN_MD5"

        if [ "$GIVEN_MD5" == "$PROVEN_MD5" ]; then
            echo "md5 matches, doing is_collector_bundle()"
            is_collector_bundle ${FOUND_FP_TAR_FILE}
            RC=$?

            if [ $RC -eq 0 ]; then
                echo "is_collector_bundle returned 0, running ingest()"
                ingest ${FOUND_FP_TAR_FILE}
                rm -f ${MD5_FILE}
            fi
        fi
    done
else
    if [ -f "$1" ]; then
        GIVEN_FP_TAR=$1
        echo "Called with specific bundle, running ingest()"
        ingest ${GIVEN_FP_TAR}
    fi
fi

rm -f ${LOCK_FILE}
