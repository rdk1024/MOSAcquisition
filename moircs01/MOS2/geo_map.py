#!/usr/bin/env python

#
# geo_map.py -- a script that starts Ginga with the MESAnalyze plugin running
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#

import ginga.main

import sys
argv = sys.argv

if len(argv) < 5:
    print("usage: mes_plot( FITS_image_name, input_coo_filename, "+
                           "output_dbs_filename, log_filename[, output_res] )")
    quit()

ginga.main.reference_viewer(['$HOME/Install/bin/ginga',
                             argv[1],
                             '--plugins=MESAnalyze'])

#END

