#!/bin/bash

source ../.nxrc
[ -z "${NXTA_LEGACY}" ] && { echo "NXTA_LEGACY var MUST be set !"; exit 1; }

[ -z "$1" ] && { echo "Must specify valid filename for ingestion."; exit 1; }

[ -d "$1" ] && { echo "FAIL: must specify tarball, not a directory."; exit 1; }

if [ -f "$1" ]; then
	echo "Running initial ingestion."
	${NXTA_LEGACY}/initial-ingestion.sh $1 >/dev/null 2>&1

	echo
	echo "You can now either run ingestor manually against the untarred "
	echo "directory structure, or wait - ingestor should pick up and "
	echo "ingest the new bundle directory shortly (runs on 1m cron job "
	echo "but could be backed up a bit)."
	echo
fi
