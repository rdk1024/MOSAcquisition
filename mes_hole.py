#!/usr/bin/env python

import ginga.main

import sys
args = sys.argv

ginga.main.reference_viewer(['$HOME/Install/bin/ginga',
                             args[1],
                             '--plugins=MESLocate'])
