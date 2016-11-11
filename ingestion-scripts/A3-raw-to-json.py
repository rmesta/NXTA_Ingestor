#!/usr/bin/env python

"""
Rick Mesta <rick.mesta@nexenta.com>
Copyright 2015 Nexenta Systems, Inc. All rights reserved.

Central script to convert all raw text files of interest into
their json counterparts, for their eventual absorption in the
Nexenta dashboard.
"""

import sys
import json
import time
import tarfile
import inspect
from pprint import pprint               # pretty printing
from functions import *                 # local functions.py file

r2j_ver = '1.0.0'
Debug = False
vcdbg = True

# name of this script
script_name = 'A3-raw-to-json.py'


def caller():
    return inspect.stack()[2][3]


def valid_collector_output(fname):
    raw_file = fname + '.out'
    tgz_file = fname + '.tar.gz'
    stt_file = fname + '.stats'
    src_file = raw_file

    called_by = caller()
    if called_by == 'opthac_json':
        src_file = tgz_file
        vostat = valid_tar_gz(fname)

    elif called_by == 'fma_faults_json':
        vostat = valid_out_gz(fname)

    elif called_by == 'lun_smartstat_json':
        vostat = valid_output(fname, True)

    else:
        vostat = valid_output(fname)

    if vostat != Errors.e_ok:
        if vostat == Errors.e_nzrc:
            if vcdbg:
                print 'Non-Zero return code: ' +    \
                    'refer to', stt_file, 'for additional info'
            return False

        elif vostat == Errors.e_noent:
            if vcdbg:
                print src_file, 'does not exist... skipping'
            return False

        elif vostat == Errors.e_mpty:
            if vcdbg:
                print src_file, 'is empty... skipping'
            return False

        else:
            if vcdbg:
                if vostat != Errors.e_tok and   \
                   vostat != Errors.e_zok and   \
                   vostat != Errors.e_stok:
                    print '%s error = %d' % (called_by, vostat)

    return True


def aptsrc_jsp(srcslist):
    idx = 1
    jsp = {'repos': {}}                # json encoded data string
    for i in read_raw_txt(srcslist):
        key = 'repo-' + str(idx)
        row = {}                        # each repo represents one row
        for l in i.split():
            patt = '^(deb[a-zA-Z0-9-_]*)$'
            mp = re.match(patt, l)
            if mp:
                row['title'] = mp.group(1)
                continue

            patt = '^(http.*)$'
            mp = re.match(patt, l)
            if mp:
                row['link'] = mp.group(1)
                continue

            patt = '^([a-zA-Z0-9_]+)-([a-zA-Z0-9_]+)$'
            mp = re.match(patt, l)
            if mp:
                if mp.group(1) == 'non' and mp.group(2) == 'free':
                    row['perks'] = mp.group(1) + '-' + mp.group(2)
                    continue
                row['osrel'] = mp.group(1) + '-' + mp.group(2)
                continue

            patt = '^(main)$'
            mp = re.match(patt, l)
            if mp:
                row['branch'] = mp.group(1)
                continue

            patt = '^(contrib)$'
            mp = re.match(patt, l)
            if mp:
                row['repcon'] = mp.group(1)
                continue

        jsp['repos'][key] = row
        idx += 1

    return jsp


def aptsrc_json(bdir):
    fname = os.path.join(bdir, 'appliance/sources.list')
    jsout = fname + '.json'
    if not valid_file(fname):
        return
    jsdct = aptsrc_jsp(fname)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def nmchkpt_jsp(fname):
    hdrs = []
    for e in read_raw_txt(fname)[0].split():
        pattern = '[A-Z-]+'
        mp = re.match(pattern, e)
        if mp:
            hdrs.append(mp.group(0).lower())

    data = []
    for d in read_raw_txt(fname):
        patt = '^rootfs.*'
        mp = re.match(patt, d)
        if mp:
            data.append(mp.group(0))

    idx = len(data)
    json_data = {'checkpoints': {}}
    for d in data:
        key = 'chkpt-' + str(idx)
        new = {}

        patt1 = '([\w-]+)\s+([a-zA-Z]+\s*\d+\s*\d+:\d+\s*\d+)'
        patt2 = '\s+(\w+)\s+(\w+)\s+(\w+)\s+([0-9A-Z.-]+)$'
        pattern = patt1 + patt2
        mp = re.match(pattern, d)
        if mp:
            for i in xrange(0, len(hdrs)):
                new[hdrs[i]] = mp.group(i + 1)

        idx -= 1
        json_data['checkpoints'][key] = new

    return json_data


def nmchkpt_json(bdir):
    fname = os.path.join(bdir, 'appliance/nmc-c-show-appliance-checkpoint')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = nmchkpt_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def hddisco_json(bdir):
    fname = os.path.join(bdir, 'disk/hddisco')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = hddisco(bdir)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def process_devid(ln):
    """
    Given line similar to:

    c0t5000C5005EC60D43d0 Soft Errors: 0 Hard Errors: 0 Transport Errors: 0

    ... process it and return a key/value pair dictionary
    """
    kvp = {}
    patt = '^(\w+)\s+.*$'
    mp = re.match(patt, ln)
    if mp:
        devid = mp.group(1)
    else:
        print "Fatal error parsing dev line"
        sys.exit(-1)
    kvp['devid'] = devid.lower()

    patt = '^\w+\s+([a-zA-Z0-9\s]*):\s+(\d+).*$'
    mp = re.match(patt, ln)
    if mp:
        softe = mp.group(1)
        value = mp.group(2)
    else:
        print "Fatal error parsing soft errors"
        sys.exit(-1)
    kvp[softe.lower()] = value.lower()

    patt1 = '^\w+\s+[a-zA-Z0-9\s]*:\s+\d+\s+'
    patt2 = '([a-zA-Z0-9\s]*):\s+(\d+).*$'
    patt = patt1 + patt2
    mp = re.match(patt, ln)
    if mp:
        harde = mp.group(1)
        nvalu = mp.group(2)
    else:
        print "Fatal error parsing hard errors"
        sys.exit(-1)
    kvp[harde.lower()] = nvalu.lower()

    patt1 = '^\w+\s+[a-zA-Z0-9\s]*:\s+\d+\s+[a-zA-Z0-9\s]*:\s+\d+'
    patt2 = '\s+([a-zA-Z0-9\s]*):\s+(\d+)$'
    patt = patt1 + patt2
    mp = re.match(patt, ln)
    if mp:
        xprte = mp.group(1)
        xprvl = mp.group(2)
    else:
        print "Fatal error parsing transport errors"
        sys.exit(-1)
    kvp[xprte.lower()] = xprvl.lower()

    return kvp


def process_vendor(l):
    """
    Given list of items similar to:

    ['Vendor:', 'ATA', 'Product:', 'ST1000NM0011', 'Revision:', 'SN03',
     'Serial', 'No:']
    """
    kvp = {}
    lst = [x.strip() for x in l]        # remove leading/trailing \s

    l = len([x.strip(':').lower() for x in lst])
    if l == 8:
        try:                        # now remove any ':' from the fields
            V, v, P, p, R, r, S, s = [x.strip(':').lower() for x in lst]
        except ValueError:
            print "process_vendor: no serial # provided"
        no = ''
    elif l == 9:
        try:                        # now remove any ':' from the fields
            V, v, P, p, R, r, S, s, no = [x.strip(':').lower() for x in lst]
        except ValueError:
            print "process_vendor: serial # provided"
    elif l == 10:
        try:
            V, v, P, X, Y, R, r, S, s, no = [x.strip(':').lower() for x in lst]
        except ValueError:
            print "process_vendor: product in multiple strings"
        p = X + ' ' + Y
    elif l == 13:
        try:
            V, v, P, X, Y, R, r, S, no, Sz, sz, N, n =  \
                [x.strip(':').lower() for x in lst]
            s = ''
        except ValueError:
            print "process_vendor: product in multiple strings"
        p = X + ' ' + Y
    else:
        try:
            V, v, P, X, Y, y, R, r, S, s, no =  \
                [x.strip(':').lower() for x in lst]
            p = X + ' ' + Y
        except ValueError:
            try:
                V, v, P, p, R, r, S, s, Z, z =  \
                    [x.strip(':').lower() for x in lst]
                no = None
            except ValueError:
                print "process_vendor: Cannot decode vendor string"
                return None

    kvp[V] = v      # Vendor
    kvp[P] = p      # Product
    kvp[R] = r      # Revision
    sn = S + ' ' + s
    kvp[sn] = no    # Serial No.

    return kvp


def process_mederr_devrdy(ln):
    """
    Given line similar to:

    Media Error: 0 Device Not Ready: 0 No Device: 0 Recoverable: 0

    ... process it and return a key/value pair dictionary
    """
    kvp = {}
    patt = '^(\w+\s+\w+):\s+(\d+).*$'   # Media Error: 0
    mp = re.match(patt, ln)
    if mp:
        mederr = mp.group(1)
        errval = mp.group(2)
    else:
        print "Fatal error parsing media error line"
        sys.exit(-1)
    kvp[mederr.lower()] = errval.lower()

    patt1 = '^\w+\s+\w+:\s+\d+\s+'
    patt2 = '([a-zA-Z0-9\s]*):\s+(\d+).*$'
    patt = patt1 + patt2                # Device Not Ready: 0
    mp = re.match(patt, ln)
    if mp:
        devrdy = mp.group(1)
        isredy = mp.group(2)
    else:
        print "Fatal error parsing device readiness errors"
        sys.exit(-1)
    kvp[devrdy.lower()] = isredy.lower()

    patt1 = '^[a-zA-Z0-9\s]*:\s+\d+\s+[a-zA-Z0-9\s]*:\s+\d+\s+'
    patt2 = '([a-zA-Z0-9\s]*):\s+(\d+).*$'
    patt = patt1 + patt2                # No Device: 0
    mp = re.match(patt, ln)
    if mp:
        device = mp.group(1)
        exists = mp.group(2)
    else:
        print "Fatal error parsing device existence line"
        sys.exit(-1)
    kvp[device.lower()] = exists.lower()

    patt1 = '^[a-zA-Z0-9\s]*:\s+\d+\s+[a-zA-Z0-9\s]*:\s+\d+\s+'
    patt2 = '[a-zA-Z0-9\s]*:\s+\d+\s+([a-zA-Z0-9\s]*):\s+(\d+).*$'
    patt = patt1 + patt2                # Recoverable: 0
    mp = re.match(patt, ln)
    if mp:
        recovr = mp.group(1)
        isrecv = mp.group(2)
    else:
        print "Fatal error parsing device recoverability line"
        sys.exit(-1)
    kvp[recovr.lower()] = isrecv.lower()

    return kvp


def process_illreq_pfa(ln):
    """
    Given line similar to:

    Illegal Request: 4075154 Predictive Failure Analysis: 0

    ... process it and return a key/value pair dictionary
    """
    kvp = {}
    patt = '^(\w+\s+\w+):\s+(\d+).*$'   # Illegal Request: <num>
    mp = re.match(patt, ln)
    if mp:
        illreq = mp.group(1)
        rqstct = mp.group(2)
    else:
        print "Fatal error parsing illegal request line"
        sys.exit(-1)
    kvp[illreq.lower()] = rqstct.lower()

    patt1 = '^\w+\s+\w+:\s+\d+\s+'
    patt2 = '([a-zA-Z0-9\s]*):\s+(\d+).*$'
    patt = patt1 + patt2                # Predictive Failure Analysis: 0
    mp = re.match(patt, ln)
    if mp:
        pfatxt = mp.group(1)
        pfacnt = mp.group(2)
    else:
        print "Fatal error parsing predictive failure analysis line"
        sys.exit(-1)
    kvp[pfatxt.lower()] = pfacnt.lower()

    return kvp


def iostat_jsp(fname):
    iostat = {}

    for line in read_raw_txt(fname):
        # If the line begins with 'c', process device id
        if line.startswith('c'):
            devnerrs = process_devid(line.strip())
            if Debug:
                print "devnerrs: ", devnerrs
            devid = devnerrs['devid']
            iostat[devid] = {}
            for k in sorted(devnerrs.keys()):
                if k == 'devid':
                    continue
                iostat[devid][k] = devnerrs[k]

        # Parse Vendor information
        elif line.startswith('V'):
            lst = [x.strip() for x in line.split()]
            vdrprodrev = process_vendor(lst)
            if vdrprodrev is not None:
                if Debug:
                    print 'vdrprodrev: ', vdrprodrev
                for k in sorted(vdrprodrev.keys()):
                    try:
                        iostat[devid][k] = vdrprodrev[k]
                    except UnboundLocalError:
                        break

        # Parse Size Info
        elif line.startswith('S'):
            try:
                Sz, sz, Tr, tr = [x.strip() for x in line.split()]
            except ValueError:
                print "S ValueError"
                continue
            if Debug:
                print Sz, sz
            try:
                iostat[devid][Sz.lower()] = sz.lower()
            except UnboundLocalError:
                continue

        # Parse Media Error, Device Readiness, etc.
        elif line.startswith('Media'):
            medredss = process_mederr_devrdy(line.strip())
            if Debug:
                print 'medredss: ', medredss
            for k in sorted(medredss.keys()):
                try:
                    iostat[devid][k] = medredss[k]
                except UnboundLocalError:
                    break

        # Parse Illegal Request, Predictive Failure Analysis.
        elif line.startswith('Illegal'):
            patt = '.*Predictive Failure.*'
            mp = re.match(patt, line)
            if mp:
                irqst_pfa = process_illreq_pfa(line.strip())
                if Debug:
                    print 'irqst_pfa: ', irqst_pfa
                for k in sorted(irqst_pfa.keys()):
                    try:
                        iostat[devid][k] = irqst_pfa[k]
                    except UnboundLocalError:
                        break
    return iostat


def iostat_json(bdir):
    fname = os.path.join(bdir, 'disk/iostat-en')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = iostat_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def nfsstat_jsp(fname):
    nfsstat = {}
    stats = {}

    stype = None
    srv = None
    scalls = False
    nfsver = 0
    vers = ''
    done = False
    for line in read_raw_txt(fname):
        if line.startswith('Server '):
            patt = '^Server\s+(.*):$'
            mp = re.match(patt, line)
            if mp:
                srv = mp.group(1).lower()

                if srv == 'rpc':
                    nfsstat[srv] = {}
                    stype = 'RPC'
                    # next line will be Connection
                elif srv == 'nfsv2' or  srv == 'nfsv3' or srv == 'nfsv4':
                    nfsstat[srv] = {}
                    stype = 'RPC'
                    # next line will be call stats
                elif srv == 'nfs_acl':
                    nfsstat[srv] = {}
                continue

        elif line.startswith('Version '):
            patt = '^Version\s+(\d+):\s+\((\d+)\s+(\w+)\)$'
            mp = re.match(patt, line)
            if mp:
                version = int(mp.group(1))
                nmcalls = int(mp.group(2))
                cops = mp.group(3)
                if version == 2 or version == 3:
                    if srv == 'nfs_acl':
                        stype = 'ACL'
                    else:
                        stype = 'NFS'
                        srv = 'nfsv' + str(version)
                    nfsstat[srv][version] = {}
                elif version == 4:
                    srv = 'nfsv' + str(version)
                    stype = 'NFS'
                    if not done:
                        nfsstat[srv][version] = {}
                        done = True
                    nfsstat[srv][version][cops] = {}
                    nfsstat[srv][version][cops]['Total'] = nmcalls
            continue

        elif stype == 'RPC':
            if srv == 'rpc':
                if line.startswith('Connection'):
                    patt = '^(Connection.*):$'
                    mp = re.match(patt, line)
                    if mp:
                        conn = mp.group(1).lower()
                        nfsstat[srv][conn] = {}
                        # next line will be conn stats tags
                    continue

                elif line.startswith('calls'):
                    Tags = [x.strip() for x in line.split()]
                    # next line will be conn stats values
                    continue

                else:
                    patt = '^[0-9]+.*$'
                    mp = re.match(patt, line)
                    if mp:
                        idx = 0
                        Values = [x.strip() for x in line.split()]
                        for v in Values:
                            nfsstat[srv][conn][Tags[idx]] = v
                            idx += 1
                        continue
            elif srv == 'nfsv2' or srv == 'nfsv3' or srv == 'nfsv4':
                if line.startswith('calls'):
                    Tags = [x.strip() for x in line.split()]
                    nfsstat[srv]['stats'] = {}
                    # next line will be conn stats values
                    continue

                else:
                    patt = '^[0-9]+.*$'
                    mp = re.match(patt, line)
                    if mp:
                        idx = 0
                        Values = [x.strip() for x in line.split()]
                        for v in Values:
                            nfsstat[srv]['stats'][Tags[idx]] = v
                            idx += 1
                        continue

        elif stype == 'NFS':
            patt = '^[a-zA-Z]+.*$'
            mp = re.match(patt, line)
            if mp:
                Tags = [x.strip() for x in line.split()]
                continue

            patt = '^[0-9]+.*$'
            mp = re.match(patt, line)
            if mp:
                idx = 0
                Vals = [x.strip() for x in line.split()]
                for t in Tags:
                    if srv == 'nfsv2' and version == 2 or   \
                       srv == 'nfsv3' and version == 3:
                        nfsstat[srv][version][t] = {}
                        nfsstat[srv][version][t]['calls'] = Vals[idx]
                        idx += 1
                        nfsstat[srv][version][t]['prcnt'] = Vals[idx]
                        idx += 1
                    elif version == 4:
                        nfsstat[srv][version][cops][t] = {}
                        nfsstat[srv][version][cops][t]['calls'] = Vals[idx]
                        idx += 1
                        nfsstat[srv][version][cops][t]['prcnt'] = Vals[idx]
                        idx += 1
            continue

        elif stype == 'ACL':
            if line.startswith('Version '):
                patt = '^Version\s+(\d+):\s+\((\d+).*\)$'
                mp = re.match(patt, line)
                if mp:
                    version = int(mp.group(1))
                    nmcalls = int(mp.group(2))
                continue

            patt = '^[a-zA-Z]+.*$'
            mp = re.match(patt, line)
            if mp:
                Tags = [x.strip() for x in line.split()]
                continue

            patt = '^[0-9]+.*$'
            mp = re.match(patt, line)
            if mp:
                idx = 0
                Vals = [x.strip() for x in line.split()]
                for t in Tags:
                    if srv == 'nfs_acl':
                        nfsstat[srv][version][t] = {}
                    nfsstat[srv][version][t]['calls'] = Vals[idx]
                    idx += 1
                    nfsstat[srv][version][t]['prcnt'] = Vals[idx]
                    idx += 1
                continue

    return nfsstat


def nfsstat_json(bdir):
    fname = os.path.join(bdir, 'nfs/nfsstat-s')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = nfsstat_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def dfshares_jsp(fname):
    hdrs = []
    for e in read_raw_txt(fname)[0].split():
        pattern = '[A-Z-_@]+'
        mp = re.match(pattern, e)
        if mp:
            hdrs.append(mp.group(0).lower())

    data = []
    for line in read_raw_txt(fname):
        if line.startswith('RESOURCE'):
            continue
        patt = '^\s*(.*)$'
        mp = re.match(patt, line)
        if mp:
            data.append(mp.group(0))

    idx = 1
    json_data = {}
    for d in data:
        val = d.split()
        key = 'nfs' + str(idx)

        new = {}
        for i in xrange(0, len(hdrs)):
            patt = '(\S+)$'
            mp = re.match(patt, val[i])
            if mp:
                new[hdrs[i]] = mp.group(1)
            else:
                new[hdrs[i]] = val[i]
        idx += 1
        json_data[key] = new

    return json_data


def dfshares_json(bdir):
    fname = os.path.join(bdir, 'nfs/dfshares')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = dfshares_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def sharectl_getnfs_jsp(fname):
    sharenfs = {}

    for line in read_raw_txt(fname):
        patt = '^(\w+)=(\w*)$'
        mp = re.match(patt, line)
        if mp:
            key = mp.group(1)
            val = mp.group(2)
            sharenfs[key] = val

    return sharenfs


def sharectl_getnfs_json(bdir):
    fname = os.path.join(bdir, 'nfs/sharectl-get-nfs')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = sharectl_getnfs_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def sharemgr_showvp_nfs_jsp(fname):
    sharemgr = {}

    for line in read_raw_txt(fname):
        patt = '^(\w+)\s+(\w+)=\(\)$'   # NB: if other stuff w/in parens,
        mp = re.match(patt, line)       # we'll need to revisit this
        if mp:
            key = mp.group(1)
            val = mp.group(2)
            sharemgr[key] = val

    return sharemgr


def sharemgr_showvp_nfs_json(bdir):
    fname = os.path.join(bdir, 'nfs/sharemgr-show-vp-p-nfs')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = sharemgr_showvp_nfs_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def svccfg_nfsprops_jsp(fname):
    nfsprops = {}

    for line in read_raw_txt(fname):

        patt = '^([a-z_-]+)\s+(.*)$'
        mp = re.match(patt, line)
        if mp:
            cat = mp.group(1)
            key = mp.group(2)
            if Debug:
                print 'Category:', cat
            nfsprops[cat] = {}

        ptrn = '^([a-z_-]+)[/]+([a-z_-]+)\s+(\w+)\s+(.*)$'
        mp = re.match(ptrn, line)
        if mp:
            if cat == mp.group(1):
                sub = mp.group(2)
                typ = mp.group(3)
                if typ == 'time':
                    val = time.ctime(float(mp.group(4)))
                else:
                    val = mp.group(4)
                if Debug:
                    print '\t', sub, ':', val
                nfsprops[cat][sub] = val

    return nfsprops


def svccfg_nfsprops_json(bdir):
    fname = os.path.join(bdir, \
        'nfs/svccfg-s-svcnetworknfsserverdefault-listprop')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = svccfg_nfsprops_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def zfsgetnfs_jsp(fname):
    zfsnfs = {}

    for line in read_raw_txt(fname):
        patt = '^(\S+)\s+(sharenfs)\s+(\S+)\s+(\S+)$'
        mp = re.match(patt, line)
        if mp:
            if mp.group(3) == 'off':
                continue
            vname = mp.group(1)
            pname = mp.group(2)
            props = mp.group(3)
            orign = mp.group(4)

            if vname not in zfsnfs:
                zfsnfs[vname] = {}
            zfsnfs[vname]['src'] = orign
            zfsnfs[vname]['type'] = pname
            for x in props.split(','):
                if ':' in x:
                    key, lst = x.split('=')
                    tmp = []
                    for l in lst.split(':'):
                        tmp.append(l)
                    zfsnfs[vname][key] = tmp
                    continue
                if '=' in x:
                    k, v = x.split('=')
                    zfsnfs[vname][k] = v

    return zfsnfs


def zfsgetnfs_json(bdir):
    fname = os.path.join(bdir, 'zfs/zfs-get-p-all')
    rtfile = fname + '.out'
    jsout = 'zfs-get-nfs.out.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = zfsgetnfs_jsp(rtfile)
    if len(jsdct) == 0:
        return
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def scsi_vhci_jsp(fname):
    scsivhci = {}
    mlme = {}
    ml = []

    mls = False
    mle = False
    for line in read_raw_txt(fname):

        patt = '^(#|$)'
        mp = re.match(patt, line)
        if mp:
            continue

        # one entry per line
        patt = '^([a-z_-]+)="([a-z_-]+)";'
        mp = re.match(patt, line)
        if mp:
            key = mp.group(1)
            val = mp.group(2)
            scsivhci[key] = val

        # two entries per line
        patt = '^([a-z_-]+)="([a-z_-]+)"\s+([a-z_-]+)="([a-z_-]+)"'
        mp = re.match(patt, line)
        if mp:
            i = 1
            while i <= 4:
                key = mp.group(i)
                i += 1
                val = mp.group(i)
                i += 1
                scsivhci[key] = val

        # multi-line (single entry) start
        patt = '^([a-z_-]+)\s+=$'
        mp = re.match(patt, line)
        if mp:
            mls = True
            mlsk = mp.group(1)

        # collect multiple lines in ml array
        patt = '^\s+"(\S+)",.*'
        mp = re.match(patt, line)
        if mp and mls:
            ml.append(mp.group(1).lower())

        # hit the end of a multiline
        patt = '^\s+"(\S+)";.*'
        mp = re.match(patt, line)
        if mp and mls:
            ml.append(mp.group(1).lower())
            mls = False
            scsivhci[mlsk] = ml

        # special single-line case
        patt = '^([a-z_-]+)\s+=\s+(.*);$'
        mp = re.match(patt, line)
        if mp:
            lhs = mp.group(1)
            rhs = mp.group(2)
            sslc = {}
            if not rhs.isspace():
                vals = [x.strip() for x in rhs.split(',')]
                empty = len(vals) == 0
                while not empty:
                    k, v = vals[:2]
                    del vals[:2]
                    sslc[k.strip('"')] = v.strip('"')
                    empty = len(vals) == 0
                scsivhci[lhs] = sslc
                continue

        # multi-line (multi entry) start
        patt = '^([a-z_-]+)\s+=.*$'
        mp = re.match(patt, line)
        if mp:
            mlk = mp.group(1)
            mle = True

        # collect multi entry lines in array of tuples
        patt = '^\s+"(\w+\s*\w*)",\s+"(\S+)",.*'
        mp = re.match(patt, line)
        if mp and mle:
            mlme[mp.group(1)] = mp.group(2)

        # hit end of multi entry multi-line
        patt = '^\s+"(\w+\s*\w*)",\s+"(\S+)";.*'
        mp = re.match(patt, line)
        if mp and mle:
            mlme[mp.group(1)] = mp.group(2)
            mle = False
            scsivhci[mlk] = mlme

    return scsivhci


def scsi_vhci_json(bdir):
    fname = os.path.join(bdir, 'disk/scsi_vhci.conf')
    jsout = fname + '.json'
    if not valid_file(fname):
        return

    jsdct = scsi_vhci_jsp(fname)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def etcsystm_jsp(fname):
    systm = {}

    for line in read_raw_txt(fname):
        patt = '^(\*|$)'
        mp = re.match(patt, line)
        if mp:
            continue

        patt = '^set\s+(\S+)\s*=\s*(\d+)'
        mp = re.match(patt, line)
        if mp:
            kvar = mp.group(1)
            kval = mp.group(2)
            if ':' in kvar:
                vals = [x.strip() for x in kvar.split(':')]
                empty = len(vals) == 0
                while not empty:
                    m, s = vals[:2]
                    if m not in systm:
                        systm[m] = {}
                    systm[m][s] = kval
                    del vals[:2]
                    empty = len(vals) == 0
            else:
                systm[kvar] = kval

    return systm


def etcsystm_json(bdir):
    fname = os.path.join(bdir, 'kernel/system')
    jsout = fname + '.json'
    if not valid_file(fname):
        return

    jsdct = etcsystm_jsp(fname)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def max_cstates_jsp(fname):
    data = {}

    max_cs = 0
    for line in read_raw_txt(fname):

        patt = '^\w+:\d+:\w+:supported_max_cstates\s+(\d+)'
        mp = re.match(patt, line)
        if mp:
            cs = mp.group(1)
            if cs > max_cs:
                max_cs = cs

    data['max_cstates'] = max_cs
    return data


def max_cstates_json(bdir):
    fname = os.path.join(bdir, 'kernel/kstat-p-td-10-6')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'

    if not valid_collector_output(fname):
        return

    jsdct = max_cstates_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def zplistall_jsp(fname):
    hdrs = []
    for e in read_raw_txt(fname)[0].split():
        pattern = '[A-Z-_@]+'
        mp = re.match(pattern, e)
        if mp:
            hdrs.append(mp.group(0).lower())

    data = []
    for line in read_raw_txt(fname):
        if line.startswith('NAME'):
            continue
        patt = '^[a-zA-Z_]+.*'
        mp = re.match(patt, line)
        if mp:
            data.append(mp.group(0))

    idx = 1
    json_data = {}
    for d in data:
        val = d.split()
        key = 'zpool-' + str(idx)

        new = {}
        for i in xrange(0, len(hdrs)):
            patt = '(\d+.\d+)x$'
            mp = re.match(patt, val[i])
            if mp:
                new[hdrs[i]] = mp.group(1)
            else:
                new[hdrs[i]] = val[i]
        idx += 1
        json_data[key] = new

    return json_data


def zplistall_json(bdir):
    fname = os.path.join(bdir, 'zfs/zpool-list-o-all')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = zplistall_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def zpstatus_json(bdir):
    fname = os.path.join(bdir, 'zfs/zpool-status-dv')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = zpool_status(bdir)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def zfsgtall_json(bdir):
    fname = os.path.join(bdir, 'zfs/zfs-get-p-all')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = zfs_get(bdir)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def zfs_arc_mdb_jsp(fname):
    arcmdb = {}

    for line in read_raw_txt(fname):
        patt = '^(\w+)\s*=\s*(\w*.*)$'
        mp = re.match(patt, line)
        if mp:
            key = mp.group(1)
            val = mp.group(2)
            arcmdb[key] = val

    return arcmdb


def zfs_arc_mdb_json(bdir):
    fname = os.path.join(bdir, 'zfs/echo-arc-mdb-k')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = zfs_arc_mdb_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def dladm_show_phys_jsp(fname):
    hdrs = []
    for e in read_raw_txt(fname)[0].split():
        pattern = '[A-Z-_@]+'
        mp = re.match(pattern, e)
        if mp:
            hdrs.append(mp.group(0).lower())

    data = []
    for line in read_raw_txt(fname):
        if line.startswith('LINK'):
            continue
        patt = '^[a-zA-Z_]+.*'
        mp = re.match(patt, line)
        if mp:
            data.append(mp.group(0).lower())

    json_data = {}
    for d in data:
        val = d.split()

        new = {}
        for i in xrange(0, len(hdrs)):
            new[hdrs[i]] = val[i]
            if hdrs[i] == 'link':
                key = val[i]
        json_data[key] = new

    return json_data


def dladm_show_phys_json(bdir):
    fname = os.path.join(bdir, 'network/dladm-show-phys')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = dladm_show_phys_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)

    dladm_show_link_json(bdir, jsdct)


def merge_mtu_info(bdir, mtud, nwid):
    fname = os.path.join(bdir, 'dladm-phys-link')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'

    newd = {}
    keys = ['device', 'duplex', 'link', 'media', 'speed', 'state', 'mtu']
    for i in nwid:
        if i not in newd:
            newd[i] = {}
        for k in keys:
            if k == 'mtu':
                newd[i][k] = mtud[i][k]
            else:
                newd[i][k] = nwid[i][k]

    jsdmp = json.dumps(newd, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def dladm_show_link_jsp(fname):
    hdrs = []
    for e in read_raw_txt(fname)[0].split():
        pattern = '[A-Z-_@]+'
        mp = re.match(pattern, e)
        if mp:
            hdrs.append(mp.group(0).lower())

    json_data = {}
    for line in read_raw_txt(fname):
        if line.startswith('LINK'):
            continue
        #          link           class    mtu    state   brdge   over
        patt = '^([a-zA-Z0-9]+)\s+(\w+)\s+(\d+)\s+(\w+)\s+(\S+)\s+(.*)$'
        mp = re.match(patt, line)
        if mp:
            new = {}
            lnk = mp.group(1)
            for i in xrange(0, len(hdrs)):
                new[hdrs[i]] = mp.group(i+1)
            json_data[lnk] = new

    return json_data


def dladm_show_link_json(bdir, nwid):
    fname = os.path.join(bdir, 'network/dladm-show-link')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = dladm_show_link_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)

    merge_mtu_info(bdir, jsdct, nwid)


def hex_to_ddec(hs):
    hl = len(hs)
    l = 0
    nm = ''

    while l < hl:
        s = ''
        s = hs[l:l+2]
        nm += str(int(s, 16))
        l += 2
        if l < hl:
            nm += '.'

    return nm


def ifconfig_jsp(fname):
    json_data = {}
    for line in read_raw_txt(fname):
        #patt = '^([a-zA-Z0-9]+):\s+.*$'
        patt = '^([a-zA-Z0-9]+):\s+flags=\d+<(\S+)>\s+.*$'
        mp = re.match(patt, line)
        if mp:
            nic = mp.group(1)
            new = {}
            new['link'] = nic
            flags = mp.group(2).split(',')
            for f in flags:
                if f.lower() == 'ipmp':
                    new['ipmp'] = 'yes'
                else:
                    new['ipmp'] = 'no'
            continue

        patt = '^\s+inet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+(\S+).*$'
        mp = re.match(patt, line)
        if mp:
            inet = mp.group(1)
            new['inet'] = inet
            new['mask'] = hex_to_ddec(mp.group(2))
            continue

        patt = '^\s+groupname\s+([a-zA-Z0-9-]+).*$'
        mp = re.match(patt, line)
        if mp:
            ipmp = mp.group(1)
            new['group'] = ipmp

        json_data[nic] = new

    return json_data


def ifconfig_json(bdir):
    fname = os.path.join(bdir, 'network/ifconfig-a')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = ifconfig_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def merge_link_cfg(phd, lkd, cfd):
    netinfo = {}
    for i in lkd:
        try:
            x = cfd[i]
            netinfo[i] = {}
            a,b,c,d = x['inet'].split('.')
            if a == '0' and b == '0' and c == '0' and d == '0':
                if 'group' in x:
                    g = x['group']
                    for n in cfd:
                        if n == g:
                            netinfo[i]['cfg'] = cfd[n]
                            netinfo[i]['lnk'] = lkd[i]

                            cls = lkd[i]['class']
                            ovr = lkd[i]['over']
                            lnk = lkd[i]['link']
                            if lnk == i and cls == 'phys' and ovr == '--':
                                if 'phs' not in netinfo[i]:
                                    netinfo[i]['phs'] = {}
                                netinfo[i]['phs'][i] = phd[i]
                                continue

                            for y in lkd[i]['over'].split():
                                if y == '--':
                                    continue
                                if lkd[y]['class'] == 'phys':
                                    if 'phs' not in netinfo[i]:
                                        netinfo[i]['phs'] = {}
                                    netinfo[i]['phs'][y] = phd[y]
                else:
                    netinfo[i]['lnk'] = lkd[i]

                    cls = lkd[i]['class']
                    ovr = lkd[i]['over']
                    lnk = lkd[i]['link']
                    if lnk == i and cls == 'phys' and ovr == '--':
                        if 'phs' not in netinfo[i]:
                            netinfo[i]['phs'] = {}
                        netinfo[i]['phs'][i] = phd[i]
                        continue

                    for w in lkd[i]['over'].split():
                        if w == '--':
                            continue
                        if 'phs' not in netinfo[i]:
                            netinfo[i]['phs'] = {}
                        netinfo[i]['phs'][w] = phd[w]
                continue
            netinfo[i]['cfg'] = cfd[i]
            netinfo[i]['lnk'] = lkd[i]
            for z in lkd[i]['over'].split():
                if z == '--' or lkd[z]['class'] == 'phys':
                    if 'phs' not in netinfo[i]:
                        netinfo[i]['phs'] = {}
                if z == '--':
                    netinfo[i]['phs'][i] = phd[i]
                elif lkd[z]['class'] == 'phys':
                    netinfo[i]['phs'][z] = phd[z]
        except KeyError:
            pass

    return netinfo


def network_json(bdir):
    fname = os.path.join(bdir, 'network/dladm-show-phys')
    rtfile = fname + '.out'

    if not valid_collector_output(fname):
        return
    physd = dladm_show_phys_jsp(rtfile)

    fname = os.path.join(bdir, 'network/dladm-show-link')
    rtfile = fname + '.out'
    if not valid_collector_output(fname):
        return
    linkd = dladm_show_link_jsp(rtfile)

    fname = os.path.join(bdir, 'network/ifconfig-a')
    rtfile = fname + '.out'
    if not valid_collector_output(fname):
        return
    ifcfgd = ifconfig_jsp(rtfile)

    nwinfo = merge_link_cfg(physd, linkd, ifcfgd)
    jsdmp = json.dumps(nwinfo, indent=2, separators=(',', ': '), sort_keys=True)
    jsout = os.path.join(bdir, 'network-info') + '.out.json'
    json_save(bdir, jsdmp, jsout)


def collector_stats_json(bdir):
    fnsrc = 'collector.stats'
    fndst = re.sub(r'\.', '_', fnsrc)
    fname = os.path.join(bdir, fnsrc)
    jsout = fndst + '.json'

    jsdct = {}
    for line in read_raw_txt(fname):
        if line.startswith('Collector'):
            patt = '^(\w+) \((\d+.\d+.\d+)\)\s+.*$'
            mp = re.match(patt, line)
            if mp:
                key = mp.group(1).lower()
                val = mp.group(2)
                if key not in jsdct:
                    jsdct[key] = val

        elif line.startswith('Script'):
            patt = '^(Script) (\w+): (.*)$'
            mp = re.match(patt, line)
            if mp:
                key = ('%s_%s') % (mp.group(1).lower(), mp.group(2))
                val = mp.group(3)
                if key not in jsdct:
                    jsdct[key] = val

        elif line.startswith('Elapsed'):
            patt = '^Elapsed \(s\): (.*)$'
            mp = re.match(patt, line)
            if mp:
                key = 'secs_elapsed'
                val = mp.group(1)
                if key not in jsdct:
                    jsdct[key] = val

        elif line.startswith('Number'):
            patt = '^Number of (\w+): (\d+)$'
            mp = re.match(patt, line)
            if mp:
                key = mp.group(1)
                val = mp.group(2)
                if key not in jsdct:
                    jsdct[key] = val

        elif line.startswith('Commands'):
            patt = '^Commands \(([a-zA-Z/]+)\): (\S+)$'
            mp = re.match(patt, line)
            if mp:
                key = mp.group(1).split('/')
                val = mp.group(2).split('/')
                for k in key:
                    K = 'cmd_'+k
                    if K not in jsdct:
                        jsdct[K] = val[key.index(k)]

        elif line.startswith('Configuration'):
            patt = '^Configuration file (\w+): (\S+)$'
            mp = re.match(patt, line)
            if mp:
                key = 'cfg_' + mp.group(1)
                val = mp.group(2)
                if key not in jsdct:
                    jsdct[key] = val

        elif line.startswith('Appliance'):
            patt = '^\w+ \w+: ([a-zA-Z ]+) \((v\d+.\d+.\d+[-\w+\d+\w*]*)\)$'
            mp = re.match(patt, line)
            if mp:
                ka = [ 'appl_os_name', 'appl_os_version' ]
                va = [ mp.group(1), mp.group(2) ]

                for k in ka:
                    if k not in jsdct:
                        jsdct[k] = va[ka.index(k)]

        elif line.startswith('License'):
            patt = '^([a-zA-Z ]+): (\S+)$'
            mp = re.match(patt, line)
            if mp:
                key = mp.group(1).lower().replace(" ", "_")
                val = mp.group(2)
                if key not in jsdct:
                    jsdct[key] = val

        elif line.startswith('Hostname'):
            patt = '^Hostname: ([a-zA-Z0-9_-]+) \((\S+)\)$'
            mp = re.match(patt, line)
            if mp:
                ka = [ 'hostname', 'fqhn' ]
                va = [ mp.group(1), mp.group(2) ]

                for k in ka:
                    if k not in jsdct:
                        jsdct[k] = va[ka.index(k)]

        elif line.startswith('Working'):
            patt = '^Working directory size: (\S+)$'
            mp = re.match(patt, line)
            if mp:
                key = 'cwd_size'
                val = mp.group(1)
                if key not in jsdct:
                    jsdct[key] = val

    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def sharectl_getsmb_jsp(fname):
    sharesmb = {}

    for line in read_raw_txt(fname):
        patt = '^(\w+)=(\w*)$'
        mp = re.match(patt, line)
        if mp:
            key = mp.group(1)
            val = mp.group(2)
            sharesmb[key] = val

    return sharesmb


def sharectl_getsmb_json(bdir):
    fname = os.path.join(bdir, 'cifs/sharectl-get-smb')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = sharectl_getsmb_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def kdumps_jsp(fname):
    kdumps = {}

    for line in read_raw_txt(fname):
        if line.startswith('total') or  \
           line.startswith('d') or      \
           line.endswith('bounds'):
            continue
        lst = [x.strip() for x in line.split()]
        name = lst[-1]
        date = '%s %s %s' % (lst[-4], lst[-3], lst[-2])
        size = lst[-5]

        kdumps[name] = {}
        kdumps[name]['date'] = date
        kdumps[name]['size'] = size

    if len(kdumps.keys()) == 0:
        return 'None'
    return kdumps


def kdumps_json(bdir):
    fname = os.path.join(bdir, \
        'kernel/ls-la-dumpadm-grep-savecore-directory-cut-d-f3')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = kdumps_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def uptime_jsp(fname):
    uptime = {}

    for line in read_raw_txt(fname):
        #14:34:50    up 22 min(s),  2 users,  load average: 1.16, 0.36, 0.21
        # 11:52am  up 419 day(s), 19:28, 1 user, load average: 2.51, 1.68, 1.06
        patt = '^\s*([0-9:apm]*)\s+(\w+)\s+(\d+\s+[a-z()]*),\s*\S*[,]*'
        patt2 = '\s*(\d+)\s+user[s]*,\s+\w+\s+\w+:\s+(\S+\s+\S+\s+\S+)$'
        pattern = patt + patt2
        mp = re.match(pattern, line)
        if mp:
            time = mp.group(1)
            upst = mp.group(2)
            uptm = mp.group(3)
            usrs = mp.group(4)
            ldav = mp.group(5)

            uptime['time'] = time
            uptime['status'] = upst
            uptime['uptime'] = uptm
            uptime['users'] = usrs
            uptime['load avg'] = ldav

            return uptime

        # 14:31:42    up  1:01,  1 user,  load average: 1.91, 0.60, 0.29
        patt = '^\s*([0-9:apm]*)\s+(\w+)\s+(\d+:\d+),\s*\S*[,]*'
        patt2 = '\s*(\d+)\s+user[s]*,\s+\w+\s+\w+:\s+(\S+\s+\S+\s+\S+)$'
        pattern = patt + patt2
        mp = re.match(pattern, line)
        if mp:
            time = mp.group(1)
            upst = mp.group(2)
            uptm = mp.group(3)
            usrs = mp.group(4)
            ldav = mp.group(5)

            uptime['time'] = time
            uptime['status'] = upst
            uptime['uptime'] = uptm
            uptime['users'] = usrs
            uptime['load avg'] = ldav

    return uptime


def uptime_json(bdir):
    fname = os.path.join(bdir, 'system/uptime')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = uptime_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def prtdiag_jsp(fname):
    hwdiag = {}

    ln = 0
    hdrs = []
    cpus = []
    for line in read_raw_txt(fname):
        ln += 1
        if ln <= 3:
            hdrs.append(line)
            continue

        patt = '^(.*)\s+CPU\s+(.*)$'
        mp = re.match(patt, line)
        if mp:
            cpus.append(mp.group(0))
        else:
            patt = '^(.*)\s+CPU[0-9]+$'
            mp = re.match(patt, line)
            if mp:
                cpus.append(mp.group(1).strip())

    if ln:
        hwdiag['cpu info'] = cpus
        for h in hdrs:
            if len(h) == 0:
                continue

            try:
                lbl = h.split(':')[0].lower().split()[0]
            except IndexError, e:
                pprint(h)
                print str(e)
                continue

            patt = '^(.*ion):\s+(.*)$'
            mp = re.match(patt, h)
            if mp:
                hwdiag[lbl] = mp.group(2)

    return hwdiag


def prtdiag_json(bdir):
    fname = os.path.join(bdir, 'system/prtdiag-v')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = prtdiag_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def memstat_jsp(fname):
    memstat = {}

    for line in read_raw_txt(fname):
        if line.startswith('Total') or line.startswith('Physical'):
            ln = [x.strip() for x in line.split()]
            key = ln[0].lower()

            if key not in memstat:
                memstat[key] = {}
            memstat[key]['pages'] = ln[1]
            memstat[key]['MBs'] = ln[2]

    return memstat


def memstat_json(bdir):
    fname = os.path.join(bdir, 'kernel/echo-memstat-mdb-k-tail-n2')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = memstat_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def zpiostat_jsp(fname):
    zpiostat = {}

    header = 0
    hdr = []
    hdidx = 0
    vdone = 0
    fpass = False
    pool = ''
    for line in read_raw_txt(fname):
        if not fpass:
            fpass = True
            datepatt = '\w*\s*\w+\s+\d+[,]*\s*\S*\s*(\d+:\d+:\d+).*'
            mp = re.match(datepatt, line)
            if mp:
                header = 1
                continue

        if header:
            if hdidx != 2:
                hdr.append(line.split())
                hdidx += 1
                continue
            else:
                header = 0
                hdidx = 0
                continue    # skipping header's '------------' line

        #
        # Pool
        #
        p1 = '^(\S*)\s+(\S*)\s+(\S*)\s+(\S*)\s+'
        p2 = '(\S*)\s+(\S*)\s+(\S*)\s+(\S*)\s+'
        p3 = '(\S*)'
        patt = p1 + p2 + p3
        mp = re.match(patt, line)
        if mp:
            pool = mp.group(1)
            capa = mp.group(2)
            capf = mp.group(3)
            oprd = mp.group(4)
            opwt = mp.group(5)
            bwrd = mp.group(6)
            bwwt = mp.group(7)
            ltrd = mp.group(8)
            ltwt = mp.group(9)

            if pool not in zpiostat:
                zpiostat[pool] = {}

            cap = hdr[0][0]
            labl1 = hdr[1][1]
            labl2 = hdr[1][2]
            zpiostat[pool][cap] = {}
            zpiostat[pool][cap][labl1] = capa
            zpiostat[pool][cap][labl2] = capf

            ops = hdr[0][1]
            labl3 = hdr[1][3]
            labl4 = hdr[1][4]
            zpiostat[pool][ops] = {}
            zpiostat[pool][ops][labl3] = oprd
            zpiostat[pool][ops][labl4] = opwt

            bwth = hdr[0][2]
            labl5 = hdr[1][5]
            labl6 = hdr[1][6]
            zpiostat[pool][bwth] = {}
            zpiostat[pool][bwth][labl5] = bwrd
            zpiostat[pool][bwth][labl6] = bwwt

            ltcy = hdr[0][3]
            labl7 = hdr[1][7]
            labl8 = hdr[1][8]
            zpiostat[pool][ltcy] = {}
            zpiostat[pool][ltcy][labl7] = ltrd
            zpiostat[pool][ltcy][labl8] = ltwt
            continue

        #
        # vdev
        #
        p1 = '^\s*([A-Za-z_]*[0-9]*)\s+(\d+[.]*\d*[A-Z]+)\s+(\d+[.]*\d*[A-Z]+)'
        p2 = '\s+(\d+)\s+(\d+)\s+(\d+[.]*\d*[A-Z]+)\s+(\d+[.]*\d*[A-Z]+)'
        p3 = '\s+(\d+[.]*\d*)\s+(\d+[.]*\d*)'
        patt = p1 + p2 + p3
        mp = re.match(patt, line)
        if mp and not vdone:
            vdev = mp.group(1)
            capa = mp.group(2)
            capf = mp.group(3)
            oprd = mp.group(4)
            opwt = mp.group(5)
            bwrd = mp.group(6)
            bwwt = mp.group(7)
            ltrd = mp.group(8)
            ltwt = mp.group(9)

            if vdev not in zpiostat[pool]:
                zpiostat[pool][vdev] = {}

            cap = hdr[0][0]
            labl1 = hdr[1][1]
            labl2 = hdr[1][2]
            zpiostat[pool][vdev][cap] = {}
            zpiostat[pool][vdev][cap][labl1] = capa
            zpiostat[pool][vdev][cap][labl2] = capf

            ops = hdr[0][1]
            labl3 = hdr[1][3]
            labl4 = hdr[1][4]
            zpiostat[pool][vdev][ops] = {}
            zpiostat[pool][vdev][ops][labl3] = oprd
            zpiostat[pool][vdev][ops][labl4] = opwt

            bwth = hdr[0][2]
            labl5 = hdr[1][5]
            labl6 = hdr[1][6]
            zpiostat[pool][vdev][bwth] = {}
            zpiostat[pool][vdev][bwth][labl5] = bwrd
            zpiostat[pool][vdev][bwth][labl6] = bwwt

            ltcy = hdr[0][3]
            labl7 = hdr[1][7]
            labl8 = hdr[1][8]
            zpiostat[pool][vdev][ltcy] = {}
            zpiostat[pool][vdev][ltcy][labl7] = ltrd
            zpiostat[pool][vdev][ltcy][labl8] = ltwt

            vdone = 1
            continue

        if line.startswith('------------'):
            vdone = 0
            continue

        mp = re.match(datepatt, line)
        if mp and fpass:
            break

    return zpiostat


def zpiostat_json(bdir):
    fname = os.path.join(bdir, 'zfs/zpool-iostat-td-v-1-60')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = zpiostat_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def mailer_jsp(fname):
    mailer = {}

    for line in read_raw_txt(fname):
        patt = '^(\w+)\s+:\s+([a-zA-Z0-9@$.+-]*)$'
        mp = re.match(patt, line)
        if mp:
            key = mp.group(1)
            val = mp.group(2)
            mailer[key] = val

    return mailer


def mailer_json(bdir):
    fname = os.path.join(bdir, 'appliance/nmc-c-show-appliance-mailer')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = mailer_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def normalize_lun_id(bdir, lunid):
    if '.' not in lunid:
        return lunid

    patt = '^\w+(?:...)(\S+)'
    mp = re.match(patt, lunid)
    if mp:
        sp = mp.group(1)

    fname = os.path.join(bdir, 'disk/hddisco') + '.out'
    for line in read_raw_txt(fname):
        if line.startswith('='):
            patt = '=(\w+%s)' % sp
            mp = re.match(patt, line)
            if mp:
                return mp.group(1)


def lun_smartstat_jsp(bdir, fname):
    lunstat = {}

    for line in read_raw_txt(fname):
        if line.startswith('LUN'):
            continue

        patt = '^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
        mp = re.match(patt, line)
        if mp:
            lid = normalize_lun_id(bdir, mp.group(1))
            dev = mp.group(2)
            sze = mp.group(3)
            vol = mp.group(4)
            gid = mp.group(5)   # Not Used
            sst = mp.group(6)
            ena = mp.group(7)

            if vol not in lunstat:
                lunstat[vol] = {}
                lunstat[vol]['luns'] = {}

            if lid not in lunstat[vol]['luns']:
                lunstat[vol]['luns'][lid] = {}

            lunstat[vol]['luns'][lid]['dev'] = dev
            lunstat[vol]['luns'][lid]['size'] = sze
            lunstat[vol]['luns'][lid]['smart'] = sst
            lunstat[vol]['luns'][lid]['status'] = ena

    return lunstat


def lun_smartstat_json(bdir):
    fname = os.path.join(bdir, 'disk/nmc-c-show-lun-smartstat')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = lun_smartstat_jsp(bdir, rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def cifs_domain_jsp(fname):
    domain = {}

    for line in read_raw_txt(fname):
        patt = '^(\S+)$'
        mp = re.match(patt, line)
        if mp:
            key = 'cifs domain'
            val = mp.group(1)

            if key not in domain:
                domain[key] = {}
            domain[key] = val

    return domain


def cifs_domain_json(bdir):
    fname = os.path.join(bdir, 'cifs/cifs-domains')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = cifs_domain_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def modparams_jsp(fname):
    modparms = {}

    for line in read_raw_txt(fname):
        patt = '^([a-zA-Z0-9_]*):\s*(\S*)\s*$'
        mp = re.match(patt, line)
        if mp:
            key = mp.group(1)
            val = mp.group(2)
            modparms[key] = val

    return modparms


def modparams_json(bdir):
    fname = os.path.join(bdir, 'kernel/modparams')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = modparams_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def nms_faults_jsp(fname):
    faults = {}
    hdrs = []

    for e in read_raw_txt(fname)[0].split():
        pattern = '[A-Z-]+'
        mp = re.match(pattern, e)
        if mp:
            hdrs.append(mp.group(0).lower())

    idx = 1
    nms = 0
    for line in read_raw_txt(fname):

        if line.startswith('TRIGGER'):  # skip headers
            continue

        patt = '^\s*$'                  # skip blank lines
        mp = re.match(patt, line)
        if mp:
            continue

        patt = '^\033\[[0-9]+m(.*)$'    # strip color (if any)
        mp = re.match(patt, line)
        if mp:
            ln = mp.group(1)
        else:
            ln = line

        if ln.startswith('nms-'):
            nms = 1

            key = 'fault-' + str(idx)
            if key not in faults:
                faults[key] = {}

            patt = '\s*(\S+)\s+(\d+)\s+(\d+)\s+(\w+)\s+(.*)\s*'
            mp = re.match(patt, ln)
            if mp:
                for i in xrange(0, len(hdrs)):
                    if hdrs[i] not in faults:
                        faults[key][hdrs[i]] = {}
                    faults[key][hdrs[i]] = mp.group(i + 1)
                continue

        elif nms:
            patt = '^\S+.*$'
            mp = re.match(patt, ln)
            if mp:
                faults[key]['msg'] = mp.group(0)
            idx += 1
            nms = 0

        else:
            summ = 'summary'
            patt = '^\S+.*$'
            mp = re.match(patt, ln)
            if mp:
                if summ not in faults:
                    faults[summ] = ''
                faults[summ] = mp.group(0)

    return faults


def nms_faults_json(bdir):
    fname = os.path.join(bdir, 'fma/nmc-c-show-faults')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'
    
    if not valid_collector_output(fname):
        return

    jsdct = nms_faults_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def encl_jbods_jsp(fname):
    json_data = {}
    idx = 0
    for line in read_raw_txt(fname):
        if line.startswith('PROPERTY'):
            idx += 1
            continue
        elif line.startswith('ELEMENT') or line.startswith('SLOT') or   \
           line.startswith('slot:') or line.startswith('Tray') or       \
           line.startswith('jbod') or line.startswith('fan') or         \
           line.startswith('psu'):
            continue
        patt = '^([a-zA-Z_]+)\s\s+(\S+).*'
        mp = re.match(patt, line)
        if mp:
            key = mp.group(1)
            val = mp.group(2)

            jb = 'jbod-' + str(idx)
            if jb not in json_data:
                json_data[jb] = {}
            json_data[jb][key] = val

    return json_data


def encl_jbods_json(bdir):
    fname = os.path.join(bdir, 'enclosures/nmc-c-show-jbod-all')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = encl_jbods_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def lun_slotmap_jsp(fname):
    json_data = {}
    hdrs = []

    hdrs_done = False
    for line in read_raw_txt(fname):
        if line.startswith('LUN'):
            if not hdrs_done:
                for l in line.split():
                    hdrs.append(l.lower())
                hdrs_done = True
            continue

        new = {}
        patt = '^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*(\S*)'
        mp = re.match(patt, line)
        if mp:
            for i in xrange(0, len(hdrs)-1):
                new[hdrs[i]] = mp.group(i + 1).lower()

            # using LUN as the outer index
            json_data[mp.group(1).lower()] = new

    return json_data


def lun_slotmap_json(bdir):
    fname = os.path.join(bdir, 'enclosures/nmc-c-show-lun-slotmap')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = lun_slotmap_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


#
# ENCLOSURE_ID                 VENDOR  PRODUCT LID             STATUS IDENT FAIL
# LSI-SAS2X36:5003048001faa53f    LSI SAS2X36 5003048001faa53f    OK    0     0
# LSI-SAS2X36:5003048001e2e03f    LSI SAS2X36 5003048001e2e03f    OK    0     0
# LSI-SAS2X36:5003048001e2e03f    LSI SAS2X36 5003048001e2e03f    OK    0     0
#
def jbods_sesctl_jsp(fname):
    json_data = {}
    idx = 0

    hdrs = []
    for e in read_raw_txt(fname)[0].split():
        # ['enclosure', 'vendor', 'product', 'lid', 'status', 'ident', 'fail']
        pattern = '[A-Z-]+'
        mp = re.match(pattern, e)
        if mp:
            hdrs.append(mp.group(0).lower())

    for line in read_raw_txt(fname):
        new = {}
        if line.startswith('ENCLOSURE'):
            idx += 1
            continue
        patt = '^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
        mp = re.match(patt, line)
        if mp:
            for i in xrange(0, len(hdrs)):
                new[hdrs[i]] = mp.group(i + 1)

            # using LID as the outer index
            json_data[mp.group(4)] = new

    return json_data


def jbods_sesctl_json(bdir):
    fname = os.path.join(bdir, 'enclosures/sesctl-enclosure')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = jbods_sesctl_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def opthac_jsp(gzname):
    hac = {}

    try:
        names = tarfile.open(gzname, 'r:*').getnames()
    except:
        sys.stderr.write('Fatal error: cannot open ' + gzname + '\n')
        return None

    i = 0
    hac['cluster'] = {}
    hw = {}
    l = 0
    for n in names:
        patt = '\S*/licen[cs]e.*'
        mp = re.match(patt, n)
        if mp:
            i += 1
            mid = 'machid' + str(i)
            val = mp.group(0).split('.')[-1]
            hw[mid] = val                   # save off machid's for later
            continue

        #
        # Extract ./etc/config in order to parse it
        #
        patt = '\S*/etc/config$'
        mp = re.match(patt, n)
        if mp:
            cfgfile = mp.group(0)
            try:
                fd = tarfile.open(gzname, 'r:*').extractfile(cfgfile)
            except:
                sys.stderr.write('Cannot extract ' + cfgfile + '\n')
                continue

            newsvc = False
            idx = 0
            n = 0
            k = 0
            for line in fd.readlines():
                if line.startswith('#'):
                    continue
                elif line.startswith('CLUSTER_NAME'):
                    patt = '^\S+\s+(\S+).*'
                    mp = re.match(patt, line)
                    if mp:
                        hac['cluster']['name'] = mp.group(1)
                    continue
                elif line.startswith('MACHINE'):
                    if line.startswith('MACHINE_BOOTSTRAP'):
                        return hac
                    idx += 1
                    host = 'node' + str(idx)
                    patt = '^\S+\s+(\S+).*'
                    mp = re.match(patt, line)
                    if mp:
                        if host not in hac['cluster']:
                            hac['cluster'][host] = {}
                        if 'hostname' not in hac['cluster'][host]:
                            hac['cluster'][host] = {}
                        hac['cluster'][host]['hostname'] = mp.group(1)
                    continue
                elif line.startswith('SERVICE'):
                    newsvc = True
                    continue
                elif newsvc:
                    if line.startswith(' MOUNT_POINT') or   \
                       line.startswith(' SETENV'):
                        pass
                    else:
                        continue

                    if line.startswith(' MOUNT_POINT'):
                        k += 1
                        node = 'node' + str(k)

                        patt = '^\s+(\S+)\s+(\S+).*'
                        mp = re.match(patt, line)
                        if mp:
                            mntpt = mp.group(2).strip('"')
                            if node not in hac['cluster']:
                                hac['cluster'][node] = {}
                            hac['cluster'][node]['mntpt'] = mntpt
                        continue
                    elif line.startswith(' SETENV'):
                        n += 1
                        node = 'node' + str(n)
                        patt = '^\s+\S+\s+(\S+)\s+(\S+).*'
                        mp = re.match(patt, line)
                        if mp:
                            guid = mp.group(1).lower()
                            gval = mp.group(2).strip('"')
                            hac['cluster'][node][guid] = gval
                        continue

                    newsvc = False
                    continue

            hac['cluster']['ha'] = True if idx >= 2 else False

    #
    # Add the machid's saved from before
    #
    l = 0
    for m in sorted(hw):
        l += 1
        node = 'node' + str(l)
        hac['cluster'][node]['machid'] = hw[m]

    if 'cluster' in hac:
        if len(hac['cluster']) == 0:
            return None
    return hac


def opthac_json(bdir):
    fname = os.path.join(bdir, 'plugins/tar-czf-opthac')
    gzfile = fname + '.tar.gz'
    jsout = gzfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = opthac_jsp(gzfile)
    if jsdct is None:
        return
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def fmdump_evt_30day(bdir, errs):
    vfile = os.path.join(bdir, 'fmdump-evt-30day.out.gz')
    cs = ['zcat ', vfile]
    cmd = "".join(cs)
    flimit = 10*1024*1024                   # 10MB File size limit (for now)

    faults = {}
    sz = os.stat(vfile).st_size
    if sz > flimit:
        print vfile, 'exceeds size limits... skipping'
        return faults

    cap = False
    for e in sorted(errs):
        flt = errs[e]['fault']
        if flt not in faults:
            faults[flt] = {}

        fd = os.popen(cmd)
        for line in fd:
            patt = '^\s*$'                  # skip blank lines
            mp = re.match(patt, line)
            if mp:
                continue

            patt = '^\s+([a-zA-Z0-9_-]+)\s+=\s+([a-zA-Z0-9/\.@:,_ -]+)\s*$'
            mp = re.match(patt, line)
            if mp:
                lv = mp.group(1)
                rv = mp.group(2)
                if rv == flt:
                    cap = True
                if cap:
                    faults[flt][lv] = rv
                    if lv == '__tod':
                        cap = False
                        break

    return faults


def fma_faults_jsp(gzname):
    errs = {}
    cs = ['zcat ', gzname, ' | awk \'{print $NF}\' | sort | uniq -c',
           ' | egrep -v CLASS']
    cmd = "".join(cs)
    fh = os.popen(cmd)

    idx = 0
    for f in fh:
        idx += 1
        key = 'event' + str(idx)
        if key not in errs:
            errs[key] = {}

        errs[key]['count'] = f.strip().split()[0]
        errs[key]['fault'] = f.strip().split()[1]

    return fmdump_evt_30day(os.path.dirname(gzname), errs)


def fma_faults_json(bdir):
    fname = os.path.join(bdir, 'fma/fmdump-e')
    gzfile = fname + '.out.gz'
    jsout = gzfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = fma_faults_jsp(gzfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(', ', ': '),
        sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def stmfadm_lu_v_jsp(fname):
    luns = {}
    name = ''

    for line in read_raw_txt(fname):
        if line.startswith('LU Name:'):
            patt = '^LU Name:\s+(\S+)$'
            mp = re.match(patt, line)
            if mp:
                name = mp.group(1)

                if name not in luns:
                    luns[name] = {}
            
                continue
        else:
            patt = '\s+([a-zA-Z ]+)\s*:\s+(.*)$'
            mp = re.match(patt, line)
            if mp:
                lval = re.sub(' ', '_', mp.group(1).strip().lower())
                rval = mp.group(2)

                luns[name][lval] = rval

    return luns


def stmfadm_lu_v_json(bdir):
    fname = os.path.join(bdir, 'comstar/stmfadm-list-lu-v')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = stmfadm_lu_v_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def is_hex(s):
    try:
        int(s, 16)
        return True

    except ValueError:
        return False


def for_lu_in_stmfadm_jsp(fname):
    stanza = {}
    hval = ''

    for line in read_raw_txt(fname):
        patt = '^\s*$'                  # skip blank lines
        mp = re.match(patt, line)
        if mp:
            continue

        if is_hex(line):
            hval = line
            if hval not in stanza:
                stanza[hval] = {}

        else:
            patt = '^\s*([a-zA-Z0-9 ]+)\s*:\s+(\S+)$'
            mp = re.match(patt, line)
            if mp:
                lval = re.sub(' ', '_', mp.group(1).strip().lower())
                rval = mp.group(2)
                stanza[hval][lval] = rval
                continue

    return stanza


def for_lu_in_stmfadm_json(bdir):
    fname = os.path.join(bdir, 'comstar/for-lu-in-stmfadm-list-lucut-d-f3-do-echo-echo-luecho-stmfadm-list-view-l-lu-done')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = for_lu_in_stmfadm_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def itadm_list_target_jsp(fname):
    targets = {}
    curriqn = ''
    hdrs = []

    head_done = False
    for line in read_raw_txt(fname):
        #print line

        if not head_done:
            patt = '^(\S+\s+\S+)\s+(\S+)\s+(\S+).*'
            mp = re.match(patt, line)
            if mp:
                hdrs.append(re.sub(' ', '_', mp.group(1).strip().lower()))
                hdrs.append(mp.group(2).strip().lower())
                hdrs.append(mp.group(3).strip().lower())
                head_done = True
                continue

        if line.startswith('iqn'):
            iqn, state, sess = line.split()
            if iqn not in targets:
                targets[iqn] = {}
                #targets[iqn][hdrs[0]] = iqn
                targets[iqn][hdrs[1]] = state
                targets[iqn][hdrs[2]] = sess
                curriqn = iqn
            continue

        patt = '^\s+(\S+):\s+(\S+ = \d+)$'
        mp = re.match(patt, line)
        if mp:
            lval = re.sub('-', '_', mp.group(1).strip().lower())
            rval = mp.group(2)
            if 'attrs' not in targets[curriqn]:
                targets[curriqn]['attrs'] = {}
            targets[curriqn]['attrs'][lval] = rval
            continue

        patt = '^\s+(\S+):\s+(\S+).*'
        mp = re.match(patt, line)
        if mp:
            lval = mp.group(1).strip().lower()
            rval = mp.group(2).strip()
            if 'attrs' not in targets[curriqn]:
                targets[curriqn]['attrs'] = {}
            targets[curriqn]['attrs'][lval] = rval

    return targets


def itadm_list_target_json(bdir):
    fname = os.path.join(bdir, 'comstar/itadm-list-target-v')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = itadm_list_target_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


def itadm_list_tpg_jsp(fname):
    tpg = {}
    currnm = ''
    hdrs = []

    head_done = False
    for line in read_raw_txt(fname):

        if not head_done:
            patt = '^(\S+\s+\S+\s+\S+)\s+(\S+\s+\S+).*'
            mp = re.match(patt, line)
            if mp:
                hdrs.append(re.sub(' ', '_', mp.group(1).strip().lower()))
                hdrs.append(re.sub(' ', '_', mp.group(2).strip().lower()))
                head_done = True
                continue

        patt = '^(\S+)\s+(\d+).*'
        mp = re.match(patt, line)
        if mp:
            name = re.sub('-', '_', mp.group(1).strip().lower())
            if name not in tpg:
                tpg[name] = {}
            tpg[name][hdrs[0]] = mp.group(1)    # target portal group
            tpg[name][hdrs[1]] = mp.group(2)    # portal count
            currnm = name
            continue

        patt = '^\s+(\S+):\s+(\S+)$'
        mp = re.match(patt, line)
        if mp:
            lval = mp.group(1).strip().lower()
            rval = mp.group(2)
            if currnm not in tpg:
                tpg[currnm] = {}
            tpg[currnm][lval] = rval

    return tpg


def itadm_list_tpg_json(bdir):
    fname = os.path.join(bdir, 'comstar/itadm-list-tpg-v')
    rtfile = fname + '.out'
    jsout = rtfile + '.json'
    stfile = fname + '.stats'

    if not valid_collector_output(fname):
        return

    jsdct = itadm_list_tpg_jsp(rtfile)
    jsdmp = json.dumps(jsdct, indent=2, separators=(',', ': '), sort_keys=True)
    json_save(bdir, jsdmp, jsout)


#
# XXX - The following files don't need to be converted; just checked
#       for whether someone has modified them by comparison to their
#       corresponding master copy.
#
#       comstar/stmf_sbd.conf, disk/sd.conf, disk/mpt_sas.conf
#

#
# put your actual code within this function.
# exit 0 on success, exit 1 on failure
#
def main(bundle_dir):
    convnames = ['aptsrc',              \
                'nmchkpt',              \
                'hddisco',              \
                'iostat',               \
                'nfsstat',              \
                'dfshares',             \
                'zfsgetnfs',            \
                'sharectl_nfs',         \
                'sharemgr',             \
                'svccfg',               \
                'scsi_vhci',            \
                'etcsystm',             \
                'zplistall',            \
                'zpstatus',             \
                'zfsgtall',             \
                'zfs_arc_mdb',          \
                'sharectl_smb',         \
                'kdumps',               \
                'uptime',               \
                'prtdiag',              \
                'memstat',              \
                'zpiostat',             \
                'mailer',               \
                'cifs_domain',          \
                'modparams',            \
                'nms_faults',           \
                'encl_jbods',           \
                'jbods_sesctl',         \
                'opthac',               \
                'fma_faults',           \
                'stmfadm_lu_v',         \
                'lun_smartstat',        \
                'lun_slotmap',          \
                'dladm_show_phys',      \
                'ifconfig',             \
                'network',              \
                'collector_stats',      \
                'itadm_list_tpg',       \
                'itadm_list_target',    \
                'for_lu_in_stmfadm',    \
                'max_cstates']

    convfuncs = {'aptsrc_json':             aptsrc_json,
                'nmchkpt_json':             nmchkpt_json,
                'hddisco_json':             hddisco_json,
                'iostat_json':              iostat_json,
                'nfsstat_json':             nfsstat_json,
                'zfsgetnfs_json':           zfsgetnfs_json,
                'dfshares_json':            dfshares_json,
                'sharectl_nfs_json':        sharectl_getnfs_json,
                'sharemgr_json':            sharemgr_showvp_nfs_json,
                'svccfg_json':              svccfg_nfsprops_json,
                'scsi_vhci_json':           scsi_vhci_json,
                'etcsystm_json':            etcsystm_json,
                'zplistall_json':           zplistall_json,
                'zpstatus_json':            zpstatus_json,
                'zfsgtall_json':            zfsgtall_json,
                'zfs_arc_mdb_json':         zfs_arc_mdb_json,
                'dladm_show_phys_json':     dladm_show_phys_json,
                'network_json':             network_json,
                'collector_stats_json':     collector_stats_json,
                'ifconfig_json':            ifconfig_json,
                'kdumps_json':              kdumps_json,
                'sharectl_smb_json':        sharectl_getsmb_json,
                'uptime_json':              uptime_json,
                'prtdiag_json':             prtdiag_json,
                'memstat_json':             memstat_json,
                'zpiostat_json':            zpiostat_json,
                'mailer_json':              mailer_json,
                'cifs_domain_json':         cifs_domain_json,
                'modparams_json':           modparams_json,
                'nms_faults_json':          nms_faults_json,
                'encl_jbods_json':          encl_jbods_json,
                'jbods_sesctl_json':        jbods_sesctl_json,
                'opthac_json':              opthac_json,
                'fma_faults_json':          fma_faults_json,
                'stmfadm_lu_v_json':        stmfadm_lu_v_json,
                'lun_smartstat_json':       lun_smartstat_json,
                'lun_slotmap_json':         lun_slotmap_json,
                'itadm_list_tpg_json':      itadm_list_tpg_json,
                'itadm_list_target_json':   itadm_list_target_json,
                'for_lu_in_stmfadm_json':   for_lu_in_stmfadm_json,
                'max_cstates_json':         max_cstates_json}

    if verify_bundle_directory(script_name, bundle_dir):
        for nm in convnames:
            c = nm + '_json'
            convfuncs[c](bundle_dir)

    else:
        print script_name + ": directory (" + bundle_dir + ") not valid."
        sys.exit(1)


# no reason to touch
if __name__ == '__main__':

    if len(sys.argv) <= 1:
        print script_name + ": no directory specified."
    else:
        main(sys.argv[1])


# pydoc
__author__ = "Rick Mesta"
__copyright__ = "Copyright 2015 Nexenta Systems, Inc. All rights reserved."
__credits__ = ["Rick Mesta, Billy Kettler"]
__license__ = "undefined"
__version__ = "$Revision: " + r2j_ver + " $"
__created_date__ = "$Date: 2015-03-02 09:00:00 +0600 (Mon, 02 Mar 2015) $"
__last_updated__ = "$Date: 2016-09-16 11:32:00 +0600 (Fri, 16 Sep 2016) $"
__maintainer__ = "Rick Mesta"
__email__ = "rick.mesta@nexenta.com"
__status__ = "Production"
