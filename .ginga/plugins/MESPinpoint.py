#
# MESPinpoint.py -- a ginga plugin designed to help pinpoint a group of objects.
# Similar to MESLocate.py, but with more precision and no step 1
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import math
import sys

# local imports
from MESLocate import MESLocate

# ginga imports
from ginga import GingaPlugin
from ginga.gw import Widgets, Viewers, Plot

# third-party imports
import numpy as np



# constants
# the arguments passed in to the outer script
argv = sys.argv
fits_image = argv[1]
input_coo = argv[2]
output_coo = argv[3]    #TODO: What do I have to output?
interact = argv[4]

# the object we are looking for
#mode = 'star' if 'star' in argv[1] else 'hole'
# the size of the object-finding squares (dependent on whether we look for holes or stars)
sq_size = 50
# the difference between the threshold and the mean, in standard deviations
#threshold_dist = 3 if mode == 'star' else -.2
# the colors of said squares
#colors = ('green','red','blue','yellow','magenta','cyan','orange')
# the different ways we can select things
selection_modes = ("Automatic", "Crop", "Mask")



class MESPinpoint(MESLocate):
    """
    A custom LocalPlugin for ginga that locates a set of calibration objects,
    asks for users to help locate anomolies and artifacts on its images
    of those objects, and then calculates their centers of masses. Intended
    for use as part of the MOS Acquisition software for aligning MOIRCS.
    """
    
    
    
    def start(self):
        """
        Called when the plugin is invoked, right after build_gui()
        One of the required LocalPlugin methods
        """
        MESLocate.start(self)
        self.step2_cb()
    
    
    def __str__(self):
        return "MESPinpoint"
    
    
    
    @staticmethod
    def readInputFile():
        """
        Reads the COO file and returns the position of the first active
        object as well as the relative positions of all the other objects in a list
        @returns:
            A tuple containing a list of float tuples representing relative
            locations and radii of objects, and a single float tuple (absolute
            location of first object)
        """
        # define variables
        obj_list = []
        obj0 = None
        
        # try to open the file
        try:
            coo = open(input_coo, 'r')
        except IOError:
            try:
                coo = open("sbr_elaisn1rev_mask.coo")
            except IOError:
                return [(dx, dy) for dx in [0,1,-1] for dy in [0,1,-1]], (0,0)
        
        # now parse it!
        line = coo.readline()
        while line != "":
            # for each line, get the important values and save them in obj_list
            vals = [float(word) for word in line.split(",")]
            if obj0 == None:
                obj_list.append((0, 0))
                obj0 = (vals[0], vals[1])
            else:
                obj_list.append((vals[0]-obj0[0],   # don't forget to shift it so object #0 is at the origin
                                 vals[1]-obj0[1],
                                 vals[2]))
            line = coo.readline()
            
        return obj_list, obj0
    
    
    @staticmethod
    def locate_obj(bounds, masks, image):
        """
        Finds the center of an object using center of mass calculation
        @param bounds:
            A tuple of floats x1, y1, x2, y2. The object should be within this box
        @param masks:
            A list of tuples of the form (x1, y1, x2, y2, kind) where kind is either
            'mask' or 'crop' and everything else is floats. Each tuple in masks
            is one drag of the mouse that ommitted either its interior or its
            exterior
        @param image:
            The AstroImage containing the data necessary for this calculation
        @returns:
            A tuple of two floats representing the actual location of the object
        @raises ZeroDivisionError:
            If no object is visible in the frame
        """
        # start by cropping the image to get the data matrix
        data, x0,y0 = image.cutout_adjust(*bounds)[0:3]
        
        # omit data based on masks
        mask_tot = np.ones(data.shape)
        for drag in masks:
            x1, y1, x2, y2, kind = (int(drag[0]-bounds[0]), int(drag[1]-bounds[1]),
                                    int(drag[2]-bounds[0]), int(drag[3]-bounds[1]),
                                    drag[4])
            mask = np.ones(data.shape)
            mask[y1:y2, x1:x2] = np.zeros((y2-y1, x2-x1))
            if kind == 'crop':
                mask = 1-mask
            mask_tot = mask_tot*mask
        
        # apply mask, calculate threshold, coerce data positive, and reapply mask
        data = data * mask_tot
        threshold = 3*np.std(data) + np.mean(data)
        data = data - threshold
        data = np.clip(data, 0, float('inf'))
        data = data * mask_tot
        
        # now do a center-of mass calculation to find the size and centroid
        yx = np.indices(data.shape)
        x, y = yx[1], yx[0]
        x_sum = float(np.sum(data*x))
        y_sum = float(np.sum(data*y))
        data_sum = float(np.sum(data))
        area = float(np.sum(np.sign(data)))
        
        x_cen = x_sum/data_sum
        y_cen = y_sum/data_sum
        radius = math.sqrt(area/math.pi)
        print "I'm different..."
        return (x0 + x_cen - 0.5, y0 + y_cen - 0.5, radius)

#END

