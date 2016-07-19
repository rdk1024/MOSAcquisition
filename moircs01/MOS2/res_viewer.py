#!/usr/bin/env python

#
# resviewer.py -- a script that starts Ginga with the MESResults plugin running
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#

import ginga.main

import sys
argv = sys.argv

if len(argv) < 3:
    print("usage: res_viewer( FITS_image_name, input_file_name )")
    quit()

ginga.main.reference_viewer(['$HOME/Install/bin/ginga',
                             argv[1],
                             '--plugins=MESResults'])

#END

