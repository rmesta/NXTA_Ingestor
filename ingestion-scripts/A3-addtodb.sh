#!/usr/bin/env bash

# Author: aaron.knodel@nexenta.com
# Created On: 2016-10-31
# Last Updated On: 2016-10-31
# Description:
# Add an entry to the database for ingested collectors

echo "$1" >> /var/tmp/testing-addtodb.sh-script.txt

# include generic functions file
dbloc=/mnt/carbon-steel/ingested/collector_db/collector.sqlite

source /root/Collector/Ingestor/ingestion-scripts/functions.sh

# name of this script - could be filename, or something unique people will recognize
SCRIPT_NAME="A3-addtodb.sh"

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
main () {
#BUNDLE_DIR is the full path of the collector bundle
	BUNDLE_DIR=$1 # use BUNDLE_DIR inside here, don't use $1, just for sanity
	echo $BUNDLE_DIR
	sqlite3 $dbloc "insert into collectors (date,path,machinesig) values (\"$(echo $BUNDLE_DIR | cut -d/ -f5)\",\"$(echo $BUNDLE_DIR)\",\"$(echo $BUNDLE_DIR | cut -d- -f6)\")"
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

