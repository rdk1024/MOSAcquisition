#
# MESOffset.py -- a ginga plugin to align MOIRCS for Subaru Telescope
#
# Justin Kunimune
#



# local imports
from util import fitsUtils
from util import mosPlugin
from util.mesAnalyze import MESAnalyze
from util.mesInterface import MESInterface
from util.mesLocate import MESLocate



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
        
        self.database = {}   # the variables shared between the departments
        
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
    def begin_mesoffset1(self): # TODO: check for errors opening FITS in ginga, running iraf stuff, finding img_dir/c_file
        """
        Start the first, rough, star/hole location, based on the raw data and
        the SBR input file. The first step is processing the star frames
        """
        self.__dict__.update(self.database)
        self.mes_interface.log("Starting MES Offset 1...")
        self.process_star_fits()
    
    def process_star_fits(self, *args):
        """ Use fitsUtils to combine raw data into a usable star mosaic """
        # if reuse is on, don't bother with any of this
        if self.reuse1:
            self.load_processed_star()
            return
        
        self.go_to_gui('log')
        self.fv.nongui_do(lambda:
                fitsUtils.process_star_fits(self.star_chip1, self.sky_chip1,
                                            self.c_file, self.img_dir,
                                            self.rootname+"_star.fits",
                                            log=self.mes_interface.log,
                                            next_step=self.load_processed_star)
                          )
    
    def load_processed_star(self, *args):
        """ Load the star frame FITS image that was processed by fitsUtils """
        star_filename = self.rootname+"_star.fits"
        self.open_fits(star_filename, next_step=self.mes_star)
    
    def mes_star(self, *args):  # TODO: display values and give a chance to redo
        """ Call MESLocate in star mode on the current image """
        self.sbr_data = self.mes_locate.read_sbr_file(self.rootname+".sbr")
        self.mes_locate.start(self.sbr_data, 'star', True, self.interact1,
                              next_step=self.wait_for_masks)
    
    def wait_for_masks(self, *args):
        """ Save data from mes_locate and wait for user input """    # TODO: use an epar for this
        self.star_locations = self.mes_locate.output_data[:,:2]
        self.go_to_gui('wait')
        self.mes_interface.wait("Are the mask images ready for analysis?\n"+
                                "Click 'Go!' when\n"+
                                "MCSA{:08d}.fits and\nMCSA{:08d}.fits ".format(
                                        self.star_chip1+4, self.star_chip1+5)+
                                "are in {} and ready.".format(self.img_dir),
                                next_step=self.process_mask_fits)
    
    def process_mask_fits(self, *args):
        """ Use fitsUtils to comine raw data into a usable mask mosaic """
        if self.reuse2:
            self.load_processed_mask()
            return
        
        self.go_to_gui('log')
        self.fv.nongui_do(lambda:
                fitsUtils.process_mask_fits(self.star_chip1+4,
                                            self.c_file, self.img_dir,
                                            self.rootname+"_mask.fits",
                                            log=self.mes_interface.log,
                                            next_step=self.load_processed_mask)
                          )
    
    def load_processed_mask(self, *args):
        """ Load the mask frame FITS image that was processed by fitsUtils """
        mask_filename = self.rootname+"_mask.fits"
        self.open_fits(mask_filename, next_step=self.mes_hole)
    
    def mes_hole(self, *args):
        """ Call MESLocate in mask mode on the current image """
        self.mes_locate.start(self.sbr_data, 'mask', True, self.interact2,
                              next_step=self.analyze_1)
    
    def analyze_1(self, *args):
        """ Call MESAnalyze on the data from mes_star and mes_hole """
        self.hole_locations = self.mes_locate.output_data
        self.mes_analyze.start(self.star_locations, self.hole_locations,
                               next_step=self.end_mesoffset1)
    
    def end_mesoffset1(self, *args):
        """ Finish off the first, rough, star/hole location """
        self.mes_interface.log("Done with MES Offset 1!")    # TODO: does the canvas get deleted or replaced?
        self.mes_interface.write_to_logfile(self.rootname+"_log",
                                            "MES Offset 1",
                                            self.mes_analyze.offset)
        self.database['starhole_chip1'] = self.star_chip1+6
        self.database['sky_chip1'] = self.sky_chip1+2
        self.mes_interface.set_defaults(2)
        self.go_to_gui('epar 2')
    
    
    ### ----- MESOFFSET2 FUNCTIONS ----- ###
    def begin_mesoffset2(self):
        """
        Start the second, star-hole location, based on the raw data. The first
        step is processing the starhole frames
        """
        self.__dict__.update(self.database)
        self.mes_interface.log("Starting MES Offset 2...")
        self.process_starh_fits()
    
    
    def process_starh_fits(self, *args):
        """ Use fitsUtils to combine raw data into a compound starhole image """
        if self.reuse3:
            self.load_processed_starh()
            return
        
        self.go_to_gui('log')
        self.fv.nongui_do(lambda:
                fitsUtils.process_star_fits(self.starhole_chip1, self.sky_chip1,
                                            self.c_file, self.img_dir,
                                            self.rootname+"_starhole.fits",
                                            log=self.mes_interface.log,
                                            next_step=self.load_processed_starh)
                          )
    
    def load_processed_starh(self, *args):
        """ Load the finished starhole image into ginga """
        starhole_filename = self.rootname+"_starhole.fits"
        self.open_fits(starhole_filename, next_step=self.mes_starhole)
    
    def mes_starhole(self, *args):
        """ Call MESLocate in starhole mode on the current image """
        self.mes_locate.start(self.hole_locations, 'starhole',
                              False, self.interact3,
                              next_step=self.analyze_2)
    
    def analyze_2(self, *args):
        """ Call MESAnalyze on the data from mes_star and mes_starhole """
        self.star_locations = self.mes_locate.output_data
        self.mes_analyze.start(self.star_locations, self.hole_locations,
                               next_step=self.end_mesoffset2)
    
    def end_mesoffset2(self, *args):
        """ Finish off the second star-hole location """
        self.mes_interface.log("Done with MES Offset 2!")
        self.mes_interface.write_to_logfile(self.rootname+"_log",
                                            "MES Offset 2",
                                            self.mes_analyze.offset)
        self.mes_interface.set_defaults(3)
        self.go_to_gui('epar 3')
    
    
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
        print filename
        self.fitsimage.clear_callback('image-set')  #TODO: can I do this while preserving the built-in callbacks?
        if next_step != None:
            self.fitsimage.add_callback('image-set', next_step)
        self.fitsimage.make_callback('drag-drop', [filename])

#END

