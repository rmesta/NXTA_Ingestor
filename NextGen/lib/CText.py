#!/usr/bin/env python
#
# Rick Mesta
# Colored text
#
import sys
from pprint import pprint
import os

ctext_ver = '1.0.0'

class Colors:
    def __init__(self):
        self.lite_gray =    '\033[0;90m'
        self.bold_gray =    '\033[1;90m'
        self.lite_red =     '\033[0;91m'
        self.bold_red =     '\033[1;91m'
        self.lite_green =   '\033[0;92m'
        self.bold_green =   '\033[1;92m'
        self.lite_yellow =  '\033[0;93m'
        self.bold_yellow =  '\033[1;93m'
        self.lite_blue =    '\033[0;94m'
        self.bold_blue =    '\033[1;94m'
        self.lite_purple =  '\033[0;95m'
        self.bold_purple =  '\033[1;95m'
        self.lite_cyan =    '\033[0;96m'
        self.bold_cyan =    '\033[1;96m'
        self.lite_white =   '\033[0;97m'
        self.bold_white =   '\033[1;97m'
        self.normal =       '\033[0m'
        self.debug = self.lite_yellow
        self.warn = self.bold_yellow
        self.fail = self.bold_red
        self.okay = self.bold_green
        self.reset = self.normal
        self.clear = self.normal

    def lcolor(self, color, msg, nl):
        es = eval('self.lite_%s' % str(color))
        if nl:
            print es + msg + self.reset
        else:
            print es + msg + self.reset,

    def lcfmt(self, color, msg, fmt, nl):
        es = eval('self.lite_%s' % str(color))
        if nl:
            print es + fmt % msg + self.reset
        else:
            print es + fmt % msg + self.reset,

    def bcolor(self, color, msg, nl):
        es = eval('self.bold_%s' % str(color))
        if nl:
            print es + msg + self.reset
        else:
            print es + msg + self.reset,

    def bcfmt(self, color, msg, fmt, nl):
        es = eval('self.bold_%s' % str(color))
        if nl:
            print es + fmt % msg + self.reset
        else:
            print es + fmt % msg + self.reset,

    def bcmplx(self, color, cds, nl):
        es = eval('self.bold_%s' % str(color))
        print es,
        pprint(cds)
        if nl:
            print self.reset
        else:
            print self.reset,

    def reset(self):
        sys.stdout.write(self.reset)


class CText(Colors):
    def __init__(self):
        Colors.__init__(self)

    def lite(self, color, msg, nl):
        Colors.lcolor(self, color, msg, nl)

    def lite_fmt(self, color, msg, fmt, nl):
        Colors.lcfmt(self, color, msg, fmt, nl)

    def bold(self, color, msg, nl):
        Colors.bcolor(self, color, msg, nl)

    def bold_fmt(self, color, msg, fmt, nl):
        Colors.bcfmt(self, color, msg, fmt, nl)

    def bold_cmplx(self, color, cds, nl):
        Colors.bcmplx(self, color, cds, nl)

    def c_reset(self):
        Colors.reset(self)


def print_reset():
    text = CText()
    text.c_reset()


def print_lite(msg, color, nl):
    text = CText()
    text.lite(color, msg, nl)


def prfmt_lite(msg, fmt, color, nl):
    text = CText()
    text.lite_fmt(color, msg, fmt, nl)


def print_bold(msg, color, nl):
    text = CText()
    text.bold(color, msg, nl)


def prfmt_bold(msg, fmt, color, nl):
    text = CText()
    text.bold_fmt(color, msg, fmt, nl)


def print_bcmplx(cds, color, nl):
    text = CText()
    text.bold_cmplx(color, cds, nl)


def print_debug(msg, nl):
    text = CText()
    text.lite('yellow', msg, nl)


def print_warn(msg, nl):
    text = CText()
    text.bold('yellow', msg, nl)


def prfmt_warn(msg, fmt):
    prfmt_bold(msg, fmt, 'yellow', True)


def print_pass(msg):
    text = CText()
    text.bold('green', msg, True)


def prfmt_pass(msg, fmt):
    prfmt_bold(msg, fmt, 'green', True)


def print_fail(msg):
    text = CText()
    text.bold('red', msg, True)


def prfmt_fail(msg, fmt):
    prfmt_bold(msg, fmt, 'red', True)


def prfmt_mc_row(msg, fmt, cset, typ):
    ma = msg.split(',')
    fa = fmt.split(',')
    ca = cset.split(',')
    ta = typ.split(',')

    for m in ma:
        f = fa[ma.index(m)]
        c = ca[ma.index(m)]
        t = ta[ma.index(m)].strip()
        if t == 'bold':
            prfmt_bold(m.strip(), f.strip(), c.strip(), False)
        elif t == 'lite':
            prfmt_lite(m.strip(), f.strip(), c.strip(), False)
    print ''


def print_header(msg):
    l = len(msg)
    n = 65 - l
    print ''
    print_bold(3 * '=', 'white', False)
    print_bold(msg, 'blue', False)
    print_bold(n * '=', 'white', True)
    print ''


def main():
    print_lite('hello... ', 'white', False)
    print_bold('hello again', 'white', True)

    print_lite('Simple Oops', 'red', True)

    print_warn('Warning', True)
    print_fail('Failure')
    print_pass('Passed')
    print_header('some header')

    f = 'print_header'
    globals()[f]('header 2')

    print_lite('light blue', 'blue', False)
    print_bold('bold blue', 'blue', True)
    print_lite('light cyan', 'cyan', False)
    print_bold('bold cyan', 'cyan', True)

    prfmt_pass('Pass', '%15s')
    prfmt_pass('Pass', '%14s')

    prfmt_bold('formatted blue', '%20s', 'blue', False)
    prfmt_lite('formatted red', '%25s', 'red', True)
    prfmt_bold('formatted fail', '%30s', 'red', True)
    prfmt_warn('formatted WARN', '%40s')

    prfmt_mc_row('cell1, cell2, cell3, cell4',
                '  %20s,  %10s,  %10s,  %20s',
                '   red, white, yellow, blue',
                '  lite,  bold,  lite,  bold')

    bpurple =  '\033[1;95m'
    print bpurple + 'this is purple text'
    print 'text with no color specified'
    print_reset()
    print_bold('more output after reset', 'cyan', True)

    print_debug('\nthis is some debug output\n', True)

    cds = os.stat('.')
    print_bcmplx(cds, 'gray', True)


# Boilerplate
if __name__ == '__main__':
    main()


# pydoc related
__author__ = "Rick Mesta"
__copyright__ = "Copyright 2015 Nexenta Systems, Inc. All rights reserved."
__credits__ = ["Rick Mesta"]
__license__ = "undefined"
__version__ = "$Revision: " + ctext_ver + " $"
__created_date__ = "$Date: 2015-07-16 22:00:00 +0600 (Thr, 16 Jul 2015) $"
__last_updated__ = "$Date: 2015-08-11 12:57:00 +0600 (Tue, 11 Aug 2015) $"
__maintainer__ = "Rick Mesta"
__email__ = "rick.mesta@nexenta.com"
__status__ = "Experimental"
