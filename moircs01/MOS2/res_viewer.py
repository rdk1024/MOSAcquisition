#!/usr/bin/env python

#
# resviewer.py -- a script that starts Ginga with the MESAnalyze plugin running
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#

import ginga.main

import sys
argv = sys.argv

if len(argv) != 2:
    print("usage: res_viewer( input_file_name )")
    quit()

ginga.main.reference_viewer(['$HOME/Install/bin/ginga',
                             argv[1],
                             '--plugins=MESAnalyze'])

#END

