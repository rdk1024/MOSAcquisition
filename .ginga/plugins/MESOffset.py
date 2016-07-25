#
# MESOffset.py -- a ginga plugin designed to help locate a group of objects.
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import math
import sys

# local imports
from util import mosPlugin
from util.mesAnalyze import MESAnalyze
from util.mesInterface import MESInterface
from util.mesLocate import MESLocate

# ginga imports
from ginga.gw import Widgets, Viewers

# third-party imports
import numpy as np
from numpy import ma



class MESOffset(mosPlugin.MESPlugin):
    """
    A custom LocalPlugin for ginga that takes parameters from the user in a
    user-friendly menu, locates a set of calibration objects, asks for users to
    help locate anomolies and artifacts on its images of those objects,
    calculates their centers of masses, graphs some data about some objects'
    positions, and asks the user to modify the data if necessary. Intended for
    use as part of the MOS Acquisition software for aligning MOIRCS.
    """
    
    def __init__(self, fv, fitsimage):
        """
        Class constructor
        @param fv:
            A reference to the ginga.main.GingaShell object (reference viewer)
        @param fitsimage:
            A reference to the specific ginga.qtw.ImageViewCanvas object
            associated with the channel on which the plugin is being invoked
        """
        super(MESOffset, self).__init__(fv, fitsimage)
        
        # these three classes are the three departments of MESOffset;
        # each one handles a different set of tasks, and this class manages them
        self.mes_interface = MESInterface(self)
        self.mes_locate = MESLocate(self)
        self.mes_analyze = MESAnalyze(self)
        
        self.globals = {}   # the variables shared between the departments
        
        self.stack_idx = {} # the indices of the guis in the stack
        
        
        
    def initialise(self, department):
        """
        Assign all of self's important instance variables to this department
        @param department:
            An object of some kind that wants my variables
        """
        department.fv        = self.fv
        department.fitsimage = self.fitsimage
        department.logger    = self.logger
        department.canvas    = self.canvas
        department.dc        = self.dc
        department.manager   = self
    
    
    def stack_guis(self, stack, orientation='vertical'):
        """
        Get the GUIs from all the different departments of mesoffset, and stacks
        them together neatly in one gw.Widget
        """
        all_guis = (self.mes_interface.gui_list(orientation) +
                    self.mes_locate.gui_list(orientation) +
                    self.mes_analyze.gui_list(orientation))
        for i, (name, gui) in enumerate(all_guis):
            stack.add_widget(gui)
            self.stack_idx[name] = i
    
    
    def go_to_gui(self, gui_name):
        """
        Set the stack to look at the specified GUI
        @param gui_name
            The name of the GUI, which should be a key in stack_idx
        """
        self.stack.set_index(self.stack_idx[gui_name])
    
    
    ### ----- MESOFFSET1 FUNCTIONS ----- ###
    def begin_mesoffset1(self):
        """
        Start the first, rough, star/hole location, based on the raw data and
        the SBR input file. The first step is opening the FITS image
        """
        self.__dict__.update(self.globals)
        
        starg10_filename = self.rootname+"_star.fits"    # TODO: does it have to be "starg10"?
        self.open_fits(starg10_filename, next_step=self.mes_star_cb)
    
    
    def mes_star_cb(self, *args):
        """
        Call MESLocate in star mode on the current image
        """
        sbr_data = self.mes_locate.read_sbr_file(self.rootname+".sbr")
        self.mes_locate.start(sbr_data, 'star', True,
                              next_step=self.end_mesoffset1)
    
    
    def end_mesoffset1(self):
        """
        Finish off the first, rough, star/hole location
        """
        self.mes_interface.log("Done with MESOffset1!")
        self.canvas.delete_all_objects()    # TODO: does this canvas get reused, or replaced?
        self.fitsimage.center_image()
        self.fitsimage.zoom_fit()
        self.go_to_gui('epar 2')
    
    
    ### ----- MESOFFSET2 FUNCTIONS ----- ###
    def begin_mesoffset2(self):
        print "MESOffset2!"
    
    
    ### ----- MESOFFSET3 FUNCTIONS ----- ###
    def begin_mesoffset3(self):
        print "MESOffset1!"
    
    
    def open_fits(self, filename, next_step=None):
        """
        Open a FITS image and display it in ginga, then call a function
        @param filename:
            The name of the fits file
        @param next_step:
            The function to call once the image has been loaded
        """
        if next_step != None:
            self.fitsimage.add_callback('image-set', next_step)
        self.fitsimage.make_callback('drag-drop', [filename])

#END

