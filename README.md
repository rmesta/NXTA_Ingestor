Ingestor
========

This repository contains all scripts and files related to the Ingestor.

Ingestor: This set of scripts is used to ingest Collector tarballs uploaded to our ftp/http site. It handles both initial ingestion (moving, untarring, archiving original), as well as initiates all ingestion scripts on the untarred information, allowing for a variety of analysis and health check tasks to be automated and reported on.


Collector
=========

This repository contains all scripts and files related to the Collector.

Collector: This utility will be behind the "support" command functionality in NMS (and its equivalent in NEF).

I try to keep an up to date .deb at: http://www.nexenta.com/nexenta-collector_latest_solaris-i386.deb , for download to appliances (both ones pre-dating 3.1.5, or 3.1.5+ if you want to snag a later version). Every effort is made to keep collector version-compatible with NexentaStor 3.x and 4.x, it should run on any version of either.

Please note that while I try to keep this Github up to date, it is not the actual repository for Collector anymore - that is in Stash.
