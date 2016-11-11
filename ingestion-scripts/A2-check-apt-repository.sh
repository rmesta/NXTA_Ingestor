#!/usr/bin/env bash
#
# Author:	andrew.galloway@nexenta.com
# Created On:	2013-09-26
# Last Updated:	2016-11-09
# Description:
#   just prepares a warning directory to put various warnings into

#
# include generic functions file
#
[ -z "${NXTA_INGESTOR}" ] && { echo "NXTA_INGESTOR var MUST be set !"; exit 1; }
source ${NXTA_INGESTOR}/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A2-check-apt-repository.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
    BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
    WARN_FILE=${BUNDLE_DIR}/ingestor/warnings/check-apt-repository
    CHECK_FILE=${BUNDLE_DIR}/ingestor/checks/check-apt-repository

    echo "Apt Repository Check | aptrepocheck" > ${CHECK_FILE}

    CHECK_VERS=$(check_nexenta_version)

    if [ "$CHECK_VERS}" -lt "4000" ] && [ "$CHECK_VERS}" -gt "2999" ]; then
        if [ -f "${BUNDLE_DIR}/appliance/sources.list" ]; then
            LIC_MD5=`cat ${BUNDLE_DIR}/collector.stats | grep 'License key:' | awk -F':' '{print $2}'`

            for APT_MD5 in `cat ${BUNDLE_DIR}/appliance/sources.list | grep -v '^#' | awk -F'/' '{print $5}' | uniq`; do
                if [ "${LIC_MD5}" == "${APT_MD5}" ]; then
                    echo "<li>License key matches repository</li>" >> ${CHECK_FILE}

                    PRE_CHECK_LICENSE=`wget --user-agent="NEX-QUERY" -S "http://nexenta.com/apt/${LIC_MD5}/${VERS}/plugins/dists/hardy-stable/main/Contents-solaris-i386.gz" 2>&1 | tail -n 2 | head -n 1`
                    
                    echo ${PRE_CHECK_LICENSE} | grep ERROR 2>&1 >/dev/null
                    RC=$?

                    if [ $RC == 0 ]; then
                        echo "<li>Problem with repository, HTTP query returned: ${PRE_CHECK_LICENSE}</li>" >> ${WARN_FILE}
                        exit 1
                    fi

                    PLUGINS=`echo "http://nexenta.com/apt/${LIC_MD5}/${VERS}/plugins/dists/hardy-stable/main/Contents-solaris-i386.gz" | xargs -n1 wget --user-agent="NEX-QUERY" -i - -O - -q | zcat -c | awk '{print $2}' | sort | uniq`
                    BFILES=`echo "http://nexenta.com/apt/${LIC_MD5}/${VERS}/dists/hardy-stable/main/binary-solaris-i386/Packages.gz" | xargs -n1 wget --user-agent="NEX-QUERY" -i - -O - -q | zcat -c | grep "i386/admin/base-files" | awk -F' ' '{print $2}'`
                    NEWAPTV=`echo "http://nexenta.com/apt/${LIC_MD5}/${VERS}/getNewAptVersion" | wget --user-agent="NEX-QUERY" -i - -O - -q`

                    wget --user-agent="NEX-QUERY" -q "http://nexenta.com/apt/${MD5}/${VERS}/plugins/dists/hardy-stable/main/Packages.gz" -O plugin_packages.gz
                    wget --user-agent="NEX-QUERY" -q "http://nexenta.com/apt/${MD5}/${VERS}/$BFILES" -O base_files_check.deb
                    dpkg-deb -x base_files_check.deb check_base_files
                    VERSION=`cat check_base_files/etc/issue`
                    rm -rf check_base_files
                    rm -f base_files_check.deb

                    echo "<li>Repository details:<ul>" >> ${CHECK_FILE}
                    echo "<li>Version (base-files): ${VERSION}</li>" >> ${CHECK_FILE}
                    echo "<li>Version (NewApt): {$NEWAPTV}</li>" >> ${CHECK_FILE}
                    echo "<li>Plugins Information:<ul>" >> ${CHECK_FILE}
                    
                    for plugin in $PLUGINS; do
                        PFILE=`zcat plugin_packages.gz | grep "${plugin}_" | grep Filename | awk '{print $2}' | awk -F'/' '{printf $NF}'`
                        echo "<li>${plugin} (${PFILE})</li>" >> ${CHECK_FILE}
                    done

                    echo "</ul></li>" >> ${CHECK_FILE}
                    echo "</ul></li>" >> ${CHECK_FILE}
                else
                    echo "<li>License key does not match repository in /etc/apt/sources.list</li>" >> ${WARN_FILE}
                fi
            done
        else
            echo "<li>No sources.list file</li>" >> ${WARN_FILE}
        fi
    else
        echo "<li>Cannot currently analyze NexentaStor 4.x repositories.</li>" >> ${WARN_FILE}
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
