#!/usr/bin/env python

import ginga.main


args = ['/home/justinku/moircs01/MOS/mes_star',
        'sbr_elaisn1rev_starg10.fits',
        'sbr_elaisn1rev.sbr',
        'sbr_elaisn1rev_star.coo',
        'yes']

ginga.main.reference_viewer(['$HOME/Install/bin/ginga',
                             args[1],
                             '--plugins=MESOffset1'])
