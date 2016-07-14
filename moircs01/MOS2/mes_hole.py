#!/usr/bin/env python

#
# mes_hole.py -- script that starts Ginga with the MESLocate plugin running
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#

import ginga.main

import sys
argv = sys.argv

if len(argv) != 5:
    print("usage: mes_hole(FITS_image_name, hole_pos_list, outputfile, interact?")
    quit()

ginga.main.reference_viewer(['$HOME/Install/bin/ginga',
                             argv[1],
                             '--plugins=MESLocate'])

#END

