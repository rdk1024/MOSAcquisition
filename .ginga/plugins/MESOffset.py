#
# MESOffset.py -- a ginga plugin to align MOIRCS for Subaru Telescope
#
# Justin Kunimune
#



# standard imports
import math
import sys

# local imports
from util import fitsUtils
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
        the SBR input file. The first step is processing the star frames
        """
        self.__dict__.update(self.globals)
        self.mes_interface.log("Starting MES Offset1...")
        self.process_star_frames()
    
    def process_star_frames(self, *args):
        """ Use fitsUtils to combine raw data into a usable star mosaic """
        self.go_to_gui('log')
        self.fv.nongui_do(lambda:
                fitsUtils.process_star_frames(self.star_chip1, self.sky_chip1,
                                              self.rootname, self.c_file,
                                              self.img_dir, self.retry1,
                                              log=self.mes_interface.log,
                                              next_step=self.load_processed_star
                                              )
                          )
    
    def load_processed_star(self, *args):
        """ Load the star frame FITS image that was processed by fitsUtils """
        star_filename = self.rootname+"_starg10.fits"   # TODO: let's change this to something more descriptive once this works
        self.open_fits(star_filename, next_step=self.mes_star)
    
    def mes_star(self, *args):
        """ Call MESLocate in star mode on the current image """
        sbr_data = self.mes_locate.read_sbr_file(self.rootname+".sbr")
        self.mes_locate.start(sbr_data, 'star', self.globals['inter1'],
                              next_step=self.wait_for_masks)
    
    def wait_for_masks(self, *args):
        """ Wait for the user to add mask images """
        self.go_to_gui('wait')
        self.mes_interface.wait("Are the mask images ready for analysis?\n"+
                                "Click 'Go!' when\n"+
                                "MCSA{:08d}.fits and\nMCSA{:08d}.fits ".format(
                                        self.star_chip1+4, self.star_chip1+5)+
                                "are in {} and ready.".format(self.img_dir),
                                next_step=self.process_mask_frames)
    
    def process_mask_frames(self, *args):
        """ Use fitsUtils to comine raw data into a usable mask mosaic """
        self.go_to_gui('log')
        self.fv.nongui_do(lambda:   #FIXME: this method has not yet been written
                fitsUtils.process_mask_frames(
                                              log=self.mes_interface.log,
                                              next_step=self.load_processed_mask
                                              )
                          )
    
    def load_processed_mask(self, *args):
        """ Load the mask frame FITS image that was processed by fitsUtils """
        mask_filename = self.rootname+"_mask.fits"
        self.open_fits(mask_filename, next_step=self.mes_hole)
    
    def mes_hole(self, *args):
        """ Call MESLocate in mask mode on the current image """
        self.mes_locate.start(None, 'mask', self.globals['inter2'],
                              next_step=self.analyze_1)
    
    def analyze_1(self, *args):
        """ Call MESAnalyze on the data from mes_star and mes_hole """
        self.mes_analyze.start(next_step=self.end_mesoffset1)
    
    def end_mesoffset1(self, *args):
        """ Finish off the first, rough, star/hole location """
        self.mes_interface.log("Done with MES Offset1!")
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

