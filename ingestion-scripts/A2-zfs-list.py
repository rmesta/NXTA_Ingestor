#!/usr/bin/env python

# Author: andrew.galloway@nexenta.com
# Created On: 2013-09-26
# Last Updated On: 2013-09-26
# Description:
#   creates a zfs list like output from zfs-get-all

import sys
from functions import *  # local functions.py file

# name of this script - could be filename, or something unique people will recognize
script_name = 'A2-zfs-list.py'

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
def main(bundle_dir):

    if verify_bundle_directory(script_name, bundle_dir):
        working_file = bundle_dir + "/ingestor/zfs-list"

        pools = []
        datasets = {}
        snapshots = 0

        with open(bundle_dir + "/zfs/zfs-get-p-all.out") as f:
            for line in f:
                if line[0:4] == "NAME":
                    continue

                columns = ' '.join(line.split()).split()
                
                pool = columns[0].split('/')[0]
                dataset = columns[0]

                zfs_property = columns[1]
                zfs_property_value = columns[2]
                zfs_property_origin = columns[3]

                if not pool in pools:
                    pools.append(pool)

                if not dataset in datasets.keys():
                    datasets[dataset] = {}
                    datasets[dataset][zfs_property] = zfs_property_value

                    if '@' in dataset:
                        snapshots = snapshots + 1
                else:
                    datasets[dataset][zfs_property] = zfs_property_value

        append_file(working_file, "Pools: " + str(len(pools)) + "\n")
        append_file(working_file, "Datasets: " + str(len(datasets)) + "\n")
        append_file(working_file, "Snapshots: " + str(snapshots) + "\n")
        append_file(working_file, "\n")

        longest = 24
        for dataset, junk in datasets.iteritems():
            if len(dataset) > longest:
                longest = len(dataset)

        output_line = "%-*s\t%4s\t%-5s\t%-7s\t%-7s\t%-7s\t%-7s\t%-7s\t%-6s\t%-5s\t%-4s\n" % (longest, "Name", "Type", 
            "RecSZ", "Used", "Avail", "Refer", "Reserv", "Refrsrv", "Cmpres", "Dedup", "Sync")
        append_file(working_file, output_line)

        for dataset, properties in datasets.iteritems():
            ds_type = properties['type']

            if 'recordsize' in properties:
                ds_recsz = bytes_format(properties['recordsize'])
            elif 'volblocksize' in properties:
                ds_recsz = bytes_format(properties['volblocksize'])
            else:
                ds_recsz = '-'

            ds_used = bytes_format(properties['used'])
            ds_refer = bytes_format(properties['referenced'])

            if ds_type == "filesystem" or ds_type == "volume":
                ds_avail = bytes_format(properties['available'])
                ds_reserv = bytes_format(properties['reservation'])
                ds_refreserv = bytes_format(properties['refreservation'])
                ds_dedup = properties['dedup']
                ds_sync = properties['sync']
                ds_compress = properties['compression']
            else:
                ds_avail, ds_reserv, ds_refreserv, ds_dedup, ds_sync, ds_compress = '-' * 6

            output_line = "%-*s\t%4s\t%-5s\t%-7s\t%-7s\t%-7s\t%-7s\t%-7s\t%-6s\t%-5s\t%-4s\n" % (longest,
                dataset, ds_type[0:4], ds_recsz, ds_used, ds_avail, ds_refer, ds_reserv, ds_refreserv,
                ds_compress[0:6], ds_dedup[0:5], ds_sync[0:4])
            
            append_file(working_file, output_line)

    else:
        print script_name + ": directory (" + bundle_dir + ") not valid."
        sys.exit(1)

# no reason to touch
if __name__ == '__main__':

    if len(sys.argv) <= 1:
        print script_name + ": no directory specified."
    else:
        main(sys.argv[1])
