#!/usr/bin/env python

# author Andrew Galloway
# contact with questions/additions/etc (use Github)

import os
import re


class Path(Exception):
    pass


def verify_bundle_directory(caller, directory):
    if os.path.isdir(directory):
        return True
    else:
        print '%s: %s is not a valid directory' % (script_name, directory)
        return False


def check_path(f):
    """
    Verify a path exists.

    Inputs:
        f      (str): Path to file
    Outputs:
        None
    """
    if not os.path.exists(f):
        raise Path('%s does not exist' % f)


def append_file(filename, message):
    with open(filename, "a") as af:
        af.write(message)


def bytes_format(orig_bytes):

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
    unit_num = 0
    work_bytes = int(orig_bytes)

    while work_bytes > 1024:
        work_bytes = work_bytes / 1024
        unit_num = unit_num + 1

    work_bytes = round(work_bytes, 2)

    return str(work_bytes) + units[unit_num]


def check_list_identical(lst):
    return lst[1:] == lst[:-1]


def zfs_get(p):
    """
    Parse 'zfs get -p all'.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        zfs (dict): Parsed zfs properties
    """
    # Input file
    f = "/".join([p, 'zfs/zfs-get-p-all.out'])
    check_path(f)

    zfs = {}

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        for line in fh.readlines()[1:]:
            # Split lines using a delimiter of 2+ spaces
            try:
                name, property, value, source = [x.strip()
                            for x in re.split(r'\s{2,}', line)]
            # There are some systems that will print a property on more then
            # one line and we want to ignore these values.
            except ValueError:
                continue

            # If this is a new file system add a new key
            if name not in zfs:
                zfs[name] = {}

            # Add property, value, source
            # Note values are not cast to a specific type

            if property == "compressratio":
                patt = '(\d+.\d+)x$'
                mp = re.match(patt, value)
                if mp:
                    value = mp.group(1)

            zfs[name][property] = {
                'value': value,
                'source': source
            }

    return zfs


def kstat(p):
    """
    Parse 'kstat -p -td <int>' output.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        kstat (dict): Parsed kstat's
    """
    # Input file
    f = "/".join([p, 'kernel/kstat-p-td-10-6.out'])
    check_path(f)

    kstat = {}

    # Match any date string. This had to remain fairly generic because the
    # date strings vary from system to system
    m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct',
         'Nov', 'Dec']
    month = re.compile('(%s).+[0-9]{2}:[0-9]{2}:[0-9]{2}' % '|'.join(m))

    # Match empty lines
    empty = re.compile('^\s*$')

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        for line in fh.readlines():
            # Ignore blank lines
            if empty.search(line):
                continue

            # If line contains a month string add new key and set current
            if month.search(line):
                t = line.split()[3]
                kstat[t] = {}
                continue

            # Reset to base after each iteration
            current = kstat[t]

            # Parse key/value pairs
            try:
                keys, v = [x.strip() for x in line.split('\t')]
            # Skip anomolies
            except ValueError:
                continue
            keys = keys.split(':')

            # All but last key should be a dict
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = v

    return kstat


def svcs(p):
    """
    Parse 'svcs -a' output.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        svcs (dict): Parsed svcs's
    """
    # Input file
    f = "/".join([p, 'services/svcs-a.out'])
    check_path(f)

    svcs = []

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        for line in fh.readlines()[1:]:
            state, stime, fmri = [x.strip() for x in line.split()]
            svcs.append([state, stime, fmri])

    return svcs


def zpool_list(p):
    """
    Parse 'zpool list' output.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        zlist (dict): Parsed list
    """
    # Input file
    f = '/'.join([p, 'zfs/zpool-list-o-all.out'])
    check_path(f)

    zlist = {}

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        lines = fh.readlines()

        # Read column headers
        head = [x.lower() for x in lines[0].split()]

        # Parse each zpool|zfs
        for line in lines[1:]:
            info = line.split()
            for i in range(len(info)):
                # First entry is always the zpool|zfs name
                if i == 0:
                    name = info[i]
                    zlist[name] = {}
                zlist[name][head[i]] = info[i]

    return zlist


def hddisco(p):
    """
    Parse 'hddisco' output.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        disco (dict): Parsed hddisco output
    """
    # Input file
    f = '/'.join([p, 'disk/hddisco.out'])

    disco = {}

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        for line in fh.readlines():
            # If the line begins with '=' set current devid
            if line.startswith('='):
                devid = line.lstrip('=').strip()
                disco[devid] = {'P': {}}
                path = 0
            # Parse path information
            elif line.startswith('P'):
                try:
                    k, v = [x.strip() for x in line.split()[1:]]
                except:
                    # Increment path count
                    if line.startswith("P end"):
                        path += 1
                else:
                    # sd driver doesn't print P start/end
                    if path not in disco[devid]["P"]:
                        disco[devid]["P"][path] = {}
                    disco[devid]["P"][path][k] = v
            # Split line on spaces into key/value pairs
            else:
                k, v = [x.strip() for x in line.split(None, 1)]
                disco[devid][k] = v

    return disco


def mpathadm(p):
    """
    Parse the output of 'mpathadm list lu'.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        lu (dict): Parsed mpathadm output
    """
    # Input file
    f = '/'.join([p, 'hbas/mpathadm-list-logical-unit.out'])
    check_path(f)

    lu = {}

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        for line in fh.readlines():
            # Add new dict for each lu
            if line.strip().startswith('/'):
                current = line.strip()
                lu[current] = {}
            # Split line into key/value pairs
            else:
                k, v = [x.strip() for x in line.split(':')]
                lu[current][k] = v

    return lu


def start(p):
    """
    Return the collector start date.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        start (str): Date string
    """
    # Input file
    f = '/'.join([p, 'collector.stats'])
    check_path(f)

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        for line in fh.readlines():
            if 'Script started' in line:
                start = line.split(':', 1)[1].strip()
                break

    return start


def end(p):
    """
    Return the collector end date.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        end (str): Date string
    """
    # Input file
    f = '/'.join([p, 'collector.stats'])
    check_path(f)

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        for line in fh.readlines():
            if 'Script ended' in line:
                end = line.split(':', 1)[1].strip()
                break

    return end


def version(p):
    """
    Return the appliance version.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        version (str): Appliance version
    """
    # Input file
    f = '/'.join([p, 'collector.stats'])
    check_path(f)

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        for line in fh.readlines():
            if 'Appliance version' in line:
                version = line.split(':')[1].strip()
                break

    return version


def machinesig(p):
    """
    Return the machine signature.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        machinesig (str): Machine signature
    """
    l = license(p)
    if l is not None:
        machinesig = l.split('-')[2]
    else:
        machinesig = None

    return machinesig


def license(p):
    """
    Return the appliance license.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        license (str): Appliance license
    """
    # Input file
    f = '/'.join([p, 'collector.stats'])
    check_path(f)

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        for line in fh.readlines():
            if 'License key' in line:
                license = line.split(':')[1].strip()
                break

    return license


def sesctl(p):
    """
    Parse the output of 'sesctl list <enclosure>'.

    Inputs:
        p (str): Path to collector bundle
    Outputs:
        ses (dict): Parse sesctl
    """
    # Input file
    l1 = 'enclosures/for-enclosure-in-sesctl-list-grep-v-enclosure_'
    l2 = 'id-awk-print-1-do-echo-enclosure-sesctl-list-enclosure-done.out'
    f = '/'.join([p, l1 + l2])
    check_path(f)

    ses = {}

    # Match empty lines
    empty = re.compile('^\s*$')

    # Open file with universal newline support
    restart = True
    with open(f, 'rU') as fh:
        for line in fh.readlines():
            # If restart the line contains a new enclosure ID
            if restart:
                encl_id = line.strip()
                #print encl_id
                ses[encl_id] = {}
                restart = False

            # Parse the column headers
            elif 'element-type' in line:
                head = [x.strip() for x in line.split()]
                head = head[2:]

            # Ignore empty lines
            elif empty.search(line):
                continue

            # The last line of every output starts with 'Found' and the
            # following line is the enclosure ID
            elif 'Found' in line:
                restart = True

            # If there are no elements returned
            elif 'No elements found' in line:
                restart = True

            # Parse column values
            else:
                values = [x.strip() for x in line.split()]

                # The first entry is the element-type
                e_type = values[0]
                if e_type not in ses[encl_id]:
                    ses[encl_id][e_type] = {}

                # The second entry is the element-num
                e_num = values[1]
                if e_num not in ses[encl_id][e_type]:
                    ses[encl_id][e_type][e_num] = {}

                # Add key/value pairs
                values = values[2:]
                for i in range(len(values)):
                    ses[encl_id][e_type][e_num][head[i]] = values[i]

    return ses


def zpool_status(p):
    """
    Parse 'zpool status -Dv' output.

    Inputs:
        f (str): Path to zpool status output
    Outputs:
        status (dict): Parsed zpool status
    """
    # Input file
    f = '/'.join([p, 'zfs/zpool-status-dv.out'])
    check_path(f)

    status = {}

    # Match empty lines
    empty = re.compile('^\s*$')

    # Match multiple underscores
    underscore = re.compile('^__')

    # Match dashes
    dash = re.compile('^--')

    # Open file with universal newline support
    with open(f, 'rU') as fh:
        current = None

        # Read the lines into an array
        lines = fh.readlines()

        # Certain scenarios can lead to no pools available
        # The Ready Deploy image will not return any pools for example
        if len(lines) == 0 or 'no pools available' in lines[0]:
            return None

        for line in lines:
            #Ignore empty lines and lines that start with dashes or underscores
            if empty.search(line) or        \
               underscore.search(line) or   \
               dash.search(line):
                continue

            # Lines containing ':' define a new section
            elif ':' in line:
                """
                Possible sections
                    + pool - pool name
                    + state - pool state
                    + status - pool status
                    + action - recovery action
                    + scan - scan status
                    + config - pool configuration
                    + errors - pool errors
                    + dedup - deduplication table
                """
                # Parse pool name
                if 'pool:' in line:
                    current = 'pool'
                    pool = line.split(':')[1].strip()
                    status[pool] = {}

                # Parse state
                elif 'state:' in line:
                    current = 'state'
                    state = line.split(':')[1].strip()
                    status[pool]['state'] = state

                # Parse status
                elif 'status:' in line:
                    current = 'status'
                    if current not in status[pool]:
                        status[pool][current] = []
                    status[pool][current].append(line.split(':')[1].strip())

                # Parse action
                elif 'action:' in line:
                    current = 'action'

                # Parse scan
                elif 'scan:' in line:
                    current = 'scan'
                    if current not in status[pool]:
                        status[pool][current] = []
                    status[pool][current].append(line.split(':')[1].strip())

                # Parse config
                elif 'config:' in line:
                    current = 'config'
                    status[pool]['config'] = []

                # Parse errors
                elif 'errors:' in line:
                    current = 'errors'

                # Parse dedup
                elif 'dedup:' in line:
                    current = 'dedup'
                    if 'no DDT entries' in line:
                        status[pool]['dedup'] = None
                    else:
                        status[pool]['dedup'] = []
                        status[pool]['dedup'].append(line.split(':')[1])

            else:
                # Ignore these fields
                #if current in ['status', 'action', 'scan', 'errors']:
                #    continue
                if current in ['action', 'errors']:
                    continue

                if current == 'status' or current == 'scan':
                    status[pool][current].append(line.strip())
                    continue

                status[pool][current].append(line)

    for pool in status:
        # Parse config
        status[pool]['config'] = _parse_zpool_config(status[pool]['config'])

        # Parse dedup table if dedup is enabled
        if 'dedup' in status[pool] and status[pool]['dedup']:
            status[pool]['dedup'] = _parse_zpool_dedup(status[pool]['dedup'])

        # Ignoring errors for now
        # Parse errors if they exist
        #if status[pool]['errors']:
        #    status[pool]['errors'] = parse_errors(status[pool]['errors'])

        # Ignoring scan information for now
        # Parse scan information is a scan is in progress
        #if status[pool]['scan']:
        #    status[pool]['scan'] = parse_scan(status[pool]['scan'])

    return status


def _parse_zpool_config(lines):
    """
    Parses the vdev configuration from zpool status.

    Inputs:
        lines (list): A list containing each config line
    Outputs:
        config (dict): Parsed config
    """
    # Don't bother parsing if the first line isn't the header we expect
    if not lines[0].split() == ['NAME', 'STATE', 'READ', 'WRITE', 'CKSUM']:
        return None

    # Match two or more spaces
    spaces = re.compile('\s{2,}')

    lines = lines[1:]
    config = {}
    i_level = 0

    for line in lines:
        # Ignore leading tab character
        indent = indentation(line.lstrip('\t'))
        fields = spaces.split(line.strip())
        name = fields[0]
        status = {}

        # Matches healthy active vdevs
        # NOTE the fields cannot be directly cast to ints because they may
        # contain suffixes such as K or M that indicate magnitude.
        if len(fields) == 5:
            status['state'] = fields[1]
            status['read'] = fields[2]
            status['write'] = fields[3]
            status['cksum'] = fields[4]

        # Matches active vdevs with additional status
        if len(fields) == 6:
            status['state'] = fields[1]
            status['read'] = fields[2]
            status['write'] = fields[3]
            status['cksum'] = fields[4]
            status['info'] = fields[5]

        # Matches spare drives
        if len(fields) == 2:
            status['state'] = fields[1]

        # Matches spare drives that are in use
        if len(fields) == 3:
            status['state'] = fields[1]
            status['info'] = fields[2]

        # If the indent is 0, it's a root node
        if indent == 0:
            config[name] = status
            stack = []
            stack.append(config[name])
            i_level = 0

        # This line is a child of the previous (indent)
        elif indent > i_level:
            stack[-1]['vdev'] = {}
            stack[-1]['vdev'][name.lower()] = status
            stack.append(stack[-1]['vdev'][name.lower()])
            i_level = indent

        # This line is a sibling of the previous
        elif indent == i_level:
            stack.pop()
            stack[-1]['vdev'][name.lower()] = status
            stack.append(stack[-1]['vdev'][name.lower()])

        # This line is not related to the previous (dedent)
        elif indent < i_level:
            while indent <= i_level:
                stack.pop()
                i_level -= 1
            stack[-1]['vdev'][name.lower()] = status
            stack.append(stack[-1]['vdev'][name.lower()])

    return config


def _parse_zpool_dedup(lines):
    """
    Parse the dedup stats from the output of zpool status.

    Inputs:
        lines (list): A list containing each dedup line
    Outputs:
        dedup (dict): Parsed dedup
    """
    dedup = {}

    entries, size, core = lines[0].split(',')
    dedup['entries'] = int(entries.split()[2])
    dedup['size'] = int(size.split()[1])
    dedup['core'] = int(core.split()[0])
    lines = lines[1:]

    dedup['ddt'] = {}
    for line in lines:
        # Ignore headings
        if line.split() == ['bucket', 'allocated', 'referenced']:
            continue

        # Ignore headings
        headings = ['refcnt',   \
                    'blocks',   \
                    'LSIZE',    \
                    'PSIZE',    \
                    'DSIZE',    \
                    'blocks',   \
                    'LSIZE',    \
                    'PSIZE',    \
                    'DSIZE']
        if line.split() == headings:
            continue

        refcnt, a_blocks, a_lsize, a_psize, a_dsize, r_blocks, r_lsize, \
            r_psize, r_dsize = line.strip().split()
        dedup['ddt'][refcnt.lower()] = {
            'allocated': {
                'blocks': a_blocks,
                'lsize': a_lsize,
                'psize': a_psize,
                'dsize': a_dsize
            },
            'referenced': {
                'blocks': r_blocks,
                'lsize': r_lsize,
                'psize': r_psize,
                'dsize': r_dsize
            }
        }

    return dedup


def _parse_zpool_scan(s):
    pass


def _parse_zpool_errors(e):
    pass


def indentation(s, spaces=2):
    """
    Return identation level

    Inputs:
        s      (str): String
        spaces (int): Spaces per tabstop
    Outputs:
        level (int): Identation level
    """
    i = 0
    for c in s:
        if c == ' ':
            i += 1
        else:
            return i / spaces
    return i / spaces


def read_raw_txt(rawfile):
    rawlines = []
    with open(rawfile, 'r') as f:
        for l in f.readlines():
            pattern = '^#.*$'           # skip comment lines
            if re.match(pattern, l):
                continue
            rawlines.append(l.rstrip('\n'))

    return rawlines


def json_save(bdir, jsdmp, jsonfile):
    debug = False
    odir = os.path.join(bdir, 'ingestor/json')
    if not os.path.exists(odir):
        os.mkdir(odir)
    ofile = os.path.join(odir, os.path.basename(jsonfile))

    if debug:
        print 'out file:', ofile
        print "JSON Dump:"
        print jsdmp
    else:
        with open(ofile, 'wt') as f:
            f.write(jsdmp)


def valid_file(fname):
    ofile = fname + '.out'

    if os.path.exists(ofile):
        return True
    return False


def valid_tball(fname):
    tfile = fname + '.tar.gz'

    if os.path.exists(tfile):
        return True
    return False


def valid_gzip(fname):
    gzfile = fname + '.out.gz'

    if os.path.exists(gzfile):
        return True
    return False


class Errors:
    # 0,    1,      2,       3,     4,     5,      6,     7
    e_ok, e_mpty, e_noent, e_tok, e_zok, e_nzrc, e_nan, e_stok = range(8)


def output_status(fname):
    sfile = fname + '.stats'

    if os.path.exists(sfile):           # stats file exists ?
        size = os.stat(sfile).st_size
        if size > 0:
            with open(sfile, 'r') as f:
                for l in f.readlines():
                    l.rstrip('\n')
                    pattern = '^#.*$'           # skip comment lines
                    mp = re.match(pattern, l)
                    if mp:
                        continue

                    pattern = '^[A-Za-z0-9-_ ]* return code: (.*)$'
                    mp = re.match(pattern, l)
                    if mp:
                        try:
                            rc = int(mp.group(1))
                        except ValueError:
                            return Errors.e_nan

                        if rc != 0:
                            return Errors.e_nzrc
                        break
            return Errors.e_stok
    return Errors.e_noent


def valid_tar_gz(fname):
    ftgz = fname + '.tar.gz'

    if not os.path.exists(ftgz):        # tar.gz file exists ?
        return Errors.e_noent

    rc = output_status(fname)
    if rc != Errors.e_stok:
        return rc

    return Errors.e_ok


def valid_out_gz(fname):
    fogz = fname + '.out.gz'

    if not os.path.exists(fogz):        # out.gz file exists ?
        return Errors.e_noent

    rc = output_status(fname)
    if rc != Errors.e_stok:
        return rc

    return Errors.e_ok


def valid_output(fname, skip=False):
    ofile = fname + '.out'

    if valid_file(fname):
        size = os.stat(ofile).st_size        # is file empty ?
        if size <= 0:
            if valid_tball(fname):
                return Errors.e_tok
            return Errors.e_mpty
    else:
        return Errors.e_noent

    if valid_gzip(fname):
        return Errors.e_zok

    if skip:
        return Errors.e_ok

    rc = output_status(fname)
    if rc != Errors.e_stok:
        return rc

    return Errors.e_ok
