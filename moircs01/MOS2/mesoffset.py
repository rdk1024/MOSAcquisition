#!/usr/bin/env python

#
# mesoffset.py -- a Python script that helps align Subaru Telescope for MOIRCS
# Acquisition. It opens several plugins in sequence and ends up (somehow)
# exporting values to ANA, whatever that is. I'm working on it.
#
# Justin Kunimune
#

import ginga.main

import sys
argv = sys.argv

if len(argv) != 5:
    print("usage: mesoffset.py")
    quit()

ginga.main.reference_viewer(['$HOME/Install/bin/ginga',
                             argv[1],
                             '--plugins=MESInterface,MESLocate,MESAnalyze,MESPinpoint'])

#END

