#!/usr/bin/env python

#
# Nexenta Collector Analyzer Tool (nxcat)
# Copyright 2015 Nexenta Systems, Inc.  All rights reserved.
#
# NB: This script assumes a collector bundle tarfile has
#     already been ingested and the argument to '--path'
#     is either the fully qualified or relative pathname
#     to the results of the ingested collector bundle.
#
import os
import re
import sys
import optparse
import json
import math
import time
import errno
import gzip
from pprint import pprint
from lib.CText import *
from netaddr import *


_ver = '1.0.0'
base = ''
zp_stat = {}
as_vmode = ''
zp_vmode = ''
hc_vmode = ''
sac_res = False
debug = False
machid = ''


def read_raw_txt(rawfile):
    rawlines = []

    try:
        with open(rawfile, 'r') as f:
            for l in f.readlines():
                pattern = '^#.*$'           # skip comment lines
                if re.match(pattern, l):
                    continue
                rawlines.append(l.rstrip('\n'))

    except IOError:
        pass

    return rawlines


def get_cs_items():
    global base
    global machid
    csfile = os.path.join(base, 'collector.stats')
    license = ''
    done = False

    print_header('collector.stats')
    for l in read_raw_txt(csfile):
        if license and not done:
            customer = get_custy_info(license)

            print 'Customer:\t',
            if customer is not None:
                print_bold(customer, 'white', True)
            else:
                print_fail('unable to obtain customer name from DB')

            done = True
            continue

        elif l.startswith('License'):
            license = l.split(':')[-1].strip()

            print 'License:' + 7*' ',
            if license.startswith('TRIA'):
                print_fail(license)
            else:
                print license

            machid = l.split('-')[-2].strip()
            print 'Machine ID:\t',
            print_warn(machid, True)

            continue

        elif l.startswith('Appliance'):
            patt = '.*\((\S+)\)$'
            mp = re.match(patt, l)
            if mp:
                print 'NS Version:\t', mp.group(1)
            continue
    return


def get_opthac():
    global base
    global machid
    File = os.path.join(base, 'ingestor/json/tar-czf-opthac.tar.gz.json')

    if not os.path.exists(File):
        return

    try:
        with open(File) as f:
            json_data = json.load(f)

    except IOError:
        print '\t',
        print_warn('No clustering info in bundle', True)
        return

    print_header('Clustering Info')
    for c in json_data:
        for val in sorted(json_data[c]):
            if val == 'ha':
                print_bold('Clustered:\t', 'white', False)
                ha = json_data[c][val]
                if ha == True:
                    prfmt_bold(str(ha), '%11s', 'green', True)
                else:
                    # XXX - still to unit test this path
                    prfmt_warn(str(ha), '%11s')
                continue

            elif val == 'name':
                cn = json_data[c][val]
                print_bold('Cluster Name:\t' + 7 * ' ', 'white', False)
                print_pass(cn)
                continue

            elif val == 'node1' or val == 'node2':
                try:
                    if json_data[c][val]['machid'] == machid:
                        node = 'master'
                        print_bold('Primary Node Info', 'white', True)
                    else:
                        node = 'slave'
                        print 'Secondary Node Info'

                except KeyError:
                    continue

                if 'hostname' in json_data[c][val]:
                    host = json_data[c][val]['hostname']
                    print '\tHostname:\t',
                    if node == 'master':
                        print_warn(host, True)
                    else:
                        print_lite(host, 'white', True)

                if 'machid' in json_data[c][val]:
                    mcid = json_data[c][val]['machid']
                    print '\tMachine ID:\t',
                    if node == 'master':
                        print_warn(mcid, True)
                    else:
                        print_lite(mcid, 'white', True)

                if 'mntpt' in json_data[c][val]:
                    mpnt = json_data[c][val]['mntpt']
                    print '\tMnt Point:\t',
                    if node == 'master':
                        print_warn(mpnt, True)
                    else:
                        print_lite(mpnt, 'white', True)

                if 'zpool_guid' in json_data[c][val]:
                    guid = json_data[c][val]['zpool_guid']
                    print '\tZPool GUID:\t',
                    if node == 'master':
                        print_warn(guid, True)
                    else:
                        print_lite(guid, 'white', True)

    return


def get_uptime():
    global base
    File = os.path.join(base, 'ingestor/json/uptime.out.json')

    up_stats = {}
    try:
        with open(File) as f:
            up_stats = json.load(f)

    except IOError:
        print 'Up Time:\t',
        print_warn('No uptime info in bundle', True)
        return

    try:
        msg = up_stats['uptime']

    except KeyError:
        print 'Up Time:\t',
        print_warn('No uptime info in bundle', True)
        return

    print 'Up Time:\t', msg
    return


#
# collector.stats Info
#
def process_cs():
    get_cs_items()
    get_uptime()
    return


#
# Dump Device
#
def dump_dev():
    global base
    dmpfile = os.path.join(base, 'kernel/dumpadm.conf')
    msgfile = os.path.join(base, 'kernel/messages')

    for l in read_raw_txt(dmpfile):
        if l.startswith('#'):
            continue
        elif l.startswith('DUMPADM_DEVICE'):
            dev = l.split('=')[-1]
            continue

    try:
        print 'Dump Device:\t', dev,

    except UnboundLocalError:
        print_warn('No dump device info in bundle', True)
        return

    size = ''
    for l in read_raw_txt(msgfile):
        patt = '.* dump on .*'
        mp = re.match(patt, l)
        if mp:
            size = l.split()[-2]    # in MB
            break

    if len(size) != 0:
        szgb = math.ceil(float(size) / 1024)
    else:
        szgb = '??'

    print_bold('\t( ' + str(szgb) + ' GB ' + ')', 'white', True)
    return


def max_cstates():
    global  base
    File = os.path.join(base, 'ingestor/json/kstat-p-td-10-6.out.json')

    print 'max_cstates:\t',
    try:
        with open(File) as f:
            data = json.load(f)

    except IOError:
        print_warn('No Data Found', True)
        return

    for d in data:
        print_pass(data[d])


#
# Hardware
#
def vendor_cpu():
    global  base
    File = os.path.join(base, 'ingestor/json/prtdiag-v.out.json')

    try:
        with open(File) as f:
            json_data = json.load(f)

    except IOError:
        print 'MB Vendor:\t',
        print_warn('No vendor info in bundle', True)
        print 'CPU:\t\t',
        print_warn('No CPU info in bundle', True)
        return

    for section in json_data:
        if section == 'header':
            print_warn('< Using old ingested data; please re-ingest >', True)

        elif section == 'system':
            print 'MoBo Vendor:\t', json_data[section]

        elif section == 'bios':
            print 'BIOS Info:\t', json_data[section]

        elif section == 'bmc':
            print 'BMC Info:\t', json_data[section]

        elif section == 'cpu info':
            nc = len(json_data[section])
            print 'CPU Info:\t',
            ncpu = str(nc) + 'x'

            try:
                cpuinfo = json_data[section][0].lstrip().split('@')[0]

            except IndexError:
                print_warn('No CPU info in bundle', True)
                return

            print ncpu, cpuinfo


def memory():
    global base
    File = os.path.join(base,
        'ingestor/json/echo-memstat-mdb-k-tail-n2.out.json')

    try:
        with open(File) as f:
            json_data = json.load(f)

    except IOError:
        print 'RAM:\t\t',
        print_warn('No memory info in bundle', True)
        return

    for section in json_data:
        if section == 'total':
            mem = json_data[section]['MBs']
            if len(mem) > 3:
                mem = math.ceil(float(mem) / 1024)
                unit = "GB"
            else:
                unit = "MB"
            print 'RAM:\t\t', mem, unit


#
# ZPool Info
#
def print_fmt_msg(hdr, msg, disp):
    formatted = []
    t = 0
    i = 55

    #
    # work w/single string and slice it up in
    # lines of 55 chars (or so) until done and
    # put them in formatted list.
    #
    s = ' '.join(msg)
    sl = len(s)
    while i < sl:
        while s[i] != ' ':
            i += 1
            if i == sl:
                break

        formatted.append(s[t:i].lstrip())
        t = i
        i = t + 55
        if i >= sl:
            formatted.append(s[t:sl].lstrip())
            break

    #
    # Finally simply print the passed in header
    # and the formatted output.
    #
    prt_hdr = False
    for f in formatted:
        if not prt_hdr:
            if disp == 'bold':
                print_warn(hdr + ':\t\t' + f, True)
            else:
                print_debug(hdr + ':\t\t' + f, True)
            prt_hdr = True
            continue
        if disp == 'bold':
            print_warn('\t\t' + f.lstrip(), True)
        else:
            print_debug('\t\t' + f.lstrip(), True)

    return


def print_status(pool):
    global zp_stat

    if 'State' in zp_stat[pool]:    # New format
        print_fmt_msg('State:', zp_stat[pool]['State'], 'bold')

    elif 'status' in zp_stat[pool]: # Old format
        print_fmt_msg('Status', zp_stat[pool]['status'], 'bold')

    return


def get_vdev(pool, item):
    global zp_stat

    pname = zp_stat[pool]['config'][item]
    for x in pname['vdev']:
        if 'vdev' in pname['vdev'][x]:
            vdev = pname['vdev'][x]['vdev']
        else:
            vdev = pname['vdev']

    return vdev


def slot_xref(msg, vd, color, sfix = ''):
    global base
    File = os.path.join(base, 'ingestor/json/nmc-c-show-lun-slotmap.out.json')

    if not os.path.exists(File):
        print_bold(msg + vd, color, True)
        return False
    else:
        try:
            with open(File) as f:
                slotmap = json.load(f)

        except Exception, e:
            print 'Exception %s raised' % str(e)
            return False

    jbod = slotno = False
    try:
        jb = slotmap[vd]['jbod']
        jbod = True

    except KeyError:
        print_bold(msg + vd, color, True)
        return False

    try:
        sn = slotmap[vd]['slot#']
        slotno = True

    except KeyError:
        print_bold(msg + vd, color, True)
        return False

    if jbod and slotno:
        if len(sfix) == 0:
            s = msg + vd + '\t\t( ' + jb + ', slot:' + sn + ' )'
        else:
            s = msg + vd +  \
                '\t( ' + jb + ', slot:' + sn + ' )\t' + '(' + sfix + ')'
        print_bold(s, color, True)
    else:
        print_bold(msg + vd, color, True)
        return False

    return True


def simple_device(dev):
    patt = 'c[0-9]+t[0-9]+d[0-9]+.*'
    mp = re.match(patt, dev)
    if mp:
        return True
    return False


def print_devices_ofmt(pool):
    global zp_stat

    vdevs = [pool, 'cache', 'logs']
    for v in vdevs:
        try:
            pname = zp_stat[pool]['config'][v]
        except KeyError:
            continue

        vtype = ''
        dok = dfl = 0
        devices = pname['vdev']
        for d in devices:
            vtype = d

            if simple_device(d):
                vds = pname['vdev'][d]['state']
                if vds == 'ONLINE':
                    dok += 1
                elif vds == 'FAULTED' or vds == 'DEGRADED':
                    dfl += 1
                continue

            vDv = get_vdev(pool, v)
            for vc in vDv:
                try:
                    vds = vDv[vc]['state']
                except KeyError:
                    continue

                if vds == 'ONLINE':
                    dok += 1                    # Number of ONLINE devices
                else:
                    try:
                        notol = vDv[vc]['vdev']
                        for flt in notol:
                            if notol[flt]['state'] == 'FAULTED':
                                dfl += 1        # Number of FAULTED devices

                    except KeyError:
                        pass

        devlen = len(devices)
        tdev = dok / devlen

        if tdev > 11:               # Anything more thn 11 disks, flag fail
            col = 'red'
        elif vtype == 'raidz1-0':   # raidz1 is pow2 + 1 parity disk, else warn
            col = 'yellow' if (tdev - 1) % 2 else 'green'
        elif vtype == 'raidz2-0':   # raidz2 is pow2 + 2 parity disks, else warn
            col = 'yellow' if (tdev - 2) % 2 else 'green'
        elif vtype == 'raidz3-0':   # raidz3 is pow2 + 3 parity disks, else warn
            col = 'yellow' if (tdev - 3) % 2 else 'green'
        else:
            col = 'white'           # Anything else not considered a problem
        kd = str(tdev)

        sdev = False
        done = False
        for x in devices:
            stt = pname['vdev'][x]['state']

            #
            # NB: Hack to deal w/json files that have multiple devices
            #     as vdevs for 'cache' or 'logs', instead of a properly
            #     defined dictionary that has the one vdev and multiple
            #     devices underneath.
            #
            if len(devices) > 1:
                sdev = simple_device(x)
                if v == 'cache' or v == 'logs' or sdev:
                    if not done:
                        done = True
                    else:
                        continue

            if v == 'cache' or v == 'logs':
                msg = 'vdev:\t' + v
            elif sdev:
                msg = 'vdev:\t' + 'Concatenation'
                kd = str(dok + dfl)
            else:
                msg = 'vdev:\t' + x
            print_pass(msg) if stt == 'ONLINE' else print_fail(msg)

            print '\tTotal Devices: (',
            print_bold(kd, col, False)
            print ')'

            fd = str(dfl)
            if dfl != 0:
                print_fail('\tFailed Devices:\t' + fd)

            try:
                vdev = pname['vdev'][x]['vdev']
            except KeyError:
                vdev = pname['vdev']

            for vd in vdev:
                try:
                    if vdev[vd]['state'] == 'ONLINE':
                        slot_xref('\t\t', vd, 'green')

                    else:
                        try:
                            pdevs = vdev[vd]['vdev']    # raidz2 devices

                            for fds in pdevs:
                                vds = vdev[vd]['vdev'][fds]['state']
                                if vds == 'FAULTED' or vds == 'DEGRADED':
                                    slot_xref('\t\t\t', fds, 'red')
                                    print_fail('\t\t\t\t' + '<< ' + \
                                        vdev[vd]['vdev'][fds]['info'] + ' >>')
                                else:
                                    slot_xref('\t\t\t', fds, 'green')

                        except KeyError:                # mirror devices

                            vds = vdev[vd]['state']
                            if vds == 'FAULTED' or vds == 'DEGRADED':
                                slot_xref('\t\t', vd, 'red')
                                print_fail('\t\t\t' + \
                                    '<< ' + vdev[vd]['info'] + ' >>')
                            else:
                                slot_xref('\t\t\t', vd, 'green')

                except KeyError:
                    continue

    return


def print_lun(lun):
    lname = lun[0].lower()
    lstat = lun[1]

    if lstat == 'ONLINE':
        slot_xref('\t\t', lname, 'green')
    else:
        slot_xref('\t\t', lname, 'red')

    return


ident = 2
def print_nx_devs(nxd):
    global  ident

    if len(nxd) == 0:
        return

    ident += 1
    for y in nxd:
        nd = nxd[y]
        if nd['st'] == 'ONLINE':
            slot_xref('\t' + 2*ident*' ', y, 'green')
        else:
            slot_xref('\t' + 2*ident*' ', y, 'red')

        if 'nx' in nd and len(nd['nx']) != 0:
            print_nx_devs(nd['nx'])

    return


def print_hs_data(vdev):
    global  ident

    for fd in vdev['hs']:
        if vdev['hs'][fd]['state'] == 'DEGRADED':
            print_fail('\t  ' + fd)

        if 'devs' in vdev['hs'][fd]:
            dvs = vdev['hs'][fd]['devs']
            for x in sorted(dvs):
                if dvs[x]['st'] == 'ONLINE':
                    if 'msg' in dvs[x]:
                        col = 'yellow'
                        msg = dvs[x]['msg']
                        slot_xref('\t' + 2*ident*' ', x, col, sfix=msg)
                    else:
                        col = 'green'
                        slot_xref('\t' + 2*ident*' ', x, col)
                else:
                    if '-' in x:    # print replacing-X or spare-X labels
                        print_fail('\t' + 2*ident*' ' + x)

                    if 'nx' in dvs[x]:
                        print_nx_devs(dvs[x]['nx'])
                    elif 'old' in dvs[x]:
                        pdev = dvs[x]['old']
                        pdst = dvs[x]['st']
                        msg = x + ' was ' + pdev + ' (%s) ' % pdst
                        print_fail('\t' + 2*ident*' ' + msg)

        elif 'old' in vdev['hs'][fd]:
            pdev = vdev['hs'][fd]['old']
            pdst = vdev['hs'][fd]['state']
            msg = fd + ' was ' + pdev + ' (%s) ' % pdst
            print_fail('\t' + 2*ident*' ' + msg)
    return


def print_spares(spares):
    print_bold('Spares:', 'white', True)
    if 'luns' in spares:
        for l in spares['luns']:
            if l[1] == 'AVAIL':
                uc = 'white'
                sc = 'green'
            else:
                uc = 'gray'
                sc = 'yellow'

            vals = '%s, %s, %s' % (l[0].lower(), l[1], l[2])
            fmts = '%37s, %7s, %18s,'
            cols = '%s, %s, %s' %  (uc, sc, sc)
            disp = 'lite, bold, lite'
            prfmt_mc_row(vals, fmts, cols, disp)
    return


def print_cache(cache):
    print_bold('Cache:', 'white', True)
    if 'luns' in cache:
        for l in cache['luns']:
            if l[1] == 'ONLINE':
                uc = 'white'
                sc = 'green'
                fm = '%8s'
            elif l[1] == 'FAULTED':
                uc = 'gray'
                sc = 'red'
                fm = '%9s'
            else:
                uc = 'yellow'
                sc = 'yellow'
                fm = '%8s'

            vals = '%s, %s' %  (l[0].lower(), l[1])
            fmts = '%s, %s' % ('%37s', fm)
            cols = '%s, %s' %  (uc, sc)
            disp = 'lite, bold'
            prfmt_mc_row(vals, fmts, cols, disp)
    return


def print_logs(logs):
    print_bold('Logs:', 'white', True)
    for d in logs:
        if 'luns' in logs[d]:
            for l in logs[d]['luns']:
                if l[1] == 'ONLINE':
                    sc = 'green'
                else:
                    sc = 'yellow'

                vals = '%s, %s' %  (l[0].lower(), l[1])
                fmts = '%37s, %8s,'
                cols = '%s, %s' %  ('white', sc)
                disp = 'lite, bold'
                prfmt_mc_row(vals, fmts, cols, disp)
    return


def zp_vdevs():
    global base
    global zp_stat
    File = os.path.join(base, 'ingestor/json/zpool-status-dv.out.json')

    try:
        with open(File) as f:
            zp_stat = json.load(f)
    except IOError:
        print_warn('\tNo zpool status info found in bundle', True)
        return

    print 70 * '-'
    for vd in zp_stat:
        if vd == 'spares':
            print_spares(zp_stat[vd])

        elif vd == 'cache':
            print_cache(zp_stat[vd])

        elif vd == 'logs':
            print_logs(zp_stat[vd])

    return


def print_devices_nfmt(pool):
    global zp_stat

    for v in zp_stat[pool]:
        #
        # if 'devs' key exists, this is a vdev
        #
        if 'luns' in zp_stat[pool][v]:
            vdev = zp_stat[pool][v]

            if vdev['State'] == 'ONLINE':
                print_pass('vdev:\t' + v)
                for lun in vdev['luns']:
                    print_lun(lun)
            else:
                print_fail('vdev:\t' + v)
                if 'hs' in vdev:
                    print_hs_data(vdev)

                for lun in vdev['luns']:
                    print_lun(lun)
    return


def print_devices(pool):
    global zp_stat

    if 'State' not in zp_stat[pool]:
        print_devices_ofmt(pool)
    else:
        print_devices_nfmt(pool)

    return


def print_scan(pool):
    global zp_stat

    print_bold('Scan:', 'yellow', False)
    if 'scan' in zp_stat[pool]:
        mlen = len(zp_stat[pool]['scan'])
        for i in xrange(0, mlen):
            msg = zp_stat[pool]['scan'][i]
            print_debug('\t\t' + msg, True)
    return


def zp_status(zpool):
    global base
    global zp_stat
    File = os.path.join(base, 'ingestor/json/zpool-status-dv.out.json')

    try:
        with open(File) as f:
            zp_stat = json.load(f)
    except IOError:
        print_warn('\tNo zpool status info found in bundle', True)
        return

    for pool in zp_stat:
        if pool != zpool:
            continue
        print_status(pool)
        print_devices(pool)
        print_scan(pool)

    return


def sz_unit(size):
    unit = size[-1]

    if unit == 'Z':
        exp = 7             # ZettaBytes
    elif unit == 'E':
        exp = 6             # ExaBytes
    elif unit == 'P':
        exp = 5             # PetaBytes
    elif unit == 'T':
        exp = 4             # TeraBytes
    elif unit == 'G':
        exp = 3             # GigaBytes
    elif unit == 'M':
        exp = 2             # MegaBytes
    div = 1024**exp

    return unit, div


def zp_size_chk(zpool, zpsize):
    global base
    File = os.path.join(base, 'ingestor/json/zfs-get-p-all.out.json')

    try:
        with open(File) as f:
            zprops = json.load(f)
    except IOError:
        print_warn('\tNo zfs properties info found in bundle', True)
        return

    unit, div = sz_unit(zpsize)
    if debug:
        msg = "%s:\t%s" % (zpool, zpsize)
        print_debug(msg, True)

    for p in zprops:
        if p == zpool:
            val = zprops[p]['used']['value']

            # abbreviate actual value into Eng units
            nval = float(val) / div

            if nval >= zpsize:
                print_fail('\t\t### Warning: Over-provisioned ###')
            elif debug:
                fval = "{0:.2f}".format(nval) + unit
                print_warn('Fully Used:\t%s' % fval, True)


def zp_list(mode):
    global base
    File = os.path.join(base, 'ingestor/json/zpool-list-o-all.out.json')

    if not os.path.exists(File):
        return

    print_header('ZPools Info')
    with open(File) as f:
        json_data = json.load(f)

    for section in json_data:
        if json_data[section]:
            name = json_data[section]['name']
            health = json_data[section]['health']
            bootfs = json_data[section]['bootfs']
            used = json_data[section]['alloc']
            free = json_data[section]['free']
            size = json_data[section]['size']
            cap = json_data[section]['cap']
            if 'lowatermark' in json_data[section]:
                lowat = int(json_data[section]['lowatermark'])
            else:
                lowat = 50      # some sane value

            if 'hiwatermark' in json_data[section]:
                hiwat = int(json_data[section]['hiwatermark'])
            else:
                hiwat = 80      # some sane value

            print 70 * '-'
            print 'Pool:\t\t',
            print_bold(name, 'white', True)

            tint = 'red' if health != 'ONLINE' else 'green'
            print_bold('Health:\t\t' + health, tint, True)

            if mode == 'verbose' or health != 'ONLINE':
                zp_status(name)

            print 'Active Boot:\t',
            print_bold(bootfs, 'white', True)

            print 'Total:\t\t',
            print_bold(used + ' / ' + size, 'white', True)

            capacity = int(cap.split('%')[0])
            if capacity <= lowat:
                tint = 'green'
            elif capacity > lowat and capacity <= hiwat:
                tint = 'yellow'
            elif capacity > hiwat:
                tint = 'red'
            print 'Capacity:\t',
            print_bold(cap, tint, True)
            zp_size_chk(name, size)

    zp_vdevs()


#
# JBOD Info
#
def print_jbod_hdr():

    prfmt_mc_row('     ,      ,      ,      , Total,  Busy',
                 ' %15s,  %12s,  %20s,  %21s,  %10s,   %5s',
                 'white, white, white, white, white, white',
                 ' bold,  bold,  bold,  bold,  bold,  bold')

    prfmt_mc_row('JBOD, Vendor, Model, Serial Number, Slots , Slots',
                 '%9s,    %11s,  %13s,          %21s,   %7s,  %6s',
                 'white, white, white,         white, white, white',
                 ' bold,  bold,  bold,          bold,  bold,  bold')

    prfmt_mc_row('----------, --------, ----------------, \
                 ----------------, -----, -----',
                 '%12s,    %9s,  %17s,  %17s,   %6s,  %7s',
                 'white, white, white, white, white, white',
                 ' bold,  bold,  bold,  bold,  bold,  bold')


def dump_jbod_data(status, alias, vendor, model, serial, tslots, bslots):

    if status == None:
        tint = 'white'
    elif status == 'OK':
        tint = 'green'
    else:
        tint = 'yellow'

    vals = '%s, %s, %s, %s, %s, %s' %  \
        (alias, vendor, model, serial, tslots, bslots)
    fmts = '%12s,    %9s,  %17s,  %17s,   %5s,  %6s,'
    cols = '%s, %s, %s, %s, %s, %s' %  \
        (tint, 'white', 'white', 'white', 'white', 'white')
    disp = ' bold,  lite,  lite,  lite,  lite,  lite'

    prfmt_mc_row(vals, fmts, cols, disp)


def jbods():
    global base
    File1 = os.path.join(base, 'ingestor/json/nmc-c-show-jbod-all.out.json')
    File2 = os.path.join(base, 'ingestor/json/sesctl-enclosure.out.json')
    colorized = False

    if not os.path.exists(File1):
        return

    print_header('JBOD Enclosure Info')
    try:
        with open(File1) as f:
            jbods = json.load(f)
    except IOError:
        print_warn('\tNo JBOD info found in bundle', True)
        return

    if os.path.exists(File2):
        try:
            with open(File2) as f:
                sesctl = json.load(f)
                colorized = True
        except IOError:
            pass

    #
    # Alpha-numeric sort of 'jbod-1, jbod-10, jbod-11, jbod-2, ...' items
    #
    print_jbod_hdr()
    for jb in sorted(jbods, key=lambda item: int(item.split('-')[1])):
        alias = jbods[jb]['alias']
        vendor = jbods[jb]['vendor']
        model = jbods[jb]['model']
        serial = jbods[jb]['serial']
        tslots = jbods[jb]['total_slots']
        bslots = jbods[jb]['busy_slots']

        status = None
        if colorized:
            for lid in sesctl:
                if lid == serial:
                    status = sesctl[lid]['status']

        patt = '[a-zA-Z0-9-]+_SIM_.*'
        mp = re.match(patt, model)
        if mp:
            continue

        patt = '\s*SuperMicro\s*'
        mp = re.match(patt, vendor)
        if mp:
            vendor = 'SMC'

        patt = '\s*LSI[_A-Z]+\s*'
        mp = re.match(patt, vendor)
        if mp:
            vendor = 'LSI'

        patt = '\s*AIC[_A-Z]+\s*'
        mp = re.match(patt, vendor)
        if mp:
            vendor = 'AIC'

        patt = '\s*(SuperMicro-)(\S*)'
        mp = re.match(patt, model)
        if mp:
            model = mp.group(2)

        patt = '\s*(DataON-)(\S*)'
        mp = re.match(patt, model)
        if mp:
            model = mp.group(2)

        patt = '\s*(LSI.*-)(\S*)'
        mp = re.match(patt, model)
        if mp:
            model = 'LSI_' + mp.group(2).rstrip('_')

        patt = '\s*(AIC.*-)(\S*)'
        mp = re.match(patt, model)
        if mp:
            model = mp.group(2).rstrip('_')

        patt = '\s*(HP.*-)(\S*)'
        mp = re.match(patt, model)
        if mp:
            model = mp.group(2)

        patt = '\s*(XYRATEX-)(\S*)'
        mp = re.match(patt, model)
        if mp:
            model = mp.group(2)

        if vendor == 'SMC':
            patt = '(\S*)-back$'
            mp = re.match(patt, model)
            if mp:
                patt1 = '(\S*)-(\S*)-back'
                mp1 = re.match(patt1, model)
                if mp1:
                    model = mp1.group(1) + '-back'

        dump_jbod_data(status, alias, vendor, model, serial, tslots, bslots)


#
# hddisco Info
#
def print_hddko_hdr():
    prfmt_mc_row('Cnt,  Vendor, Model,   F/W, mpxio,  pths,  SSD,  SMART',
                 '%5s,     %8s,  %13s,  %12s,   %9s,   %6s,   %5s,    %8s',
                 'white, white, white, white, white, white, white,  white',
                 'bold,   bold,  bold,  bold,  bold,  bold,  bold,   bold')

    s = '---, --------, ----------------, -----, -----, ----, ---, -----'
    prfmt_mc_row(s,
                 '%5s,     %9s,  %17s,  %8s,   %s,   %6s,   %5s,  %s',
                 'white, white, white, white, white, white, white, white',
                 'bold,   bold,  bold,  bold,  bold,  bold,  bold,  bold')


def hdd_json_params(hdisks, dev):
    global base
    File = os.path.join(base, 'ingestor/json/nmc-c-show-lun-smartstat.out.json')

    smrt = ''
    if not os.path.exists(File):
        smrt = 'Unknown'
    else:
        with open(File) as f:
            smrtdata = json.load(f)

        for sd in smrtdata:
            if dev in smrtdata[sd]['luns']:
                smrt = smrtdata[sd]['luns'][dev]['status']
                break

    hdko = hdisks[dev]
    try:
        vendr = hdko['vendor']
    except KeyError:
        vendr = 'unknown'

    patt = '([0-9a-zA-Z_]+)\S*'
    mp = re.match(patt, vendr)
    if mp:
        vdr = mp.group(1)
    else:
        vdr = vendr

    try:
        model = hdko['product']
    except KeyError:
        model = 'Indeterminate'

    try:
        fware = hdko['revision']
    except KeyError:
        fware = '???'

    try:
        ssd = hdko['is_ssd']
    except KeyError:
        ssd = '??'

    try:
        mpxio = hdko['mpxio_enabled']
    except KeyError:
        mpxio = 'no'

    try:
        pcnt = hdko['path_count']
    except KeyError:
        pcnt = 0

    try:
        serno = hdko['serial']
    except KeyError:
        serno = 'unknown'

    return vdr, model, fware, ssd, mpxio, pcnt, serno, smrt


def hddko():
    global base
    File = os.path.join(base, 'ingestor/json/hddisco.out.json')
    brands = {}

    if not os.path.exists(File):
        return

    print_header('hddisco Info')
    with open(File) as f:
        disks = json.load(f)

    for hdd in disks:
        if disks[hdd]['device_type'] != 'disk':
            continue

        vdr, model, fware, ssd, mpxio, pcnt, serno, smrt = \
            hdd_json_params(disks, hdd)
        if debug:
            print hdd, vdr, model, fware, '\'%s\'' % ssd, smrt

        if vdr not in brands:
            brands[vdr] = {}
        if model not in brands[vdr]:
            brands[vdr][model] = {}
        if fware not in brands[vdr][model]:
            brands[vdr][model][fware] = {}
        if ssd not in brands[vdr][model][fware]:
            brands[vdr][model][fware][ssd] = {}
        if mpxio not in brands[vdr][model][fware][ssd]:
            brands[vdr][model][fware][ssd][mpxio] = {}
            brands[vdr][model][fware][ssd][mpxio]['count'] = 0

        if smrt not in brands[vdr][model][fware][ssd][mpxio]:
            brands[vdr][model][fware][ssd][mpxio][smrt] = {}
            brands[vdr][model][fware][ssd][mpxio][smrt]['count'] = 0

        if 'devs' not in brands[vdr][model][fware][ssd][mpxio]:
            brands[vdr][model][fware][ssd][mpxio]['devs'] = []

        #
        # duplicate WWN detection; formatting for output is done later
        #
        ports = []
        pdups = []
        for i in xrange(0, int(pcnt)):
            try:
                p = disks[hdd]['P'][str(i)]['target_port']
                if p in ports:
                    pdups.append(p)
                else:
                    ports.append(p)
            except KeyError:
                continue

        f = {}
        f['dev'] = hdd
        f['pts'] = ports
        f['dup'] = pdups
        f['sno'] = serno
        f['smt'] = smrt
        brands[vdr][model][fware][ssd][mpxio]['devs'].append(f)

        if mpxio == "yes":
            brands[vdr][model][fware][ssd][mpxio]['status'] = 'on'
            brands[vdr][model][fware][ssd][mpxio]['paths'] = pcnt
            if debug:
                print 'mpxio', pcnt, ports

        else:       # mpxio disabled
            brands[vdr][model][fware][ssd][mpxio]['status'] = 'off'
            brands[vdr][model][fware][ssd][mpxio]['paths'] = 1
            if debug:
                print ports

        brands[vdr][model][fware][ssd][mpxio]['count'] += 1
        brands[vdr][model][fware][ssd][mpxio][smrt]['count'] += 1

    if debug:
        pprint(brands)

    print_hddko_hdr()
    for v in brands:
        for m in brands[v]:
            if m == 'Indeterminate':
                mc = 'yellow'
                md = 'bold'
            else:
                mc = 'white'
                md = 'lite'

            for f in brands[v][m]:
                vc = fc = 'white'
                vd = fd = 'lite'
                if v == 'STEC' and m == 'ZeusRAM':
                    if f < 'C023':
                        fc = 'red'
                        fd = 'bold'
                elif v == 'ATA':
                    vc = 'red'
                    vd = 'bold'
                elif v == 'unknown':
                    vc = 'yellow'
                    vd = 'bold'

                for d in brands[v][m][f]:
                    if d == 'yes':
                        dc = 'green'
                        dd = 'bold'
                    else:
                        dc = 'yellow'
                        dd = 'lite'

                    for x in brands[v][m][f][d]:
                        c = brands[v][m][f][d][x]['count']
                        s = brands[v][m][f][d][x]['status']
                        p = brands[v][m][f][d][x]['paths']
                        try:
                            SMRT = brands[v][m][f][d][x]['Enabled']['count']
                        except KeyError:
                            SMRT = 0

                        if s == 'on':
                            sc = 'green'
                            sd = 'bold'
                        else:
                            sc = 'yellow'
                            sd = 'lite'

                        if SMRT > 0:
                            XC = 'yellow'
                            XD = 'bold'
                            XM = 'on '
                        else:
                            XC = 'green'
                            XD = 'lite'
                            XM = 'off '

                        #
                        # check for duplicates and form new LoD => pl[{}, ...]
                        #
                        pl = []
                        lod = brands[v][m][f][d][x]['devs']
                        for hw in lod:
                            for pt in hw['pts']:
                                Z = {}
                                if pt in hw['dup']:
                                    Z['port'] = pt
                                    Z['snum'] = hw['sno']
                                    Z['disk'] = hw['dev']
                                    pl.append(Z)

                        #
                        # print hdd aggregate info
                        #
                        z = '%s, %s, %s, %s, %s, %s, %s, %s' %  \
                            (c, v, m, f, s, p, d, XM)
                        y = '%5s, %9s, %17s, %8s, %7s, %6s, %6s, %7s'
                        w = 'white, %s, %s, %s, %s, white, %s, %s' % \
                            (vc, mc, fc, sc, dc, XC)
                        D = 'lite, %s, %s, %s, %s, lite, %s, %s' % \
                            (vd, md, fd, sd, dd, XD)
                        prfmt_mc_row(z, y, w, D)

                        #
                        # print hdd's that have any dupped WWN's
                        #
                        if len(pl) > 0:
                            for k in pl:
                                dk = k['disk']
                                sn = k['snum']
                                pt = k['port']

                                z = 'Dev:, %s, SN:, %s, Port:, %s' %\
                                    (dk, sn, pt)
                                y = ' %5s, %21s,  %4s, %20s,  %6s, %17s'
                                w = 'gray,  red, gray,  red, gray,  red'
                                D = 'bold, lite, bold, lite, bold, bold'
                                prfmt_mc_row(z, y, w, D)
                            print


#
# Networking
#

def network():
    net_config()
    net_rehash()
    lnk_config()
    phs_config()
    print_net()


def print_nw_hdr():
    prfmt_mc_row('Link, Class, State, MTU, Speed, Duplex, IPv4, Mask',
                 '%6s,  %11s,   %6s,  %4s, %6s,   %7s,    %10s,  %15s',
                 'white, white, white, white, white, white, white, white',
                 'bold,  bold,  bold,  bold,  bold,  bold,  bold,  bold')
    prfmt_bold('---------', '%9s', 'white', False)
    prfmt_bold('-----',     '%8s', 'white', False)
    prfmt_bold('-----',     '%6s', 'white', False)
    prfmt_bold('---',       '%4s', 'white', False)
    prfmt_bold('-----',     '%6s', 'white', False)
    prfmt_bold('------',    '%7s', 'white', False)
    prfmt_bold('--------', '%12s', 'white', False)
    prfmt_bold('--------', '%15s', 'white', True)


def str_adj(stg, w):
    l = len(stg)
    s = w - l
    n = stg + s*' '

    return n


def fmt_ipmp_dev(dev, ipa, msk):
    global SNInfo

    n = str_adj(dev, 10)
    prfmt_bold(n, '%10s', 'blue', False)

    if len(dev) >= 11:
        ipfmt = '%47s'
        mkfmt = '%17s'
    else:
        ipfmt = '%49s'
        mkfmt = '%15s'

    # CIDR
    ipnet = '%s/%s' % (ipa, msk)
    IP = IPNetwork(ipnet)
    cidr = '%s' % IP.cidr
    if SNInfo[cidr]['conflict'] == True:
        ipcol = mkcol = 'red'
        ipfnt = mkfnt = 'bold'
    else:
        ipcol = mkcol = SNInfo[cidr]['color']
        ipfnt = mkfnt = 'lite'

    fields = '%s, %s' % (ipa, msk)
    fmt = '%s, %s' % (ipfmt, mkfmt)
    colors = '%s, %s' % (ipcol, mkcol)
    fonts = '%s, %s' % (ipfnt, mkfnt)

    return fields, fmt, colors, fonts


def fmt_aggr_dev(dev, cls, stt, mtu, col):

    # Interface color
    disp = 'bold' if cls == 'vlan' else 'lite'
    if stt == 'up':
        if col == 'gray':
            scol = col
            disp = 'lite'
        else:
            scol = 'green'
    else:
        scol = 'red'
        disp = 'bold'

    # MTU color
    if mtu >= '9000':
        if col == 'white':
            mcol = 'green'
            mdsp = 'bold'
        else:
            mcol = col
            mdsp = 'lite'
    else:
        mcol = 'green'
        mdsp = 'lite'

    n = str_adj(dev, 10)
    fields = '%s, %s, %s, %s' % (n, cls, stt, mtu)
    fmt = '%10s, %7s, %4s, %6s'
    colors = '%s, %s, %s, %s' % (col, col, scol, mcol)
    fonts = 'lite, lite, %s,  %s' % (disp, mdsp)

    return fields, fmt, colors, fonts


vlnk = {}
def fmt_phys_dev(lnk, dev, cls, stt, mtu, spd, dup):
    if lnk not in vlnk:
        vlnk[lnk] = {}
    if 'mtu' not in vlnk[lnk]:
        vlnk[lnk]['mtu'] = mtu
    if 'spd' not in vlnk[lnk]:
        vlnk[lnk]['spd'] = spd

    if vlnk[lnk]['mtu'] != mtu:
        mtc = 'yellow'
        mtf = 'bold'
    else:
        mtc = 'gray'
        mtf = 'lite'

    if vlnk[lnk]['spd'] != spd or spd == '0':
        spc = 'yellow'
        spf = 'bold'
    else:
        spc = 'green' if spd >= '10000' else 'gray'
        spf = 'lite'

    dupw = 6
    if dup != 'full':
        dpcl = 'red'
        dpdp = 'bold'
    else:
        dpcl = 'gray'
        dpdp = 'lite'

    if stt == 'down':
        stwd = 2 + len(stt) - 1
        mtuw = 5
        stcl = 'red'
        stdp = 'bold'
    elif stt == 'unknown':
        stwd = len(stt) - 1
        mtuw = 3
        stcl = 'red'
        stdp = 'lite'
        dupw = 5
    else:
        stwd = 2 + len(stt)
        mtuw = 6
        stcl = 'gray'
        stdp = 'lite'

    mts = '%'+str(mtuw)+'s'
    sts = '%'+str(stwd)+'s'
    dps = '%'+str(dupw)+'s'

    fields = '%s, %s, %s, %s, %s, %s' % (dev, cls, stt, mtu, spd, dup)
    fmt = '%s, %s, %s, %s, %s, %s' % ('%11s', '%6s', sts, mts, '%6s', dps)
    colors = 'gray, gray, %s, %s, %s, %s' % (stcl, mtc, spc, dpcl)
    fonts = 'bold, lite, %s, %s, %s, %s' % (stdp, mtf, spf, dpdp)

    return fields, fmt, colors, fonts


netproc = {}
def print_phys_devs(l, k):
    global NetLink
    global NetPhys
    ni = NetInfo

    devs = 0
    for c in ni[l][k]['lnk']['over'].split():
        if c == '--':
            continue
        devs += 1

    for i in ni[l][k]['lnk']['over'].split():
        if i == '--':
            print
            return
        try:
            cls = NetLink[i]['class']
        except KeyError:
            m = '\n%s: No such device' % i
            print_fail(m)
            continue

        lnk = ni[l][k]['lnk']['link']
        stt = ni[l][k]['lnk']['state']
        mtu = ni[l][k]['lnk']['mtu']

        if 'phs' in ni[l][k]:
            if i in ni[l][k]['phs']:
                spd = ni[l][k]['phs'][i]['speed']
                dup = ni[l][k]['phs'][i]['duplex']

                if k not in netproc:
                    netproc[k] = {}
                    netproc[k]['done'] = False

                if netproc[k]['done']:
                    continue

                flds, fmt, cols, fnts = \
                    fmt_phys_dev(l, i, cls, stt, mtu, spd, dup)
                prfmt_mc_row(flds, fmt, cols, fnts)

                devs -= 1
                if devs == 0:
                    netproc[k]['done'] = True
        else:
            flds, fmt, cols, fnts = fmt_aggr_dev(i, cls, stt, mtu, 'white')
            prfmt_mc_row(flds, fmt, cols, fnts)

            if i not in netproc:
                netproc[i] = {}
                netproc[i]['done'] = False

            if cls != 'phys':
                if not netproc[i]['done']:
                    for d in NetLink[i]['over'].split():
                        nld = NetLink[d]
                        cls = nld['class']
                        stt = nld['state']
                        mtu = nld['mtu']

                        pdv = NetPhys[d]
                        spd = pdv['speed']
                        dup = pdv['duplex']

                        flds, fmt, cols, fnts = \
                            fmt_phys_dev(l, d, cls, stt, mtu, spd, dup)
                        prfmt_mc_row(flds, fmt, cols, fnts)

                netproc[i]['done'] = True
    print


def fmt_link_dev(lnk, cls, stt, mtu, ipa, msk):
    global SNInfo

    # MTU color
    if mtu >= '9000':
        mcol = 'green'
        mdsp = 'bold'
    elif mtu >= '1500':
        mcol = 'green'
        mdsp = 'lite'
    else:
        mcol = 'red'
        mdsp = 'bold'

    if stt == 'down':
        stwd = 2 + len(stt) - 1
        mtuw = 5
        stcl = 'red'
        stdp = 'bold'
    elif stt == 'unknown':
        stwd = len(stt) - 1
        mtuw = 3
        stcl = 'red'
        stdp = 'bold'
    else:
        stwd = 2 + len(stt)
        mtuw = 6
        stcl = 'green'
        stdp = 'bold'

    # CIDR
    ipnet = '%s/%s' % (ipa, msk)
    IP = IPNetwork(ipnet)
    cidr = '%s' % IP.cidr
    if SNInfo[cidr]['conflict'] == True:
        ipcol = mkcol = 'red'
        ipfnt = mkfnt = 'bold'
    else:
        ipcol = mkcol = SNInfo[cidr]['color']
        ipfnt = mkfnt = 'lite'

    mts = '%'+str(mtuw)+'s'
    sts = '%'+str(stwd)+'s'

    n = str_adj(lnk, 10)
    prfmt_bold(n, '%10s', 'blue', False)

    clstr = '%6s' if len(lnk) >= 11 else '%7s'
    fields = '%s, %s, %s, %s, %s' % (cls, stt, mtu, ipa, msk)
    colors = 'white, %s, %s, %s, %s' % (stcl, mcol, ipcol, mkcol)
    fonts = 'lite, bold, %s, %s, %s' % (mdsp, ipfnt, mkfnt)

    if cls == 'vlan':
        mks = '%14s'

    elif cls == 'aggr':
        mks = '%15s'
    else:
        mks = '%15s' if len(lnk) >= 11 else '%14s'

    fmt = '%s, %s, %s, %s, %s' % (clstr, sts, mts, '%30s', mks)

    return fields, fmt, colors, fonts


def print_net():
    global NetPhys
    ni = NetInfo

    print_nw_hdr()
    for l in sorted(ni):

        if 'ip' in ni[l]:
            ipa = ni[l]['ip']['inet']
            msk = ni[l]['ip']['mask']
            cid = ni[l]['ip']['cidr']

        done = False
        devs = 0
        for c in ni[l]:
            if c == 'ip':
                continue
            devs += 1

        for k in sorted(ni[l]):
            if k == 'ip':
                continue

            lnk = ni[l][k]['lnk']['link']
            cls = ni[l][k]['lnk']['class']
            stt = ni[l][k]['lnk']['state']
            mtu = ni[l][k]['lnk']['mtu']

            if k == l:
                fds, fmt, col, fnt = fmt_link_dev(lnk, cls, stt, mtu, ipa, msk)

                if cls == 'phys':
                    prfmt_mc_row(fds, fmt, col, fnt)

                    spd = NetPhys[l]['speed']
                    dup = NetPhys[l]['duplex']

                    fds, fmt, col, fnt =    \
                        fmt_phys_dev(k, l, cls, stt, mtu, spd, dup)
            else:
                if not done:
                    fds, fmt, col, fnt = fmt_ipmp_dev(l, ipa, msk)
                    prfmt_mc_row(fds, fmt, col, fnt)
                    done = True

                if cls == 'phys':
                    spd = NetPhys[lnk]['speed']
                    dup = NetPhys[lnk]['duplex']

                    fds, fmt, col, fnt =    \
                        fmt_phys_dev(l, lnk, cls, stt, mtu, spd, dup)
                    prfmt_mc_row(fds, fmt, col, fnt)

                    devs -= 1
                    if devs == 0:
                        print
                    continue

                else:
                    agc = 'gray' if cls == 'vlan' else 'white'
                    fds, fmt, col, fnt =    \
                        fmt_aggr_dev(lnk, cls, stt, mtu, agc)

            prfmt_mc_row(fds, fmt, col, fnt)
            print_phys_devs(l, k)


NetLink = {}
def lnk_config():
    global NetLink
    global base
    File = os.path.join(base, 'ingestor/json/dladm-show-link.out.json')

    if not os.path.exists(File):
        return

    with open(File) as f:
        NetLink = json.load(f)


NetPhys = {}
def phs_config():
    global NetPhys
    global base
    File = os.path.join(base, 'ingestor/json/dladm-show-phys.out.json')

    if not os.path.exists(File):
        return

    with open(File) as f:
        NetPhys = json.load(f)


#
# We do this here because we want to limit the
# color choices as to what constitutes is a
# 'valid' IP and Netmask. We reserve 'red' for
# conflicting IP's
#
popc = 2
def get_next_color():
    global popc
    colors = [ 'gray', 'blue', 'purple', 'cyan', 'green', 'yellow' ]
    popc = popc % len(colors)
    c = colors[popc]
    popc += 1
    return c


#
# Classless Inter Domain Routing
#
# cidr: {
#   ipl:      list              /* list of IP's that map to this subnet */
#   conflict: True/False        /* True if same IP and same Subnet */
#   snshared: True/False        /* True if more than 1 IP in Subnet */
#   color:    'color'           /* Tint to print IP and Netmask */
# }
#
SNInfo = {}
def net_rehash():

    for i in NetInfo:
        cidr = NetInfo[i]['ip']['cidr']
        if cidr not in SNInfo:
            SNInfo[cidr] = {}

        ip = NetInfo[i]['ip']['inet']
        if 'ipl' not in SNInfo[cidr]:
            SNInfo[cidr]['ipl'] = []

        if ip in SNInfo[cidr]['ipl']:
            SNInfo[cidr]['conflict'] = True
            SNInfo[cidr]['color'] = 'red'
        else:
            SNInfo[cidr]['ipl'].append(ip)
            SNInfo[cidr]['color'] = 'white'
            SNInfo[cidr]['conflict'] = False

        lip = len(SNInfo[cidr]['ipl'])
        if lip <= 1:
            SNInfo[cidr]['color'] = 'white'
        elif lip > 1:
            SNInfo[cidr]['color'] = get_next_color()

        if ip in SNInfo[cidr]['ipl']:
            SNInfo[cidr]['snshared'] = lip

    # Debug
    # js = json.dumps(SNInfo, indent=2, separators=(',', ': '), sort_keys=True)
    # print js


NetInfo = {}
def net_config():
    global base
    File = os.path.join(base, 'ingestor/json/network-info.out.json')

    if not os.path.exists(File):
        return

    print_header('Network Info')
    with open(File) as f:
        data = json.load(f)

    for i in sorted(data):
        key = ''
        if 'cfg' in data[i]:
            ipaddr = data[i]['cfg']['inet']
            ntmask = data[i]['cfg']['mask']
            ipnet = '%s/%s' % (ipaddr, ntmask)
            ip = IPNetwork(ipnet)
            cidr = '%s' % ip.cidr

            if 'group' in data[i]['cfg']:
                grp = data[i]['cfg']['group']
                if grp not in NetInfo:
                    NetInfo[grp] = {}
                if 'ip' not in NetInfo[grp]:
                    NetInfo[grp]['ip'] = {}
                key = grp

            else:
                link = data[i]['cfg']['link']
                if link not in NetInfo:
                    NetInfo[link] = {}
                if 'ip' not in NetInfo[link]:
                    NetInfo[link]['ip'] = {}
                key = link

            NetInfo[key]['ip']['inet'] = ipaddr
            NetInfo[key]['ip']['mask'] = ntmask
            NetInfo[key]['ip']['cidr'] = cidr
        else:
            continue

        if 'lnk' in data[i]:
            iface = data[i]['lnk']['link']

            try:
                if iface not in NetInfo[key]:
                    NetInfo[key][iface] = {}
                    NetInfo[key][iface]['lnk'] = {}
                NetInfo[key][iface]['lnk'] = data[i]['lnk']

                if 'phs' in data[i]:
                    if 'phs' not in NetInfo[key][iface]:
                        NetInfo[key][iface]['phs'] = {}
                    NetInfo[key][iface]['phs'] = data[i]['phs']

            except KeyError:
                if iface not in NetInfo:
                    NetInfo[iface] = {}
                    NetInfo[iface]['lnk'] = {}
                NetInfo[iface]['lnk'] = data[i]['lnk']

                if 'phs' in data[i]:
                    if 'phs' not in NetInfo[iface]:
                        NetInfo[iface]['phs'] = {}
                    NetInfo[iface]['phs'] = data[i]['phs']

    debug = False
    if debug == False:
        return

    for k in NetInfo:
        print_bold(k, 'blue', True)
        print '\tInet:', NetInfo[k]['ip']['inet'],
        print '\tMask:', NetInfo[k]['ip']['mask'],
        print '\tCIDR:', NetInfo[k]['ip']['cidr']

    js = json.dumps(NetInfo, indent=2, separators=(',', ': '), sort_keys=True)
    print js


#
# Faults
#
def nms_faults():
    global base
    File = os.path.join(base, 'ingestor/json/nmc-c-show-faults.out.json')

    if not os.path.exists(File):
        return

    print_header('nms Faults')
    with open(File) as f:
        json_data = json.load(f)

    for section in json_data:
        if section.startswith('fault'):
            try:
                sev = json_data[section]['severity']
                trig = json_data[section]['trigger']
            except KeyError:
                continue

            if sev == 'NOTICE':
                print_warn(sev + ' ' + trig, True)
            else:
                print_fail(sev + ' ' + trig)
            print '\tCount:\t\t', json_data[section]['count']
            print '\tFault:\t\t', json_data[section]['fault']

            if sev == 'NOTICE':
                print_warn('\tMessage:\t' + json_data[section]['msg'], True)
            else:
                print_fail('\tMessage:\t' + json_data[section]['msg'])
            print '\tTime:\t\t', json_data[section]['time'], '\n'
        else:
            data = json_data[section]
            dlen = len(data)
            summ = 'Summary:'
            slen = len(summ) + 1        # account for trailing space
            idx = 80                    # length of terminal
            i = idx - slen - 4          # Crude calculation; see str.rfind()
            row1 = data[:i]
            row2 = data[i:]

            print_bold('Summary:', 'white', False)
            print_debug(row1 + '\n\t' + row2, True)
    return


def print_secs(l, h):   # h == hex string
    i = int(h, 16)      # convert from hex to int
    f = float(i)        # int to floating point val
    s = str(f / 1e9)    # convert from nS to Secs

    print_warn('%18s' % l + 7*' ' + s + ' Secs', True)
    return


def fma_faults():
    global base
    File = os.path.join(base, 'ingestor/json/fmdump-e.out.gz.json')
    zflags = ('pool_failmode',  \
            'parent_type',      \
            'cksum_algorithm',  \
            'cksum_actual',     \
            'cksum_expected',   \
            'vdev_path',        \
            'pool')
    uflags = ('product',        \
            'vendor',           \
            'serial',           \
            'revision',         \
            'un-decode-info',   \
            'driver-assessment',\
            'device-path',      \
            'devid')
    sflags = ('product',        \
            'vendor',           \
            'serial',           \
            'revision',         \
            'device-path',      \
            'devid',            \
            'delta',            \
            'threshold')

    if not os.path.exists(File):
        return

    print_header('fma Faults (30 days)')
    with open(File) as f:
        faults_json = json.load(f)

    for key in faults_json:
        zfs = False
        scsi = False
        print_bold(key, 'blue', True)
        flt = faults_json[key]

        if 'class' in flt:      # consider using flt.has_key('class')
            line = flt['class']

            patt = '\S+\.zfs\.\S+'
            mp = re.match(patt, line)
            if mp:
                zfs = True

            patt = '\S+\.io\.scsi\.\S+'
            mp = re.match(patt, line)
            if mp:
                scsi = True
                etyp = line.split('.')[-1]

            tint = 'gray'
            font = 'lite'
            for k in flt:
                if zfs:
                    if k in zflags:
                        if k == 'cksum_actual' and  \
                           flt[k] != flt['cksum_expected']:
                                tint = 'red'
                                font = 'bold'
                        else:
                            tint = 'yellow'
                            font = 'bold'
                    else:
                        tint = 'gray'
                        font = 'lite'
                elif scsi:
                    if etyp == 'uderr' or etyp == 'derr':
                        if k in uflags:
                            if k == 'driver-assessment' and flt[k] == 'fail':
                                tint = 'red'
                                font = 'bold'
                            else:
                                tint = 'yellow'
                                font = 'bold'
                        else:
                            tint = 'gray'
                            font = 'lite'
                    elif etyp == 'slow-io':
                        if k in sflags:
                            tint = 'yellow'
                            font = 'bold'
                            if k == 'threshold' or k == 'delta':
                                print_secs(k, flt[k])
                                continue
                        else:
                            tint = 'gray'
                            font = 'lite'

                fmt_func = eval('prfmt_%s' % font)
                reg_func = eval('print_%s' % font)

                fmt_func(k + '\t', '%19s', tint, False)
                reg_func(flt[k].ljust(40, ' '), tint, True)

    return


def faults():
    nms_faults()
    fma_faults()


def print_svcs_hdr(mode):

    if mode == 'verbose':
        prfmt_mc_row(' Service, Shared Volumes',
                 '%8s, %16s',
                 'white, white',
                 'bold, bold')

        prfmt_mc_row(' -------, --------------',
                 '%8s, %16s',
                 'white, white',
                 'bold, bold')
    else:
        prfmt_mc_row(' Service, Export Cnt, Protocols, nfsd thrds, lockd thrds',
                 '%8s, %12s, %15s, %15s, %15s',
                 'white, white, white, white, white',
                 'bold, bold, bold, bold, bold')

        ln = '-------, ----------, ---------------, ------------, -------------'
        prfmt_mc_row(ln,
                 '%8s, %12s, %18s, %13s, %15s',
                 'white, white, white, white, white',
                 'bold, bold, bold, bold, bold')


def print_nfs_shared():
    global base
    File = os.path.join(base, 'ingestor/json/dfshares.out.json')

    try:
        with open(File) as f:
            dfshares  = json.load(f)

    except Exception, e:
        print 'Exception %s raised' % str(e)
        return

    idx = 0
    for s in dfshares:
        l = len(dfshares[s]['resource'])

        if idx == 0:
            n = '%'+str(l+4)+'s'
            v = 'NFS, %s' % dfshares[s]['resource']
            f = '%s,  %s' % ('%6s', n)
            c = 'green, white'
            d = 'bold, lite'
        else:
            n = '%'+str(l)+'s'
            v = '%s, %s' % ('', dfshares[s]['resource'])
            f = '%s, %s' % ('%10s', n)
            c = 'white, white'
            d = 'lite, lite'
        prfmt_mc_row(v, f, c, d)
        idx += 1


def get_svc_type(svc):
    if svc == 'sharenfs':
        return 'NFS'
    elif svc == 'sharesmb':
        return 'SMB'
    else:
        return 'Unknown'


def is_wildcard(s):
    if '*' in s:
        return True
    return False


def is_hostname(s):
    patt = '^([a-zA-Z]+[0-9_.-]*).*$'
    mp = re.match(patt, s)
    if mp:
        return True
    return False


def pfix_strip(s):
    if '*' in s:
        S = s.lstrip('*')
    else:
        S = s

    if '@' in S:
        z = S.lstrip('@')
    else:
        z = S

    return z


def nfs_ips(dfs, s, x):

    X = dfs[s][x]
    if type(X) is list:
        ipr = []
        for p in X:
            if len(p) == 0:
                continue

            if p not in ipr:
                ipr.append(p)

        ips = []
        hnm = []
        for s in sorted(ipr):
            z = pfix_strip(s)
            if is_hostname(z):
                hnm.append(z)
                continue
            ips.append(z)

        try:
            s1 = IPSet(ips)
            val = list(s1.iter_ipranges())
        except AddrFormatError, e:
            s = '%s\t<< Invalid Address >>' % str(e).split()[2]
            v = '%s, %s, %s' % (x, '=', s)
            f = '%s, %s, %s' % ('%17s', '%s', '%s')
            c = 'cyan, white, red'
            d = 'lite, lite, bold'
            prfmt_mc_row(v, f, c, d)
            return []

        if len(hnm) > 0:
            for h in hnm:
                val.append(h)

    elif type(X) is unicode:
        if X == '*':
            return X

        if is_hostname(X):
            val = []
            val.append(X)
            return val

        ips = []
        ips.append(pfix_strip(X))

        try:
            s1 = IPSet(ips)
            val = list(s1.iter_ipranges())
        except AddrFormatError, e:
            s = '%s\t<< Invalid Address >>' % str(e).split()[2]
            v = '%s, %s, %s' % (x, '=', s)
            f = '%s, %s, %s' % ('%17s', '%s', '%s')
            c = 'cyan, white, red'
            d = 'lite, lite, bold'
            prfmt_mc_row(v, f, c, d)
            return []

    else:
        val = dfs[s][x]

    return val


def print_nfs_prop(nk, x, p):

    if nk == False:
        v = '%s, %s, %s' % (x, '=', p)
        f = '%s, %s, %s' % ('%17s', '%s', '%s')
        c = 'cyan, white, gray'
        d = 'lite, lite, lite'
        prfmt_mc_row(v, f, c, d)
        nk = True
    else:
        n = '%'+str(20+len(p))+'s'
        prfmt_lite(p, n, 'gray', True)

    return nk


NFSData = False
def print_zfs_nfs(mode):
    global base
    global NFSData
    File = os.path.join(base, 'ingestor/json/zfs-get-nfs.out.json')
    ipr = []

    try:
        with open(File) as f:
            dfshares  = json.load(f)

    except Exception, e:
        print 'Exception %s raised' % str(e)
        return

    svc = ''
    numshares = 0
    for s in dfshares:
        n = '%'+str(len(s)+4)+'s'
        svc = get_svc_type(dfshares[s]['type'])
        if mode == 'verbose':
            v = '%s, %s' % (svc, s)
            f = '%s, %s' % ('%6s', n)
            c = 'green, white'
            d = 'bold, bold'
            prfmt_mc_row(v, f, c, d)

        numshares += 1
        if mode == 'verbose':

            for x in sorted(dfshares[s]):
                if x == 'type':
                    continue

                nfsk = {}
                if x == 'root' or x == 'rw' or x == 'ro':

                    if x not in nfsk:
                        nfsk[x] = {}
                        nfsk[x]['prt'] = False

                    for p in nfs_ips(dfshares, s, x):
                        try:
                            first, last = p.__str__().split('-')
                        except:
                            if is_hostname(p) or is_wildcard(p):
                                key = nfsk[x]['prt']
                                nfsk[x]['prt'] = print_nfs_prop(key, x, p)
                            continue

                        if first == last:
                            ip = first
                        else:
                            ip = '%s - %s' % (first, last)

                        key = nfsk[x]['prt']
                        nfsk[x]['prt'] = print_nfs_prop(key, x, ip)
                    continue

                try:
                    v = '%s, %s, %s' % (x, '=', dfshares[s][x])
                    f = '%s, %s, %s' % ('%17s', '%s', '%s')
                    c = 'cyan, white, gray'
                    d = 'lite, lite, bold'
                    prfmt_mc_row(v, f, c, d)

                except IndexError, e:
                    if x == 'anon':
                        msg = '<< Config Error: anon MUST be a single uid >>'
                        print_fail(msg)
                    else:
                        emsg = str(e)
                        v = '%s, %s, %s' % (x, '=', emsg)
                        f = '%s, %s, %s' % ('%17s', '%s', '%s')
                        c = 'cyan, white, red'
                        d = 'lite, lite, bold'
                        prfmt_mc_row(v, f, c, d)
            print

    if mode == 'summary':
        if  numshares > 0:
            prfmt_bold(svc, '%6s', 'green', False)
            prfmt_bold(numshares, '%10d', 'cyan', False)
            NFSData = True
        else:
            NFSData = False


def print_nfs_srv_hdr(mode):
    if mode == 'verbose':
        prfmt_mc_row('setting, value',
                 '%22s, %16s',
                 'white, white',
                 'bold, bold')

        prfmt_mc_row('-------, ------',
                 '%22s, %16s',
                 'white, white',
                 'bold, bold')


NTL = 0
def print_nfsd(thrds):
    global PSL
    global NTL
    prfmt_lite(' ', '%s', 'white', False)
    NTL = len(thrds)
    if NTL == 4:
        if PSL == 11:
            f = '%4s'
        elif PSL == 5:
            f = '%7s'
        else:
            f = '%s'
        prfmt_lite(' ', f, 'white', False)
        fmt = '%4s'
    elif NTL == 3:
        if PSL == 11:
            f = '%4s'
        elif PSL == 5:
            f = '%7s'
        else:
            f = '%s'
        prfmt_lite(' ', f, 'white', False)
        fmt = '%4s'
    elif NTL == 2:
        if PSL == 17:
            f = '%2s'
        elif PSL == 11:
            f = '%4s'
        elif PSL == 5:
            f = '%8s'
        else:
            f = '%s'
        prfmt_lite(' ', f, 'white', False)
        fmt = '%2s'
    else:
        fmt = '%s'
    prfmt_lite(thrds, fmt, 'green', False)
    return


def print_lockd(thrds):
    global NTL

    lklen = len(thrds)
    if lklen == 4:
        if NTL == 4:
            f = '%10s'
        elif NTL == 3:
            f = '%5s'
        else:
            f = '%7s'
        prfmt_lite(' ', f, 'white', False)
        fmt = '%4s'
    elif lklen == 3:
        if NTL == 4:
            f = '%9s'
        elif NTL == 3:
            f = '%9s'
        else:
            f = '%13s'
        prfmt_lite(' ', f, 'white', False)
        fmt = '%4s'
    elif lklen == 2:
        if NTL == 4:
            f = '%8s'
        elif NTL == 3:
            f = '%9s'
        else:
            f = '%10s'
        prfmt_lite(' ', f, 'white', False)
        fmt = '%4s'
    else:
        fmt = '%s'
    prfmt_lite(thrds, fmt, 'green', False)


def print_nfs_srv_cfg(mode):
    global base
    global NFSData
    File = os.path.join(base, 'ingestor/json/sharectl-get-nfs.out.json')

    try:
        with open(File) as f:
            data = json.load(f)

    except Exception, e:
        print 'Exception %s raised' % str(e)
        return

    print_nfs_srv_hdr(mode)
    if mode == 'verbose':
        for c in sorted(data):
            sc = 'white'
            if c == 'server_delegation':
                sc = 'green' if data[c] == 'on' else 'red'

            if c == 'grace_period':
                sc = 'green' if int(data[c]) >= 90 else 'red'
            v = '%s, %s' % (c, data[c])
            f = '%s, %s' % ('%25s', '%12s')
            c = 'white, %s' % sc
            d = 'lite,  bold'
            prfmt_mc_row(v, f, c, d)
    else:
        if NFSData == True:
            print_nfsd(data['servers'])
            print_lockd(data['lockd_servers'])
    print


def print_proto_hdr(proto):
    print_bold('\t' + proto + ':', 'blue', True)

    v = '%s, %s, %s' % ('ops', 'calls', 'pcnt')
    f = '%s, %s, %s' % ('%20s', '%15s', '%10s')
    c = 'white, white, white'
    d = 'bold, bold, bold'
    prfmt_mc_row(v, f, c, d)

    opl = '-'*10
    cll = '-'*12
    ptl = '-'*7
    v = '%s, %s, %s' % (opl, cll, ptl)
    f = '%s, %s, %s' % ('%20s', '%15s', '%10s')
    c = 'white, white, white'
    d = 'bold, bold, bold'
    prfmt_mc_row(v, f, c, d)
    return


nfs2_ops = ['create', 'getattr', 'link', 'lookup', 'mkdir', 'null', 'read',    \
            'readdir', 'readlink', 'remove', 'rename', 'rmdir', 'root',        \
            'setattr', 'statfs', 'symlink', 'wrcache', 'write' ]

nfs3_ops = ['access', 'commit', 'create', 'fsinfo', 'fsstat', 'getattr',       \
            'link', 'lookup', 'mkdir', 'mknod', 'null', 'pathconf', 'read',    \
            'readdir', 'readdirplus', 'readlink', 'remove', 'rename',          \
            'rmdir', 'setattr', 'symlink', 'write']

nfs4_ops = ['access', 'close', 'commit', 'create', 'delegpurge', 'delegreturn',\
            'getattr', 'getfh', 'link', 'lock', 'lockt', 'locku', 'lookup',    \
            'lookupp', 'nverify', 'open', 'open_confirm', 'open_downgrade',    \
            'openattr', 'putfh', 'putpubfh', 'putrootfh', 'read', 'readdir',   \
            'readlink', 'release_lockowner', 'remove', 'rename', 'renew',      \
            'restorefh', 'savefh', 'secinfo', 'setattr', 'setclientid',        \
            'setclientid_confirm', 'verify', 'write']


PSL = ''
def print_nfs_srv_stats(mode):
    global base
    global NFSData
    global PSL
    File = os.path.join(base, 'ingestor/json/nfsstat-s.out.json')

    try:
        with open(File) as f:
            data = json.load(f)

    except Exception, e:
        print 'Exception %s raised' % str(e)
        return

    proto_list = []
    op = {}
    for ln in data:
        patt = 'nfsv(\d+)'
        mp = re.match(patt, ln)
        if mp:
            vers = mp.group(1)
            proto = 'nfsv' + vers

            calls = data[ln]['stats']['calls']
            badcl = data[ln]['stats']['badcalls']
            ic = int(calls)
            bc = int(badcl)

            if ic > 0 or bc > 0:
                proto_list.append(proto)

            if vers == '2':
                v = vers
                op[v] = {}
                for n in nfs2_ops:
                    op[v][n] = {}
                    op[v][n]['calls'] = data[ln][vers][n]['calls']
                    op[v][n]['prcnt'] = data[ln][vers][n]['prcnt']

            elif vers == '3':
                v = vers
                op[v] = {}
                for n in nfs3_ops:
                    op[v][n] = {}
                    op[v][n]['calls'] = data[ln][vers][n]['calls']
                    op[v][n]['prcnt'] = data[ln][vers][n]['prcnt']

            elif vers == '4':
                v = vers
                op[v] = {}
                for n in nfs4_ops:
                    op[v][n] = {}
                    op[v][n]['calls'] = data[ln][vers]['operations'][n]['calls']
                    op[v][n]['prcnt'] = data[ln][vers]['operations'][n]['prcnt']


    if mode == 'summary' and NFSData == True:
        prfmt_lite(' ', '%5s', 'white', False)
        plst = sorted(proto_list)
        plen = len(plst)
        pstr = ''.join(x + ',' for x in plst).rstrip(',')
        PSL = len(pstr)
        if plen == 1:
            prfmt_lite(' ', '%5s', 'white', False)
            fmt = '%5s'
        elif plen == 2:
            prfmt_lite(' ', '%2s', 'white', False)
            fmt = '%11s'
        elif plen == 3:
            fmt = '%s'
        else:
            pstr = '< No proto data >'
            PSL = len(pstr)
            prfmt_bold(pstr, '%s', 'red', False)
            return
        prfmt_lite(pstr, fmt, 'green', False)
    else:
        for p in sorted(proto_list):
            P = str(p)
            print_proto_hdr(p)
            vers = P[-1]
            if vers == '2':
                ops = nfs2_ops
            elif vers == '3':
                ops = nfs3_ops
            else:
                ops = nfs4_ops
            for O in ops:
                nfsop = O
                calls = op[vers][O]['calls']
                prcnt = op[vers][O]['prcnt']
                if prcnt == '0%':
                    continue
                v = '%s, %s, %s' % (nfsop, calls, prcnt)
                f = '%s, %s, %s' % ('%20s', '%15s', '%10s')
                c = 'white, white, yellow'
                d = 'bold,  lite, lite'
                prfmt_mc_row(v, f, c, d)
            print
        print


def nfs_enabled():
    global base
    File = os.path.join(base,   \
        'ingestor/json/svccfg-s-svcnetworknfsserverdefault-listprop.out.json')

    try:
        with open(File) as f:
            data = json.load(f)

    except Exception, e:
        print 'Exception %s raised' % str(e)
        return

    if 'general' in data:
        if 'enabled' in data['general']:
            if data['general']['enabled'] == 'true':
                return True
    return False


def nfs_sharing():
    global base
    File = os.path.join(base, 'ingestor/json/zfs-get-nfs.out.json')

    try:
        with open(File) as f:
            dfshares  = json.load(f)

    except Exception, e:
        # If the file doesn't exist, we're not sharing anything
        return False

    if len(dfshares) > 0:
        return True
    return False


def NFS(mode):
    if nfs_enabled() and nfs_sharing():
        print_svcs_hdr(mode)
        print_zfs_nfs(mode)
        print_nfs_srv_stats(mode)
        print_nfs_srv_cfg(mode)


def services(mode):
    print_header('Appliance Services')
    NFS(mode)


def disk_heuristics(dev, tput):

    if tput >= 150:         # threshold: 150 MB/s; flag anything slower
        prfmt_lite(dev, '%25s', 'green', False)
        prfmt_bold('PASS', '%33s', 'green', True)
    else:
        prfmt_lite(dev, '%25s', 'red', False)
        prfmt_bold('FAIL', '%33s', 'red', True)

    return
 

def sac_results():
    global base

    Dir = os.path.join(base, 'go-live')
    if not os.path.exists(Dir):
        return

    if not os.listdir(Dir):     # simply return if go-live dir is empty
        return

    jfiles = []
    Files = os.listdir(Dir)
    for f in Files:
        if f.endswith('json'):
            jfiles.append(f)

    if len(jfiles) == 0:
        return

    json_files = sorted(jfiles)
    File = os.path.join(Dir, json_files[-1])    # newest json file
    try:
        with open(File) as f:
            sacres = json.load(f)

    except Exception, e:
        print 'Exception %s raised' % str(e)
        return

    print_header('SAC Results')
    for r in sacres['results']:
        c = Colors()
        print '\t', c.bold_white + r + c.reset, '\t',

        expt = ''
        try:
            if 'exception' in sacres['results'][r]:
                if sacres['results'][r]['exception'] == False:
                    expt = False
                else:
                    s = '%19s' if r == 'check_rsf_failover_from' else '%27s'
                    prfmt_bold('FAIL', s, 'red', True)
                    msg = sacres['results'][r]['exception_str']
                    print_fail('\t\t\t' + msg)
                    continue
        except TypeError:
            l = len(r)
            if r == 'check_domain_ping':
                x = 45
            elif r == 'check_rsf_failover_to':
                x = 49
            elif r == 'check_rsf_failover_from':
                x = 43
            n = x - l
            s = '%' + '%d' % n + 's'
            prfmt_bold('No Data', s, 'yellow', True)
            continue

        if 'status' in sacres['results'][r]:
            if sacres['results'][r]['status'] == True:
                if not expt:
                    if r == 'check_time_delta':
                        # time_delta threshold == 5s
                        dlt = sacres['results'][r]['delta']
                        if dlt > 5:         # flag if time diff is > 5s
                            prfmt_fail('FAIL', '%27s')
                        else:
                            prfmt_pass('PASS', '%27s')
                        continue

                    if len(r) <= 12:
                        prfmt_pass('PASS', '%35s')
                    else:
                        prfmt_pass('PASS', '%27s')
                else:
                    if len(r) <= 12:
                        # XXX - still need to be unit tested
                        prfmt_fail('[FAIL]', '%38s')
                    else:
                        # XXX - still need to be unit tested
                        prfmt_fail('(FAIL)', '%30s')
            else:
                if not expt:
                    prfmt_fail('FAIL', '%35s')
                    try:
                        msg = sacres['results'][r]['output']
                        print_fail('\t\t' + msg)
                    except KeyError:
                        print_fail('\t\t\tUnable to retrieve failure message')
                    continue
        else:
            print ''
            for k in sacres['results'][r].keys():
                if k == 'exception':
                    continue
                if 'status' in sacres['results'][r][k]:
                    if sacres['results'][r][k]['status'] == True:
                        if not expt:
                            if r == 'check_disk_perf':
                                tput = sacres['results'][r][k]['tput']
                                disk_heuristics(k, tput)
                                continue
                            else:
                                print '%25s' % k,
                                prfmt_pass('PASS', '%33s')

                        else:
                            # XXX - still need to be unit tested
                            print '%25s' % k,
                            prfmt_fail('<FAIL>', '%35s')
    print ''


def orchestrator():
    global as_vmode
    global zp_vmode
    global sac_res

    process_cs()
    vendor_cpu()
    memory()
    dump_dev()
    max_cstates()

    get_opthac()
    zp_list(zp_vmode)       # pass in 'verbose' to zp_list() for full output
    jbods()
    hddko()
    network()
    faults()
    services(as_vmode)
    if sac_res:
        sac_results()


def lookup_by_lkey(dbfile, lkey):

    if not os.path.exists(dbfile):
        return None

    fd = gzip.open(dbfile, 'rb')
    try:
        for l in fd:
            line = l.split('|')

            try:
                cname = line[1]
                email = line[2].split('@')[1]
                licen = line[3]
                mchid = line[4]
                custy = line[-3]

            except IndexError:      # badly formated line in DB
                pass

            if lkey == licen:
                if custy:
                    if custy == 'Yes' or custy == 'No':
                        customer = email
                    else:
                        customer = custy
                else:
                    customer = email

                return customer

    finally:
        fd.close()

    return None


def lookup_by_machid(dbfile, lkey):

    if not os.path.exists(dbfile):
        return None

    lkmid = lkey.split('-')[2]

    fd = gzip.open(dbfile, 'rb')
    try:
        for l in fd:
            line = l.split('|')

            try:
                cname = line[1]
                email = line[2].split('@')[1]
                licen = line[3]
                mchid = line[4]
                custy = line[-3]

            except IndexError:      # badly formated line in DB
                pass

            if lkmid == mchid:
                if custy:
                    if custy == 'Yes' or custy == 'No':
                        customer = email
                    else:
                        customer = custy
                else:
                    customer = email
                return customer

    finally:
        fd.close()

    return None


def guess_from_cs():
    global base
    File = os.path.join(base, 'collector.stats')

    for l in read_raw_txt(File):
        if l.startswith('Hostname:'):
            f = l.split()[-1]

            patt = '^\((\S+)\)$'
            mp = re.match(patt, f)
            if mp:
                fqhn = mp.group(1)
                try:
                    return fqhn.split('.')[-2]

                except IndexError:
                    return fqhn

    return None


def get_custy_info(lkey):

    DBFile = "./DB/product_reg.db.ryuji.gz"

    custy = lookup_by_lkey(DBFile, lkey)
    if custy is None:
        custy = lookup_by_machid(DBFile, lkey)

        if custy is None:
            custy = guess_from_cs()

    return custy


#
# Dark-Site Support
#
currdir = os.getcwd()
basedir = '/mnt/carbon-steel'
uplddir = os.path.join(basedir, 'upload')
ingtdir = os.path.join(basedir, 'ingested')
tarfile = ''
datestr = time.strftime('%Y-%m-%d', time.localtime())


def prep_tree():
    if not os.path.exists(basedir):
        os.mkdir(basedir)

    if not os.path.exists(uplddir):
        os.mkdir(uplddir)

    return


def collector_for_this_node():
    global tarfile

    print_debug('The following step', False)
    print_warn('WILL', False)
    print_debug('take time... please be patient !\n', True)

    print_bold('Generating Local Collector Bundle...\t', 'white', False)

    cmd = '/bin/nexenta-collector --no-upload'
    fd = os.popen(cmd)

    for line in fd:
        if not line.startswith('Result'):
            continue
    
        patt = '^Result file:\s+(\S+)$'
        mp = re.match(patt, line)
        if mp:
            collector_file = mp.group(1)
            cf = os.path.basename(collector_file)
            new_loc = os.path.join(uplddir, cf)
            
            tarfile = new_loc
            os.rename(collector_file, new_loc)

    print_pass('Done')
    return


def ingest_in_background():
    global tarfile
    nza_ingdir = '.'
    nzingestor = os.path.join(nza_ingdir, 'NZA_Ingestor.py')

    print_bold('Ingesting Local Collector Bundle...\t', 'white', False)
    os.chdir(nza_ingdir)
    cmd = nzingestor + ' --ingest ' + tarfile
    fd = os.popen(cmd)

    for line in fd:
        if not line.startswith('Ingestion'):
            continue
        print line

    print_pass('Done')
    return


def find_ingestion_dir():
    global datestr

    idir = ''
    line = os.path.basename(tarfile)
    patt = '^(\S+T)\.\d+\.tar\.gz$'
    mp = re.match(patt, line)
    if mp:
        idir = mp.group(1)
    else:
        print_fail('Could NOT decipher correct ingestion directory')
        sys.exit(1)

    return os.path.join(os.path.join(ingtdir, datestr), idir)
    

def dark_site():
    prep_tree()
    collector_for_this_node()
    ingest_in_background()

    return find_ingestion_dir()


def volun_to_vdev(vol, lun):
    File = os.path.join(base, 'ingestor/json/zpool-status-dv.out.json')
    
    if not os.path.exists(File):
        return None

    with open(File) as f:
        zpstat = json.load(f)

    for pool in zpstat:
        if pool != vol:
            continue

        pname = zpstat[pool]['config'][pool]
        for x in pname['vdev']:
            if 'vdev' in pname['vdev'][x]:
                vdev = pname['vdev'][x]['vdev']
            else:
                vdev = pname['vdev']

            for l in vdev:
                L = l.lower()
                if L == lun:
                    return x.split('-')[0]

                #
                # XXX - will need to test this against other collector
                #       bundles to make sure we do get all devices.
                #
                patt = '^(spare.*)'
                mp = re.match(patt, L)
                if mp:
                    nl = mp.group(1)
                    s9 = zpstat[pool]['config'][pool]['vdev'][x]['vdev'][nl]
                    
                    for v in s9['vdev']:
                        state = s9['vdev'][v]['state']

                        if state != 'ONLINE':
                            return 'Fault'
                        else:
                            return x.split('-')[0]
    
        # couldn't find it under pool, let's check other pool vdevs
        vdevs = ['cache', 'logs', 'spares']
        for v in vdevs:
            try:
                pname = zpstat[pool]['config'][v]
            except KeyError:
                continue

            vdev = pname['vdev']
            for d in vdev:
                if d == lun:
                    return v.split('-')[0]


def lun_to_zvol(lun):
    File = os.path.join(base, 'ingestor/json/nmc-c-show-lun-smartstat.out.json')
    
    if not os.path.exists(File):
        return None

    with open(File) as f:
        lunsmart = json.load(f)

    for vol in lunsmart:
        for l in lunsmart[vol]['luns']:
            if l.lower() == lun:
                return vol


def CI_Disk_1():
    global base
    global hc_vmode
    File = os.path.join(base, 'ingestor/json/iostat-en.out.json')

    if not os.path.exists(File):
        return

    print_header('CI-Disk-1')
    with open(File) as f:
        iostat = json.load(f)

    primed = False
    for lun in sorted(iostat):
        vol = lun_to_zvol(lun)
        vdev = volun_to_vdev(vol, lun)
        if not primed:
            ll = lun
            try:
                lv = iostat[lun]['vendor']
                vc = 1
                ls = iostat[lun]['size:']
                sc = 1
                lp = iostat[lun]['product']
                pc = 1
                lr = iostat[lun]['revision']
                rc = 1
            except KeyError:
                continue

            if hc_vmode == 'verbose':
                prfmt_mc_row('%s, %s, %s, %s, %s, %s, %s' %
                            (ll, lv, lp, lr, ls, vol, vdev),
                            ' %10s,   %8s,  %16s,   %5s,  %10s,   %5s,   %5s',
                            'white, white, white, white, white, white, white',
                            ' bold,  bold,  bold,  bold,  bold,  bold,  bold')

            primed = True
            continue

        try:
            vr = iostat[lun]['vendor']
            pr = iostat[lun]['product']
            sz = iostat[lun]['size:']
            rv = iostat[lun]['revision']
        except KeyError:
            continue

        same_v = False
        if lv == vr:
            same_v = True
        else:
            vc += 1

        same_p = False
        if lp == pr:
            same_p = True
        else:
            pc += 1

        same_s = False
        if ls == sz:
            same_s = True
        else:
            sc += 1

        same_r = False
        if lr == rv:
            same_r = True
        else:
            rc += 1

        if hc_vmode == 'verbose':

            if same_v and same_p and same_s and same_r:
                col = 'red' if vol is None else 'white'
                prfmt_mc_row('%s, %s, %s, %s, %s, %s, %s' %
                    (lun, vr, pr, rv, sz, vol, vdev),
                    ' %10s,   %8s,  %16s,   %5s,  %10s,   %5s,   %5s',
                    'white, white, white, white, white,    %s, white' % col,
                    ' bold,  bold,  bold,  bold,  bold,  bold,  bold')

            else:
                prfmt_bold(lun, '%10s', 'white', False)

                if same_v:
                    prfmt_bold(vr, '%8s', 'white', False)
                else:
                    prfmt_bold(vr, '%8s', 'yellow', False)

                if same_p:
                    prfmt_bold(pr, '%16s', 'white', False)
                else:
                    prfmt_bold(pr, '%16s', 'yellow', False)

                if same_r:
                    prfmt_bold(rv, '%5s', 'white', False)
                else:
                    prfmt_bold(rv, '%5s', 'yellow', False)
            
                if same_s:
                    prfmt_bold(sz, '%10s', 'white', False)
                else:
                    prfmt_bold(sz, '%10s', 'yellow', False)

                if vol is None:
                    tint = 'red'
                else:
                    tint = 'white'
                prfmt_bold(vol, '%5s', '%s' % tint, False)
                prfmt_bold(vdev, '%5s', '%s' % tint, True)

        ll = lun
        lv = vr
        ls = sz
        lp = pr
        lr = rv

    if vc > 1 or pc > 1 or sc > 1:
        if hc_vmode == 'verbose':
            print ''

        msg1 = 'WARNING: Disks in system span %d vendors, ' % vc
        msg2 = '%d products, %d sizes and %d f/w revs\n' %  (pc, sc, rc)
        print_warn(msg1 + msg2, True)

    return


def health_check():
    global base

    print_bold('Initiating Health Check...', 'white', False)
    CI_Disk_1()
    return


def invalid_flag(parser, mode, modstr):
    print_warn('\n\t' + mode, False)
    print 'is not a valid option for',
    msg = '\'--%s\'\n' % modstr
    print_bold(msg, 'white', True)
    parser.print_help()
    sys.exit(2)


def main():
    global base
    global as_vmode
    global zp_vmode
    global hc_vmode
    global sac_res

    c = Colors()

    parser = optparse.OptionParser(usage='%prog ' + c.bold_white +          \
        '--path ' + c.reset + 'collector_bundle_dir ' + '[ ' +              \
        c.bold_white + '--zpmode' + c.reset + ' (\'summary\'|\'verbose\') ]'\
        + '\n' + 16*' ' +  '[ ' + c.bold_white + '--asmode' + c.reset +     \
        ' (\'summary\'|\'verbose\') ]' + ' [ ' + c.bold_white + '--sac' +   \
        c.reset + ' ]' +  \
        '\n' + 7*' '+ 'nxcat.py' + c.bold_white + ' --dark-site' + c.reset  \
        + '\n' + 7*' ' + 'nxcat.py' + c.bold_white + ' --path' + c.reset +  \
        ' collector_bundle_dir' + c.bold_white + ' --health-check' + c.reset\
        + '\n' + 16*' ' + '[ ' + c.bold_white + '--hvmode' + c.reset +      \
        ' (\'summary\'|''\'verbose\') ]')

    parser.add_option('--path', dest='path', type='str', default=None,
        help='Fully qualified path to already ingested collector bundle ' + \
        'directory', metavar='BundlePath', nargs=1)
    parser.add_option('--zpmode', dest='zvmode', type='str', default='summary',
        help='\'summary\' or \'verbose\' mode for Zpool Information',
        metavar='zpmode', nargs=1)
    parser.add_option('--asmode', dest='asmode', type='str', default='summary',
        help='\'summary\' or \'verbose\' mode for Appliance Services Info',
        metavar='asmode', nargs=1)
    parser.add_option('--sac', action="store_true", default=False,
        help='Show SAC results for bundles that were successfully autosac\'ed',
        metavar=None)
    parser.add_option('--dark-site', action="store_true", default=False,
        help='For use in Dark Sites: Automatically generates, ingests and ' +\
        'analyzes the newly generated bundle', metavar=None)
    parser.add_option('--health-check', action="store_true", default=False,
        help='Perform Health Check as per Appendix C procedures of SOW; ' + \
        'mutually exclusive to --zpmode and --sac options', metavar=None)
    parser.add_option('--hvmode', dest='hvmode', type='str', default='summary',
        help='\'summary\' or \'verbose\' mode for Health Check Status',
        metavar='hcmode', nargs=1)

    (options_args, args) = parser.parse_args()

    #pprint(options_args)

    dark = options_args.dark_site
    if dark:
        base = dark_site()

    elif options_args.path is not None:
        base = options_args.path

        if options_args.health_check:
            if  options_args.sac:
                print_warn('\n\t' + 'Options --health-check ' + \
                    'and --sac are mutually exclusive !\n', True)
                sys.exit(0)
            
            hc_vmode = options_args.hvmode
            health_check()
            sys.exit(0)

        sac_res = options_args.sac
    else:
        parser.print_help()
        sys.exit(1)

    if not dark:
        zp_vmode = options_args.zvmode
        if zp_vmode != 'summary' and zp_vmode != 'verbose':
            invalid_flag(parser, zp_vmode, 'zpmode')

        as_vmode = options_args.asmode
        if as_vmode != 'summary' and as_vmode != 'verbose':
            invalid_flag(parser, as_vmode, 'asmode')

    orchestrator()


#
# Boilerplate
#
if __name__ == '__main__':
    main()


# pydoc
__author__ = "Rick Mesta"
__copyright__ = "Copyright 2015 Nexenta Systems, Inc. All rights reserved."
__credits__ = ["Rick Mesta"]
__license__ = "undefined"
__version__ = "$Revision: " + _ver + " $"
__created_date__ = "$Date: 2015-05-18 18:57:00 +0600 (Mon, 18 Mar 2015) $"
__last_updated__ = "$Date: 2016-12-02 10:43:00 +0600 (Fri, 02 Dec 2016) $"
__maintainer__ = "Rick Mesta"
__email__ = "rick.mesta@nexenta.com"
__status__ = "Production"
