#!/usr/bin/env python
#
#  Ingestor Tool / System Daemon
#  Copyright 2015 Nexenta Systems, Inc.  All rights reserved.
#
#  This python script is meant to be run on the Ingestor System
#  (that is, a separate OS instance than that of the receiving
#  ftp server) to choreograph ingestion of a Collector bundle.
#
#  It can either be run manually in order to ingest or reingest
#  a specified Collector bundle. If the bundle specified is not
#  a fully qualified path name, the script will assume the bundle
#  is already in the /mnt/carbon-steel/upload dir. This utiilty
#  can also be started as a system daemon that will be constantly
#  running (the most expected use case) and will get notified via
#  TCP/IP from the ftp server when a new bundle is ready to be
#  ingested.
#
#  NB: The default instantiation of this script performs the
#      action specified via cmd line arguments w/o storing any
#      ingestion progress in a database. However, this script
#      has the ability to utilize a MySQL DB instance in order
#      to record ingestions and the bundle's current ingestion
#      step by the specification of the --db-enable option.
#
#      In order to specify a valid MySQL DB instance and creds,
#      this script's db_user, db_pass and db_name variables MUST
#      be used. If a database is to be used, it is expected to
#      contain an 'ingestions' and a 'steps' tables, even if 
#      empty.
#
import os
import re
import sys
import pwd
import grp
import time
import atexit
import signal
import socket
import tarfile
import inspect
import optparse
import platform
from pprint import pprint
import subprocess
from SocketServer import *
from lib.CText import *


DB = ''
currdir = os.getcwd()
basedir = '/mnt/carbon-steel'
uplddir = os.path.join(basedir, 'upload')
ingddir = os.path.join(basedir, 'ingested')
linkdir = os.path.join(ingddir, 'links')
clardir = os.path.join(basedir, 'collector_archive')
#scrpdir = os.path.join(currdir, 'ingestion-scripts')
bdlpath = ''
ing_ver = '1.0.0'
dbginfo = 0
timedbg = 0
dbgpeek = 0
dbdebug = 0
db_actn = ''
db_indx = 0
procdbg = 0
xdirdbg = 0
cs_lkey = ''
cs_host = ''
cs_date = ''
program = ''
fqtd = ''
tard = ''
date = ''
sysfile = '/tmp/NXTA_Ingestor.daemon'
pidfile = sysfile + '.pid'
logfile = sysfile + '.log'
tcpaddr = '127.0.0.1'
tcpport = 12345
tcpresp = ''
month = dict(Jan='01', Feb='02', Mar='03', Apr='04',
             May='05', Jun='06', Jul='07', Aug='08',
             Sep='09', Oct='10', Nov='11', Dec='12')
commands = ['peek', 'ingest', 'reingest']
db_enable = False
db_user = 'root'
db_pass = 'nexenta'
db_name = 'cookbook'
OS = ''
PyV = ''


def debug():
    print_debug('\n########## DEBUG ##########\n', True)
    print "Program:\t",     program
    print "Base:\t\t",      basedir
    print "Upload:\t\t",    uplddir
    print "Ingested:\t",    ingddir
    print "Links:\t\t",     linkdir
    print "Coll Arch:\t",   clardir
    print "Current WD\t",   currdir


def stop(e):
    print_fail('*** Stopping Now ! ***')
    sys.exit(e)


def log(lname, msg):
    global PyV

    print PyV
    if PyV < '2.7.3':
        ln = time.strftime("%a %b %d %H:%M:%S %Y", time.strptime(time.ctime()))
        ft = ln + msg
    else:
        line = '{}' + msg
        ft = line.format(time.ctime())

    with open(lname, 'ab', 0) as f:
        os.write(f.fileno(), ft)


def usage(p, msg):
    if msg:
        print_warn(msg, True)
    p.print_help()

    if dbginfo:
        debug()

    print ''
    sys.exit(100)


#
# Time Manipulation Helper Functions
#
def now():
    return time.ctime(time.time())


def fnow():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def time_normalize(s):
    return time.strftime("%a %b %d %H:%M:%S %Y", time.strptime(s))


def cst2dbt(cst):
    """
    #
    # collector.stats time to DB time
    # '2014-05-13 11:51:20' = cst2dbt('Mon May 13 11:51:20 2014')
    #
    """
    ntm = time_normalize(cst)
    if timedbg:
        print_bold('cst2dbt Input:\t', 'white', False)
        print_debug(ntm, True)
    fields = ntm.split()

    yr = fields[-1]
    mo = fields[1]
    dy = fields[2]
    ts = fields[-2]
    tmpd = yr + '-' + month[mo] + '-' + dy + ' ' + ts

    if timedbg:
        print_bold('cst2dbt Output:\t', 'white', False)
        print_debug(tmpd, True)
    return tmpd


def fmt_time(tstr, how):
    """
    #
    # "tstr" expected to be in 'Mon May 13 11:51:20 2014' format
    #
    """
    dbtime = cst2dbt(tstr)

    if timedbg:
        print_bold('fmt_time Input:\t', 'white', False)
        print_debug(tstr + ', ' + how, True)

    if how == 'ymd':
        retstr = dbtime.split(' ')[0]
    elif how == 'hms':
        retstr = re.sub(r':', '-', dbtime.split(' ')[1])
    else:
        retstr = 'Unrecognized Time Fmt'

    if timedbg:
        print_bold('fmt_time Output:\t', 'white', False)
        print_debug(retstr, True)

    return retstr


#
# Stack Related Helper Functions
#
def whoami():
    return inspect.stack()[1][3]        # Name of current function


def caller():
    return inspect.stack()[2][3]        # Name of caller function


#
# DataBase Related Helper Functions
#
def db_connect(user, passwd, dbname):
    try:
        con = DB.connect('localhost', user, passwd, dbname)
        cur = con.cursor()

    except DB.Error, e:
        print "Error %d: %s" % (e.args[0], e.args[1])
        sys.exit(1)

    return con, cur


def db_execute(cur, cmd, echo):
    """
    #
    # do_execute returns tuple of tuples
    #
    """
    cur.execute(cmd)
    res = cur.fetchall()
    if echo:
        for r in res:
            print_bcmplx(r, 'green', True)

    return res


def db_show_table(cur, con, dbtab):
    sql = 'select * from %s;' % dbtab
    try:
        db_execute(cur, sql, True)

    except NameError as e:
        pprint(e)
        sys.exit(1)

    return


def db_print(tab, key, val):
    con, cur = db_connect(db_user, db_pass, db_name)

    sql = 'SELECT * from %s WHERE %s=%d;' % (tab, key, val)
    for r in db_execute(cur, sql, False):
        print_pass('Ingestions @ %s=%d' % (key, val))

    return


def db_find_entry(tab, key, val):
    con, cur = db_connect(db_user, db_pass, db_name)

    sql = 'SELECT id FROM %s WHERE %s="%s";' % (tab, key, val)
    try:
        idx = db_execute(cur, sql, False)

    except NameError as e:
        pprint(e)
        stop(98)

    if idx:
        return idx
    return None


def db_update_entry(tab, indx, step):
    con, cur = db_connect(db_user, db_pass, db_name)

    s = 'UPDATE %s SET last_updated_at=\'%s\', ' % (tab, fnow())
    q = 'current_step = %s WHERE id = %d;' % (step, indx)
    sql = s + q

    try:
        db_execute(cur, sql, False)
        con.commit()

    except NameError as e:
        pprint(e)
        stop(99)

    return


def db_insert_entry(tab, ent):
    con, cur = db_connect(db_user, db_pass, db_name)

    t = 'INSERT INTO %s ' % tab
    p = '(id, uploaded_fullpath, tarball_fullpath, ' +\
        'final_fullpath, created_at, last_updated_at, current_step) VALUES '
    s = "(%d, \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', %d)" %\
        (0, ent[0], ent[1], ent[2], ent[3], ent[4], ent[5])
    sql = t + p + s + ";"

    if dbdebug:
        print "sql: ", sql

    try:
        db_execute(cur, sql, False)
        con.commit()

    except NameError as e:
        pprint(e)
        sys.exit(99)

    db_show_table(cur, con, tab)
    return


#
# db_scan() checks for existing entries that have the exact same
# 'tarball_fullpath'; if one exists, then db_actn will be set to
# 'update'. If none exist, db_actn will be set to 'insert' a new
# entry.
#
def db_scan():
    global db_actn
    global db_indx
    global fqtd

    if dbdebug:
        print_warn('Start DB Debug', True)

    dbt = 'ingestions'
    key = 'tarball_fullpath'
    ne = 0
    idx = db_find_entry(dbt, key, fqtd)
    if idx is not None:
        for i in idx:
            ne += 1

    if ne == 0:
        db_actn = 'insert'
        if dbdebug:
            print_pass('New Entry to be Inserted')
    elif ne == 1:
        db_actn = 'update'
        db_indx = i[0]
        if dbdebug:
            print_pass('Entry to be Updated...')
            db_print(dbt, 'id', db_indx)
    else:
        print_warn('DB Entries Found: ' + str(ne), False)
        print_fail('Unable to continue.... DB inconsistency')
        stop(111)

    if dbdebug:
        print_warn('End DB Debug', True)

    return


def db_new_entry():
    """
    #
    # Insert a new ingestion entry in DB
    #
    """
    global bdlpath
    global fqtd
    global cs_date
    global clardir
    global date

    table = 'ingestions'
    tarb = os.path.basename(bdlpath)
    bdir = os.path.dirname(bdlpath)
    if len(bdir) == 0:
        bdir = uplddir

    upfp = os.path.join(bdir, tarb)
    trfp = fqtd
    fdir = os.path.join(os.path.join(clardir, date), tarb)
    crtd = cst2dbt(cs_date)
    uptd = fnow()
    step = 9
    entry = [upfp, trfp, fdir, crtd, uptd, step]
    if dbdebug:
        print "Table: ", table
        print "Entry: "
        for e in entry:
            print '\t', e

    db_insert_entry(table, entry)


def DBShowTab(dbtab, cc):
    con, cur = db_connect(db_user, db_pass, db_name)
    db_show_table(cur, con, dbtab)
    con.close()
    return


def DBTabEntry(dbtab, idx, cc):
    con, cur = db_connect(db_user, db_pass, db_name)
    sql = 'select * from %s where id = %d;' % (dbtab, idx[0])
    try:
        db_execute(cur, sql, True)

    except NameError as e:
        pprint(e)
        sys.exit(5)

    return


def DBPeek(fpath, cc):
    print 'DBPeek args:\t', fpath
    f = Peek(fpath, cc)
    print 'DBPeek final:\t', f

    dbt = 'ingestions'
    key = 'tarball_fullpath'
    lst = db_find_entry(dbt, key, f)
    if not lst:
        print_bold('DBPeek:\t', 'red', False)
        print_debug(f, False)
        print_fail('does NOT exist in the DB')
        return

    for i in lst:
        DBTabEntry(dbt, i, cc)

    return


#
# TCP Server Helper Functions
#
def TCP_Handle_Request(rqst):
    """
    #
    # Valid TCP cmds:
    #
    #   peek     - get bundle creation date from the collector.stat file
    #   ingest   - perform initial ingestion and execute all ingestor scripts
    #   reingest - redo ingestion of a previously ingested collector bundle
    #
    # Expected TCP pkt format:
    #
    #   'cmd collector-bundle-path'
    #
    #   where: collector-bundle-path MUST be a Fully Qualified Collector
    #       Bundle (fqcb) name or it may be of type "filename.tar.gz" if
    #       it is KNOWN to already exist in the '/mnt/carbon-steel/upload'
    #       directory of the ftp server.
    """
    global date
    global bdlpath
    cmd, arg = rqst.split(' ')

    bdlpath = arg
    resp = ''
    cc = 'net'
    pds = 'Pid %d executing \"%s\" @ %s' % (os.getpid(), cmd, now())

    if cmd in commands:
        fn = fqcb(arg, cc)
        if fn is None:
            reply = '%s: Bundle %s does not exist !' % (pds, arg)
            if len(tcpresp) == 0:
                resp = reply
            else:
                resp = reply + tcpresp
            return resp

        if cmd == 'peek':
            Peek(arg, cc)
            resp = '%s %s created on %s' % (pds, tcpresp, date)
            return resp

        elif cmd == 'ingest':
            if Ingest(arg, cc):
                resp = tcpresp
            else:
                resp = '%s %s ingested on %s' % (pds, tard, now())
            return resp

        elif cmd == 'reingest':
            if Reingest(arg, cc):
                resp = tcpresp
            else:
                resp = '%s %s reingested on %s' % (pds, tard, now())
            return resp

        else:
            resp = '%s %s' % (pds, cmd + ' not yet implemented')
    else:
        resp = '%s %s' % (pds, cmd + ': no such command')

    return resp


class TCP_Ingestion_Handler(StreamRequestHandler):
    def handle(self):
        print(self.client_address, now())
        while True:
            data = self.request.recv(1024)
            if not data:
                break
            reply = TCP_Handle_Request(data)
            self.request.send(reply.encode())
        try:
            self.request.close()
        except:
            pass


class TCP_Forking_Server(ForkingTCPServer):
    def serve_forever(self):
        def sigterm_handler(signo, frame):
            sys.stderr.write('\nSIGINT Detected\n')
            raise SystemExit(1)
        signal.signal(signal.SIGINT, sigterm_handler)

        while True:
            self.handle_request()

    def collect_children(self):
        pass


def collector_stats(fd):
    global cs_date
    global date

    if fd is None:
        print_warn('fd is not yet set!', True)
        stop(5)
    lines = fd.readlines()

    # License Key
    pattern = "^License\s+key:\s*(.*)$"
    for l in lines:
        mp = re.match(pattern, l)
        if mp:
            lk = mp.group(1)
    cs_lkey = lk

    # Hostname
    pattern = "^Hostname:\s*(\w+)\s*.*$"
    for l in lines:
        mp = re.match(pattern, l)
        if mp:
            hn = mp.group(1)
    cs_host = hn

    # Date
    pattern = "^Script\s*started:\s*(.*)$"
    dt = None
    for l in lines:
        mp = re.match(pattern, l)
        if mp:
            dt = mp.group(1)
    cs_date = dt

    if dbginfo:
        print_debug('License Key:\t%s' % cs_lkey, True)
        print_debug('Hostname:\t%s' % cs_host, True)
        print_debug('Script start:\t%s' % cs_date, True)

    date = fmt_time(dt, 'ymd')
    return


def is_compressed(fname):
    """
    #
    # Crude detection method a compressed file based on file
    # extension. If the extension is indeed of the expected
    # formats (bz2, gz), return the right tool for extraction
    #
    """
    ext = fname.split('.')[-1]
    if ext != "bz2" and ext != "gz":
        return None

    if ext == 'bz2':
        extract_tool = 'bunzip2'
    elif ext == 'gz':
        extract_tool = 'gunzip'
    else:
        extract_tool = None

    return extract_tool


def reingest_prep(fname):
    global linkdir
    global currdir
    global tard

    jinged = fname
    jinged_at = fname + '_at'

    if dbginfo:
        print_bold('Caller:\t', 'white', False)
        print_pass('\"Reingest\"')

    if os.path.exists(jinged):
        if dbginfo:
            print_bold('Removing:\t', 'white', False)
            print_debug(jinged, True)
        os.unlink(jinged)

    if os.path.exists(jinged_at):
        if dbginfo:
            print_bold('Removing:\t', 'white', False)
            print_debug(jinged_at, True)
        os.unlink(jinged_at)

    if os.path.exists(linkdir):
        os.chdir(linkdir)
        if os.path.exists(tard):
            if dbginfo:
                print_bold('Removing:\t', 'white', False)
                print linkdir + '/' + tard
            os.unlink(tard)

    os.chdir(currdir)
    return


def reingest_post(sfile, ffile):
    if dbginfo:
        print_bold('Caller:\t', 'white', False)
        print_pass('\"Reingest\"')

    if os.path.exists(sfile):
        if dbginfo:
            print_bold('Removing:\t', 'white', False)
            print_debug(sfile, True)
        os.unlink(sfile)

    if os.path.exists(ffile):
        if dbginfo:
            print_bold('Removing:\t', 'white', False)
            print_debug(ffile, True)
        os.unlink(ffile)
    return


def extract_bundle(fname, cc):
    """
    #
    # Before bundle extraction, we MUST make sure this is
    # a bonafide collector bundle. If so, we go ahead and
    # extract in the 'ingested/YYYY-MM-DD' directory
    #
    """
    global fqtd
    global tard
    global date
    global tskip
    global OS
    global db_enable

    #
    # Create fully qualified tar extraction directory
    # and perform the extraction there. We have to do
    # a bit of shell hand-waving as the tarfile module
    # is not able to readily strip 'var/tmp' prefix.
    #
    fqbn = fqcb(fname, cc)
    if fqbn is None:
        return

    tard = derive_xdir(fqbn, cc)
    if not os.path.exists(ingddir):
        os.mkdir(ingddir)
    ddir = os.path.join(ingddir, date)
    if not os.path.exists(ddir):
        os.mkdir(ddir)
    fqtd = os.path.join(ddir, tard)

    if db_enable and OS == 'Linux':
        db_scan()

    cs = [is_compressed(fname), ' < ', fqbn, ' | ', '( cd ', ddir,
           '; tar --strip-components=' + str(tskip), ' -xpf - )']
    cmd = "".join(cs)
    os.popen(cmd)

    jinged = os.path.join(fqtd, '.just_ingested')
    jinged_at = jinged + '_at'
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_TRUNC

    if caller() == 'Reingest':
        reingest_prep(jinged)

    try:
        os.close(os.open(jinged, flags, 0644))
    except:
        errmsg = 'Fatal Error: file ' + jinged + ' already exists'
        if cc == 'cli':
            print_fail(errmsg)
            raise SystemExit(1)
        else:
            tcpresp = errmsg
            return

    if dbginfo:
        print_debug('\nTarfile: %s extracted in %s\n' % (fname, fqtd), True)

    #
    # Create links
    #
    if not os.path.exists(linkdir):
        os.mkdir(linkdir)
    os.chdir(linkdir)
    try:
        os.symlink(fqtd, tard)
    except:
        None
    os.chdir(currdir)

    #
    # Move Collector Bundle to "collector_archive" directory.
    #
    if not os.path.exists(clardir):
        os.mkdir(clardir)

    dest = os.path.join(clardir, date)
    if not os.path.exists(dest):
        os.mkdir(dest)
    os.chdir(dest)
    bnm = os.path.basename(fname)

    if dbginfo:
        if cc == 'cli':
            print_debug('%s will be moved to %s/%s\n' % (fqbn, dest, bnm), True)
    os.rename(fqbn, os.path.join(dest, bnm))


def step_from_script(fn):
    pattern = '^A([0-9]+).*$'
    mp = re.match(pattern, fn)
    if (mp):
        return mp.group(1)
    return 'No Match'


def get_ingestor_scripts():
    if not os.path.exists(scrpdir):
        print scrpdir, "MUST exist and contain the ingestion scripts"
        stop(9)

    scripts = []
    pattern = '^(A[1-9]+.*)$'
    for i in sorted(os.listdir(scrpdir)):
        mp = re.match(pattern, i)
        if mp:
            scripts.append(mp.group(1))

    return scripts


def nukedir(path):
    # remove all files
    for dirname, subdirs, files in os.walk(path):
        for name in files:
            fullname = os.path.join(dirname, name)
            if dbginfo:
                print_debug('Removing file:', False)
                print fullname
            os.unlink(fullname)

    # remove all subdirs
    for sd in subdirs:
        fullsub = os.path.join(dirname, sd)
        if dbginfo: 
            print_warn('Removing dir:', False)
            print fullsub
        os.rmdir(fullsub)

    # remove 'path'
    if dbginfo:
        print_bold('Removing dir:', 'green', False)
        print dirname
    os.rmdir(dirname)


def ingest_scripts():
    global fqtd
    global OS
    global db_enable

    owner = 'ftp'
    usrid = pwd.getpwnam(owner).pw_uid
    group = 'nexentians'
    grpid = 10
    try:
        grpid = grp.getgrnam(group).gr_gid
    except KeyError:
        group = 'staff'
        grpid = grp.getgrnam(group).gr_gid
    fmode = 0660
    dmode = 0770
    ing_dir = os.path.join(fqtd, 'ingestor')
    ing_lgs = os.path.join(fqtd, '.ingestor_logs')
    act_log = os.path.join(fqtd, '.ingestor_activity_log')

    if os.path.exists(ing_dir):
        nukedir(ing_dir)
    if os.path.exists(ing_lgs):
        nukedir(ing_lgs)
    if os.path.exists(act_log):
        os.unlink(act_log)

    #
    # Execute all ingestor scripts in scrpdir
    #
    os.chdir(scrpdir)
    for s in get_ingestor_scripts():
        log(act_log, '|' + s + '|started\n')
        try:
            os.mkdir(ing_lgs)
        except OSError as e:
            pass

        dnr = ' > /dev/null 2>&1'
        fqsn = os.path.join(scrpdir, s)
        cmd = "".join([fqsn, ' ', fqtd, dnr])
        sts = subprocess.call(cmd, stdin=subprocess.PIPE, shell=True)
        if sts != 0 and dbginfo:
            print_debug('** %s = %s **' % (cmd, sts), True)
        log(act_log, '|' + s + '|done|' + str(sts) + '\n')

        if db_enable and OS == 'Linux':
            if sts == 0 and db_actn == 'update':
                step = step_from_script(s)
                if step != 'No Match':
                    db_update_entry('ingestions', db_indx, step)

    #
    # Everything should be owned by owner:group,
    # dirs should be 770 and regular files 660
    #
    for dirname, subdirs, files in os.walk(fqtd):
        os.chown(dirname, usrid, grpid)
        os.chmod(dirname, dmode)
        for name in files:
            fullname = os.path.join(dirname, name)
            os.chown(fullname, usrid, grpid)
            os.chmod(fullname, fmode)

    log(act_log, '|finished|\n')
    return sts


def ingest_bundle(cc):
    global fqtd
    global tard
    global tcpresp
    global OS
    global db_enable

    if db_enable and OS == 'Linux':
        global db_actn

    status = 0

    jinged = os.path.join(fqtd, '.just_ingested')
    jinged_at = jinged + '_at'
    ing_started = os.path.join(fqtd, '.ingestor_started')
    ing_finished = os.path.join(fqtd, '.ingestor_finished')

    cf = caller()
    if cf == 'Reingest':
        reingest_post(ing_started, ing_finished)

    if os.path.exists(jinged) and not os.path.exists(jinged_at):
        if cc == 'cli':
            print_debug('%sing:\t' % cf, False)
            print tard
        else:
            tcpresp = cf + 'ing:\t' + tard
        os.rename(jinged, jinged_at)

        log(ing_started, '\n')
        rc = ingest_scripts()
        log(ing_finished, '\n')

        if rc == 0:
            if cc == 'cli':
                print_bold('%sion Successful !' % cf, 'green', True)
        else:
            if cc == 'cli':
                print_fail('%ion Failed !' % cf)
                stop(10)
    else:
        errmsg = 'Error: Attempting to %s an already ingested directory' % cf
        print errmsg
        print_fail(tard)
        if cc == 'cli':
            stop(11)
        else:
            tcpresp = errmsg + tard
            status = 1

    if db_enable and OS == 'Linux':
        if db_actn == 'insert':
            db_new_entry()
        else:
            db_print('ingestions', 'id', db_indx)

    return status


def fqcb(path, cc):
    pattern = '^(\/.*)$'
    mp = re.match(pattern, path)
    if mp:                          # Full path provided
        nm = mp.group(1)

        if dbginfo:
            print "[fqcb match]: ", nm

        if not os.path.exists(nm):  # Stop if it doesn't exist
            errmsg = nm + ' does not exist !!!'
            if cc == 'cli':
                print_debug(errmsg, True)
                stop(1)
            else:
                tcpresp = errmsg
                return None
        elif not is_compressed(nm):
            errmsg = nm + " is not a compressed file !!!"
            if cc == 'cli':
                print_debug(errmsg, True)
                stop(2)
            else:
                tcpresp = errmsg
                return None
        return nm

    # Only bundle name provided (not full path)

    # Check uploads directory for existence...
    nm = os.path.join(uplddir, os.path.basename(path))
    if not os.path.exists(nm):
        errmsg = nm + ' does not exist !!!'
        if cc == 'cli':
            print_debug(errmsg, True)
            stop(3)                # Stop if it doesn't exist
        else:
            tcpresp = errmsg
            return None
    elif not is_compressed(nm):
        errmsg = nm + " is not a compressed file !!!"
        if cc == 'cli':
            print_debug(errmsg, True)
            stop(4)
        else:
            tcpresp = errmsg
            return None
    return nm


#
#  Ingest/Reingest the Collector Bundle denoted fpath
#
#  Both Ingest and Reingest functions perform similar checks:
#
#  - is fpath a compressed file (bz2 or gzip)
#  - is fpath indeed a bonafide Collector bundle
#  - if fpath is not a fully qualified path name, the bundle file
#    should exist in upload dir
#
#  Once all of the above checks are performed, the bundle is
#  extracted into the appropriate dir in 'ingested/YYYY-MM-DD'
#  where the date is obtained from the collector.stats file
#  that is part of the bundle itself. Finally, all the scripts
#  in ingestion-scripts are run in sorted order.
#
#  NB: Resist the temptation to squash Reingest and Ingest func's
#      together. Lower level routines depend on the context of who
#      the caller is and perform specific tasks based on the caller
#      context. Also, in addition, we may want to perform additional
#      or totally different tasks for Ingest/Reingest in the future.
#
def Reingest(fpath, cc):
    """
    # Reingest
    #
    # NXTA_Ingestor --reingest { foo.tar.gz | /fully/qualified/path/to/bundle }
    """
    if cc == 'cli':
        print_bold('%sing:\t' % whoami(), 'white', False)
        print '\"%s\"' % fpath

    bundle = fqcb(fpath, cc)
    extract_bundle(bundle, cc)
    return ingest_bundle(cc)


def Ingest(fpath, cc):
    """
    # Ingest
    #
    # NXTA_Ingestor --ingest { foo.tar.gz | /fully/qualified/path/to/bundle }
    """
    if cc == 'cli':
        print_bold('%sing:\t' % whoami(), 'white', False)
        print '\"%s\"' % fpath

    bundle = fqcb(fpath, cc)
    extract_bundle(bundle, cc)
    return ingest_bundle(cc)


def daemonize(pidf, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    #
    # Only one instance allowed
    #
    if os.path.exists(pidf):
        raise RuntimeError('daemon already running')

    try:
        if os.fork() > 0:
            raise SystemExit(0)
    except OSError as e:
        raise RuntimeError('Detach from parent failed.')

    os.chdir('/')
    os.umask(0)
    os.setsid()

    try:
        if os.fork() > 0:
            raise SystemExit(0)
    except OSError as e:
        raise RuntimeError('Failed to become session group leader.')

    #
    # redirect stdin, stdout, stderr
    #
    sys.stdout.flush()
    sys.stderr.flush()

    with open(stdin, 'rb', 0) as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open(stdout, 'ab', 0) as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
    with open(stderr, 'ab', 0) as f:
        os.dup2(f.fileno(), sys.stderr.fileno())

    #
    # PID file processing; will be removed on exit/signal
    #
    with open(pidf, 'w') as f:
        os.write(f.fileno(), str(os.getpid()))
    atexit.register(lambda: os.remove(pidf))

    #
    # Signal handler for termination (required)
    #
    def sigterm_handler(signo, frame):
        if signo == signal.SIGTERM:
            with open(stdout, 'ab', 0) as f:
                os.write(f.fileno(), 'SIGTERM received !\n')
        raise SystemExit(1)

    signal.signal(signal.SIGTERM, sigterm_handler)


def start_svc():
    print 'start_svc(): system daemon mode ( pid in', pidfile, ')'

    try:
        daemonize(pidfile, stdin='/dev/null', stdout=logfile, stderr=logfile)
    except RuntimeError as e:
        sys.stderr.write('Fatal error: {}\n'.format(e))
        raise SystemExit(1)

    # make it so that new processes don't end up as zombies
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    srva = (tcpaddr, tcpport)
    s = TCP_Forking_Server(srva, TCP_Ingestion_Handler,
        bind_and_activate=False)
    s.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    s.server_bind()
    s.server_activate()
    s.serve_forever()


#
#  Given a tar.gz or tar.bz2 fully qualified bundle name, crack it
#  open and look for the collector.stats file. If 'collector.stats'
#  exists, this is a bonafide bundle so collector_stats() is called
#  to process some key values. Taking advantage of the fact that 'i'
#  contains the fqbn, the collector extraction directory is plucked
#  out of the string and its prefix processed in order to calculate
#  the number of components to strip off out of the tar file (see
#  extract_bundle() for details). Finally the collector extraction
#  directory is returned.
#
def derive_xdir(fqbn, cc):
    global tskip

    try:
        names = tarfile.open(fqbn, 'r:*').getnames()
    except:
        sys.stderr.write('Fatal error: Cannot open collector bundle\n')
        stop(101)

    for i in names:
        pattern = "\S*collector\.stats$"
        mp = re.match(pattern, i)
        if mp:
            fd = tarfile.open(fqbn, 'r:*').extractfile(i)
            if fd:
                collector_stats(fd)

            patt = "^(\S+)/(collector[a-zA-Z0-9_.-]*)/\S*$"
            mp1 = re.match(patt, i)
            if mp1:
                prefix = mp1.group(1)
                xdir = mp1.group(2)

                tskip = 1 if len(re.split('/', prefix)) == 1 else 2
                return xdir

    return None


def Peek(fpath, cc):
    """
    # Peek
    #
    # NXTA_Ingestor --peek { foo.tar.gz | /fully/qualified/path/to/bundle }
    """
    global tard
    global cs_date
    global tcpresp

    upload = os.path.dirname(fpath)
    basedr = os.path.dirname(upload)
    me = whoami()

    if cc == 'cli':
        print_bold('%sing:\t' % me, 'white', False)
        print '\"%s\"' % fpath

    fqbn = fqcb(fpath, cc)
    if dbgpeek:
        print_bold('FQBN:\t\t', 'white', False)
        print_debug(fqbn, True)

    tard = derive_xdir(fqbn, cc)
    if dbgpeek:
        print_bold('Derived:\t', 'white', False)
        print_debug(tard, True)
        print_bold('TSTRING:\t', 'white', False)
        print_debug(cs_date, True)

    yymmdd = fmt_time(cs_date, 'ymd')
    if dbgpeek:
        print_bold('YYMMDD:\t\t', 'white', False)
        print_debug(yymmdd, True)

    if upload == uplddir:
        prtdisp = 'bold'
    else:
        dyofyr = yymmdd
        prtdisp = 'lite'

    final = os.path.join(ingddir, yymmdd, tard)

    if cc == 'cli':
        print_pass('%sing Successful !' % me)
        print_bold('Final:\t\t', 'white', False)
        if prtdisp == 'bold':
            print_pass(final)
        else:
            print_lite(final, 'green', True)
    else:
        tcpresp = me + ' Derived Name: ' + final

    return final


def process_args():
    """
    #
    # Valid Options:
    #
    #   --ingest    path_to_collector_bundle [ --db-enable ]
    #   --reingest  path_to_collector_bundle [ --db-enable ]
    #   --peek      path_to_collector_bundle
    #   --dbt       path_to_collector_bundle --db-enable
    #   --service
    #
    """
    global OS
    global bdlpath
    global db_enable
    global program

    c = Colors()
    umsg = program + c.bold_white + ' --ingest ' + c.reset +                \
        'path_to_compressed_bundle' + ' [ ' + c.bold_white + '--db-enable' +\
        c.reset + ' ]' + '\n' + 7*' ' + program + c.bold_white +            \
        ' --reingest' + c.reset + ' path_to_compressed_bundle [ ' +         \
        c.bold_white + '--db-enable' + c.reset + ' ]' + '\n' + 7*' ' +      \
        program + c.bold_white + ' --peek' + c.reset +                      \
        ' path_to_compressed_bundle' + '\n' + 7*' ' + program + c.bold_white\
        + ' --service' + c.reset + '\n'

    if OS == 'Linux':
        usage_msg = umsg + 7*' ' + program + c.bold_white + ' --dbt ' +     \
            c.reset + 'path_to_compressed_bundle' + c.bold_white +          \
            ' --db-enable' + c.reset + '\n'
    else:
        usage_msg = umsg

    parser = optparse.OptionParser(usage=usage_msg)

    parser.add_option('--ingest', dest='bpath', type='str', default=None,
        help='Ingest collector bundle \"BundlePath\"; refer to ' +          \
        c.bold_white + ' --db-enable ' + c.reset + 'for database insertion.',
        metavar='BundlePath', nargs=1)
    parser.add_option('--reingest', dest='rbpath', type='str', default=None,
        help='Re-Ingestion of previously ingested bundle \"BundlePath\"; '
        'refer to' + c.bold_white + ' --db-enable ' + c.reset + 'for database'
        ' insertion.', metavar='BundlePath', nargs=1)
    parser.add_option('--db-enable', action='store_true', default=False,
        help='Optional argument to enable database functionality: use ' +   \
        'script variables ' + c.bold_white + 'db_user, db_pass' + c.reset + \
        ' and ' + c.bold_white + 'db_name' + c.reset + ' to identify DB' +  \
        ' instance')
    parser.add_option('--peek', dest='pbpath', type='str', default=None,
        help='Peek inside collector bundle \"BundlePath\"',
        metavar='BundlePath', nargs=1)
    parser.add_option('--service', dest='daemon', action='store_true',
        default=False, help='Run ' + program + ' as a TCP Server daemon')
    if OS == 'Linux':
        parser.add_option('--dbt', dest='dbpath', type='str', default=None,
            help='Test if provided bundle already exists in database',
            metavar='BundlePath', nargs=1)

    (options_args, args) = parser.parse_args()

    #
    # check options are mutually exclusive
    #
    msg = "\n\t*** Options are mutually exclusive ***\n"
    if options_args.bpath and (options_args.rbpath or options_args.daemon):
        usage(parser, msg)
    if options_args.rbpath and (options_args.bpath or options_args.daemon):
        usage(parser, msg)
    if options_args.daemon and (options_args.bpath or options_args.rbpath):
        usage(parser, msg)

    #
    # Perform action for option specified
    #
    cc = 'cli'
    db_enable = options_args.db_enable
    if options_args.bpath is not None:
        bdlpath = options_args.bpath
        Ingest(options_args.bpath, cc)      # --ingest

    elif options_args.rbpath is not None:
        bdlpath = options_args.rbpath
        Reingest(options_args.rbpath, cc)   # --reingest

    elif options_args.pbpath is not None:
        bdlpath = options_args.pbpath
        Peek(options_args.pbpath, cc)       # --peek

    elif OS == 'Linux' and db_enable and options_args.dbpath is not None:
        bdlpath = options_args.dbpath
        DBPeek(options_args.dbpath, cc)     # --dbt

    elif options_args.daemon:
        if args:
            msg = "\n\t*** --service option takes no arguments ***\n"
            usage(parser, msg)
        start_svc()                         # --service
    else:
        parser.print_help()
        sys.exit(1)

    return


def plat_info():
    os = platform.system()
    pyv = platform.python_version()

    arch = platform.machine()
    if os == 'Linux':
        dist, ver, nick = platform.linux_distribution()
    elif os == 'SunOS':
        rel = platform.release()
        ptv = platform.version()
    elif os == 'Darwin':
        ver, foo, bar = platform.mac_ver()

    return os, pyv


#
# main()
#
def main():
    global program
    global OS
    global DB
    
    OS, PyV = plat_info()
    if OS == 'Linux':
        import MySQLdb as DB

    program = os.path.basename(sys.argv[0])
    process_args()
    return


def chk_env():
    global scrpdir;

    try:
        scrpdir = os.path.join(os.environ['NXTA_INGESTOR'], 'ingestion-scripts')
    except KeyError:
        print "NXTA_INGESTOR var MUST be set !"
        sys.exit(1)
    return


# Boilerplate
if __name__ == '__main__':
    chk_env()
    main()


# pydoc related
__author__ = "Rick Mesta"
__copyright__ = "Copyright 2014 Nexenta Systems, Inc. All rights reserved."
__credits__ = ["Rick Mesta"]
__license__ = "undefined"
__version__ = "$Revision: " + ing_ver + " $"
__created_date__ = "$Date: 2014-05-14 13:00:00 +0600 (Wed, 14 May 2014) $"
__last_updated__ = "$Date: 2016-11-10 15:44:00 +0600 (Thu, 10 Nov 2016) $"
__maintainer__ = "Rick Mesta"
__email__ = "rick.mesta@nexenta.com"
__status__ = "Experimental"
