#!/bin/bash
#
# finds and renames collector tarballs with odd names in caselogs/upload that have an md5 file

CMP_X="z"
PID=$$
UPLOAD_DIR="/mnt/carbon-steel/upload/caselogs"

function is_collector_bundle()
{
    local IBUNDLE=$1

    # exists
    if [ -f $IBUNDLE ]; then
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

for TARBALL in `ls -1 ${UPLOAD_DIR}/*z* | grep -v 'md5\|collector-'`; do

    echo "checking $TARBALL"
    is_collector_bundle $TARBALL
    RC=$?

    if [ $RC -eq 1 ]; then
        continue
    fi

    echo "checking for md5"
    if [ -f "${TARBALL}.md5" ]; then
        FILE_MD5=`head -1 ${TARBALL}.md5 | awk '{printf $1}'`
        OUR_MD5=`md5sum ${TARBALL} | awk '{printf $1}'` 2>/dev/null

        if [ ! "$FILE_MD5" == "$OUR_MD5" ]; then
            echo "md5 mismatch"
            continue
        fi
    fi

    DIRBASE=$(dirname ${TARBALL})

    if [ ${TARBALL: -2} == "z2" ]; then
        CMP_X="j"
    else
        CMP_X="z"
    fi

    tar -t${CMP_X}vf ${TARBALL} | grep collector.stats | head -n1 | grep 'var\/tmp\/c' > /dev/null

    if [ $? -gt 0 ] ; then
        NUM_STRIP=1
    else
        NUM_STRIP=2
    fi

    if [ "$NUM_STRIP" -eq 1 ]; then
        COLL_DIR=`tar -t${CMP_X}f ${TARBALL} | grep 'collector.stats' | awk -F'/' '{print $2}'`
    else
        COLL_DIR=`tar -t${CMP_X}f ${TARBALL} | grep 'collector.stats' | awk -F'/' '{print $3}'`
    fi

    if [ ${TARBALL: -2} == "z2" ]; then
        NEW_FILE="${COLL_DIR}.${PID}.tar.bz2"
    else
        NEW_FILE="${COLL_DIR}.${PID}.tar.gz"
    fi

    mv ${TARBALL} ${DIRBASE}/${NEW_FILE}
    mv ${TARBALL}.md5 ${DIRBASE}/${NEW_FILE}.md5
done
