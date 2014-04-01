Ingestor
========

This repository contains all scripts and files related to the Ingestor.

Ingestor: This set of scripts is used to ingest Collector tarballs uploaded to our ftp/http site. It handles both initial ingestion (moving, untarring, archiving original), as well as initiates all ingestion scripts on the untarred information, allowing for a variety of analysis and health check tasks to be automated and reported on.


Collector
=========

Collector is maintained in Nexenta's Stash install now, not Github. Ingestor remains on this Github.

I try to keep an up to date .deb at: http://www.nexenta.com/nexenta-collector_latest_solaris-i386.deb , for download to appliances (both ones pre-dating 3.1.5, or 3.1.5+ if you want to snag a later version).
