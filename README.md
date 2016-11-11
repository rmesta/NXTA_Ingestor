#
# NXTA_Ingestor.git
# 2016-11-10
#
 This repository contains:

 1) All legacy ingestor.sh and associated helper scripts

 2) Next Generation Tools (three major components):

	- The Nexenta Ingestor re-write (nxing.py) with TCP
	  service capability

	- A new ingestion-script to post-process raw bundle
	  text files into JSON object files (A3-raw-to-json.py)

	- The Nexenta Collector Analyzer Tool (nxcat.py) intended
	  to be used for collector bundle overview and (hopefully)
	  make root cause analysis faster and more efficient

 3) Csummary ingestion-script integration

    # Ben can say stuffs here


#
# Runtime Notes
#
 Both 'legacy' and 'NextGen' tools now rely on environment variables
 set by sourcing ./.nxrc. The only change you should have to make to
 deploy, is make sure NXTA_INGESTOR points to this directory (wherever
 it gets installed) and you should be golden.

 To run 'nxcat' or 'nxing' manually, make sure you source ./.nxrc so
 that PYTHONPATH is set properly.

