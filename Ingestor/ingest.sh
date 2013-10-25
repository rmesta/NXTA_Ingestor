#!/bin/bash
# Andrew Galloway

if [ -z "$1" ]; then
    echo "Must specify valid filename for ingestion."
    exit 1
fi

if [ -d "$1" ]; then
    echo "Failed - must specify a tarball, not a directory."
    exit 1
fi

if [ -f "$1" ]; then
    echo "Running initial ingestion."
    /root/Collector/Ingestor/initial-ingestion.sh $1 >/dev/null 2>&1

    echo -n "You can now either run ingestor manually against the untarred directory structure, or wait - ingestor should pick up and"
    echo " ingest the new bundle directory shortly (runs on 1m cron job but could be backed up a bit)."

    # should figure out the dir and run /root/Collector/Ingestor/ingestor.sh $1, but lazy
fi
