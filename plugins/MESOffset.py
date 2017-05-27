#
# MESOffset.py -- a ginga plugin to align MOIRCS for Subaru Telescope
#
# Justin Kunimune
#



# standard imports
from __future__ import absolute_import
import os
import threading

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
    
    # main menu parameters
    PARAMS_0 = [
        {'name':'star_chip1',
         'label':"Star Frame", 'type':int, 'format':"MCSA{}.fits", 'default':0,
         'desc':"The frame number for the chip1 star FITS image"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':str, 'format':"{}.sbr", 'default':'',
         'desc':"The filename of the mask definition SBR file"},
        
        {'name':'c_file',
         'label':"Config File", 'type':str, 'default':"$DATABASE/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':str, 'default':"$DATA/",
         'desc':"The directory in which the input FITS images can be found"},
        
        {'name':'exec_mode',
         'label':"Execution Mode", 'type':int, 'options':["Normal","Fine"],
         'desc':"Choose 'Fine' to skip MES Offset 1"}
    ]
    
    # mesoffset1 parameters
    PARAMS_1 = [
        {'name':'star_chip1',
         'label':"Star Frame", 'type':int, 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 star FITS image"},
        
        {'name':'sky_chip1',
         'label':"Sky Frame", 'type':int, 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 sky FITS image"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':str, 'format':"{}.sbr",
         'desc':"The filename of the mask definition SBR file"},
        
        {'name':'c_file',
         'label':"Config File", 'type':str, 'default':"$DATABASE/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':str, 'default':"$DATA/",
         'desc':"The directory in which the raw FITS images can be found"},
        
        {'name':'recalc1',
         'label':"Regenerate Star", 'type':bool,
         'desc':"Do you want to generate new composite star images?"},
        
        {'name':'interact1',
         'label':"Interact Star", 'type':bool,
         'desc':"Do you want to interact with star position measurement?"}
    ]
    
    # mesoffset1.5 parameters
    PARAMS_1p5 = [
        {'name':'mask_chip1',
         'label':"Mask Frame", 'type':int, 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 mask FITS image"},
        
        {'name':'recalc2',
         'label':"Regenerate", 'type':bool,
         'desc':"Do you want to generate new composite mask images?"},
        
        {'name':'interact2',
         'label':"Interact", 'type':bool,
         'desc':"Do you want to interact with hole position measurement?"}
    ]
    
    # mesoffset2 parameters
    PARAMS_2 = [
        {'name':'starhole_chip1',
         'label':"Star-Hole Frame", 'type':int, 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 star-hole FITS image"},
        
        {'name':'mask_chip1',
         'label':"Mask Frame", 'type':int, 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 mask FITS image"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':str, 'format':"{}.sbr",
         'desc':"The filename of the mask definition SBR file"},
        
        {'name':'c_file',
         'label':"Config File", 'type':str, 'default':"$DATABASE/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':str, 'default':"$DATA/",
         'desc':"The directory in which the raw FITS images can be found"},
        
        {'name':'recalc3',
         'label':"Regenerate", 'type':bool,
         'desc':"Do you want to generate new composite star-hole images?"},
        
        {'name':'interact3',
         'label':"Interact", 'type':bool,
         'desc':"Do you want to interact with star position measurement?"}
    ]
    
    # mesoffset3 parameters
    PARAMS_3 = [
        {'name':'mask_chip1',
         'label':"Mask Frame", 'type':int, 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 mask FITS image"},
        
        {'name':'sky_chip1',
         'label':"Sky Frame", 'type':int, 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 sky FITS image"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':str, 'format':"{}.sbr",
         'desc':"The filename of the mask definition SBR file"},
        
        {'name':'c_file',
         'label':"Config File", 'type':str, 'default':"$DATABASE/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':str, 'default':"$DATA/",
         'desc':"The directory in which the raw FITS images can be found"},
        
        {'name':'recalc4',
         'label':"Regenerate Mask", 'type':bool,
         'desc':"Do you want to generate new composite mask images?"},
        
        {'name':'interact4',
         'label':"Interact Mask", 'type':bool,
         'desc':"Do you want to interact with hole position measurement?"}
    ]
    
    # mesoffset3.5 parameters
    PARAMS_3p5 = [
        {'name':'starhole_chip1',
         'label':"Star-Hole Frame", 'type':int, 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 star-hole FITS image"},
        
        {'name':'recalc5',
         'label':"Regenerate", 'type':bool,
         'desc':"Do you want to generate new composite star-hole images?"},
        
        {'name':'interact5',
         'label':"Interact", 'type':bool,
         'desc':"Do you want to interact with star position measurement?"}
    ]
    
    
    
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
        
        # the function to run when an image is loaded
        self.image_set_next_step = None
        self.fitsimage.add_callback('image-set', self.image_set_cb)
        
        self.training_dir = None
        self.rootname_logfile = None
        
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
    
    def set_params(self, star_chip1, rootname, c_file, img_dir, exec_mode,
                   mcsred_dir, training_dir, work_dir, wait_gui):

        self.PARAMS_0[0]['default'] = int(star_chip1)
        self.PARAMS_0[1]['default'] = rootname
        self.PARAMS_0[2]['default'] = '$' + c_file
        self.PARAMS_0[3]['default'] = img_dir
        try:
            exec_option = self.PARAMS_0[4]['options'].index(exec_mode.capitalize())
        except ValueError:
            exec_option = 0
        self.PARAMS_0[4]['default'] = exec_option
        self.mes_interface.set_params(mcsred_dir)
        self.training_dir = training_dir
        fitsUtils.DIR_MCSRED = mcsred_dir + '/'
        self.work_dir = os.path.join(work_dir, 'MESOffset')
        self.logger.info('work_dir is %s' % self.work_dir)
        if os.path.isdir(self.work_dir):
            self.logger.info('work_dir %s exists' % self.work_dir)
        else:
            self.logger.info('creating %s' % self.work_dir)
            os.makedirs(self.work_dir)
        self.rootname_logfile = os.path.join(self.work_dir, rootname+"_log")
        self.wait_gui = wait_gui
        self.logger.info('wait_gui input value %s self.wait_gui %s' % (wait_gui, self.wait_gui))
        self.logger.info('after PARAMS_0 %s' % self.PARAMS_0)

    
    def stack_guis(self, stack, orientation='vertical'):
        """
        Get the GUIs from all the different departments of mesoffset, and stacks
        them together neatly in one gw.Widget
        """
        stack.remove_all()
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
    
    
    ### ----- MESOFFSET0 FUNCTION ----- ###
    def execute_mesoffset0(self):
        """ Set some stuff up to run mesoffset 1, 2, and 3 continuously """
        # start by using these values to guess at some other values
        self.__dict__.update(self.database)
        self.database['sky_chip1'] = self.star_chip1 + 2
        self.database['mask_chip1'] = self.star_chip1 + 4
        self.database['starhole_chip1'] = self.star_chip1 + 6
        if len(self.img_dir) <= 0 or self.img_dir[-1] != '/':
            self.database['img_dir'] += '/'
        
        # set the defaults for all other menus
        for i in (1, 2, 3):
            self.mes_interface.set_defaults(i)
        
        # next step depends on exec_mode
        if self.exec_mode == 0:
            self.mes_interface.go_to_mesoffset(1)
        else:
            self.mes_interface.go_to_mesoffset(3)
    
    
    ### ----- MESOFFSET1 FUNCTIONS ----- ###
    def begin_mesoffset1(self):
        """
        Start the first, rough, star/hole location, based on the raw data and
        the SBR input file. The first step is processing the star frames
        """
        # modify the database if necessary, and then absorb all values from the database
        img_dir = self.database['img_dir']
        if len(img_dir) <= 0 or img_dir[-1] != '/':
            self.database['img_dir'] += '/'
        self.__dict__.update(self.database)
        
        self.process_star_fits()
    
    def process_star_fits(self, *args):
        """ Use fitsUtils to combine raw data into a usable star mosaic """
        self.process_fits('star', self.recalc1,
                          next_step=self.load_processed_star)
    
    def load_processed_star(self, *args):
        """ Load the star frame FITS image that was processed by fitsUtils """
        self.open_fits(filename=self.rootname+"_star.fits",
                       next_step=self.mes_star)
    
    def mes_star(self, *args):
        """ Call MESLocate in star mode on the current image """
        self.sbr_data = self.mes_locate.read_sbr_file(os.path.join(self.training_dir,self.rootname+".sbr"), self.logger)
        self.mes_locate.start(self.sbr_data, 'star', self.interact1,
                              next_step=self.check_mes_star)
    
    def check_mes_star(self, *args):
        """ Review the results from mes_star and give a chance to retry """
        self.star_locations = self.mes_locate.output_data[:,:2]
        self.logger.debug('check_mes_star calling MESInterface.check with star_locations %s' % self.star_locations)
        self.mes_interface.check(self.star_locations,
                                 last_step=self.mes_star,
                                 next_step=self.wait_for_masks)
    
    def wait_for_masks(self, *args):
        """ Save data from mes_locate and wait for user input """
        self.database['mask_chip1'] = self.star_chip1 + 4
        self.mes_interface.wait(1, next_step=self.process_mask_fits)
    
    def process_mask_fits(self, *args):
        """ Use fitsUtils to comine raw data into a usable mask mosaic """
        self.__dict__.update(self.database)
        self.process_fits('mask', self.recalc2,
                          next_step=self.load_processed_mask)
    
    def load_processed_mask(self, *args):
        """ Load the mask frame FITS image that was processed by fitsUtils """
        self.open_fits(filename=self.rootname+"_mask.fits",
                       next_step=self.mes_hole)
    
    def mes_hole(self, *args):
        """ Call MESLocate in mask mode on the current image """
        self.mes_locate.start(self.sbr_data, 'mask', self.interact2,
                              next_step=self.check_mes_hole)
    
    def check_mes_hole(self, *args):
        """ Review the results from mes_hole and offer a chance to retry """
        self.hole_locations = self.mes_locate.output_data
        self.logger.debug('check_mes_hole calling MESInterface.check with hole_locations %s' % self.hole_locations)
        self.mes_interface.check(self.hole_locations,
                                 last_step=self.mes_hole,
                                 next_step=self.res_viewer_1)
    
    def res_viewer_1(self, *args):
        """ Call MESAnalyze on the data from mes_star and mes_hole """
        self.mes_analyze.start(self.star_locations, self.hole_locations,
                               next_step=self.end_mesoffset1)
    
    def end_mesoffset1(self, *args):
        """ Finish off the first, rough, star/hole location """
        self.mes_interface.log("Done with MES Offset 1!\n")
        self.mes_interface.write_to_logfile(self.rootname_logfile,
                                            "MES Offset 1",
                                            self.mes_analyze.offset)
        self.database['starhole_chip1'] = self.star_chip1 + 6
        self.mes_interface.go_to_mesoffset(2)
    
    
    ### ----- MESOFFSET2 FUNCTIONS ----- ###
    def begin_mesoffset2(self):
        """
        Start the second, star-hole location, based on the raw data. The first
        step is processing the starhole frames
        """
        # modify the database if necessary, and then absorb all values from the database
        img_dir = self.database['img_dir']
        if len(img_dir) <= 0 or img_dir[-1] != '/':
            self.database['img_dir'] += '/'
        if not hasattr(self, 'hole_locations'):
            self.mes_interface.log("No hole position data found; please run "+
                                   "literally any MESOffset besides 2.",
                                   level='error')
            return
        self.__dict__.update(self.database)
        
        self.process_starhole_fits()
    
    def process_starhole_fits(self, *args):
        """ Use fitsUtils to combine raw data into a compound starhole image """
        self.process_fits('starhole', self.recalc3,
                          next_step=self.load_processed_starhole)
    
    def load_processed_starhole(self, *args):
        """ Load the finished starhole image into ginga """
        self.open_fits(filename=self.rootname+"_starhole.fits",
                       next_step=self.mes_starhole)
    
    def mes_starhole(self, *args):
        """ Call MESLocate in starhole mode on the current image """
        self.logger.debug('mes_starhole calling self.mes_locate.start with self.hole_locations as %s' % self.hole_locations)
        self.mes_locate.start(self.hole_locations, 'starhole', self.interact3,
                              next_step=self.check_mes_starhole)
    
    def check_mes_starhole(self, *args):
        """ Review the results from mes_hole and offer a chance to retry """
        self.star_locations = self.mes_locate.output_data[:,:2]
        self.logger.debug('check_mes_starhole calling MESInterface.check with star_locations %s' % self.star_locations)
        self.mes_interface.check(self.star_locations,
                                 last_step=self.mes_starhole,
                                 next_step=self.res_viewer_2)
    
    def res_viewer_2(self, *args):
        """ Call MESAnalyze on the data from mes_star and mes_starhole """
        self.mes_analyze.start(self.star_locations, self.hole_locations,
                               next_step=self.end_mesoffset2)
    
    def end_mesoffset2(self, *args):
        """ Finish off the second star-hole location """
        self.mes_interface.log("Done with MES Offset 2!\n")
        self.mes_interface.write_to_logfile(self.rootname_logfile,
                                            "MES Offset 2",
                                            self.mes_analyze.offset)
        self.database['mask_chip1'] = self.starhole_chip1+4
        self.mes_interface.go_to_mesoffset(3)
    
    
    ### ----- MESOFFSET3 FUNCTIONS ----- ###
    def begin_mesoffset3(self):
        """
        Start the third, fine, star-hole location with updated mask locations.
        The first step is processing the mask frames
        """
        img_dir = self.database['img_dir']
        if len(img_dir) <= 0 or img_dir[-1] != '/':
            self.database['img_dir'] += '/'
        self.__dict__.update(self.database)
        
        self.process_new_mask_fits()
    
    def process_new_mask_fits(self, *args):
        """ Process the new, updated mask frames """
        self.process_fits('mask', self.recalc4,
                          next_step=self.load_new_mask)
    
    def load_new_mask(self, *args):
        """ Load the updated mask FITS image """
        self.open_fits(filename=self.rootname+"_mask.fits",
                       next_step=self.mes_hole_again)
    
    def mes_hole_again(self, *args):
        """ Get hole positions on the new mask frame """
        self.sbr_data = self.mes_locate.read_sbr_file(self.rootname+".sbr", self.logger)
        self.mes_locate.start(self.sbr_data, 'mask', self.interact4,
                              next_step=self.check_mes_hole_again)
    
    def check_mes_hole_again(self, *args):
        """ Review the results from mes_hole and offer a chance to retry """
        self.hole_locations = self.mes_locate.output_data
        self.logger.debug('check_mes_hole_again calling MESInterface.check with hole_locations %s' % self.hole_locations)
        self.mes_interface.check(self.hole_locations,
                                 last_step=self.mes_hole_again,
                                 next_step=self.wait_for_starhole)
    
    def wait_for_starhole(self, *args):
        """ Save mes locate data and wait for user input """
        if hasattr(self, 'starhole_chip1'):
            self.database['starhole_chip1'] = self.starhole_chip1 + 2
        else:
            self.database['starhole_chip1'] = self.mask_chip1 + 2
        self.mes_interface.wait(3, next_step=self.process_new_starhole_fits)
    
    def process_new_starhole_fits(self, *args):
        """ Process the new starhole FITS images """
        self.__dict__.update(self.database)
        self.process_fits('starhole', self.recalc5,
                          next_step=self.load_new_starhole)
    
    def load_new_starhole(self, *args):
        """ Load the updated starhole FITS image """
        self.open_fits(filename=self.rootname+"_starhole.fits",
                       next_step=self.mes_starhole_again)
    
    def mes_starhole_again(self, *args):
        """ Get star-hole positions on the new star-hole frame """
        self.mes_locate.start(self.hole_locations, 'starhole', self.interact5,
                              next_step=self.check_mes_starhole_again)
    
    def check_mes_starhole_again(self, *args):
        """ Review the results from mes_starhole and offer a chance to retry """
        self.star_locations = self.mes_locate.output_data[:,:2]
        self.logger.debug('check_mes_starhole_again calling MESInterface.check with star_locations %s' % self.star_locations)
        self.mes_interface.check(self.star_locations,
                                 last_step=self.mes_starhole_again,
                                 next_step=self.res_viewer_3)
    
    def res_viewer_3(self, *args):
        """ Call MESAnalyze on the data from mes_star and mes_hole """
        self.mes_analyze.start(self.star_locations, self.hole_locations,
                               next_step=self.end_mesoffset3)
    
    def end_mesoffset3(self, *args):
        """ Finish off the third, fine star-hole location with updated masks """
        self.mes_interface.log("Done with MES Offset 3!\n")
        self.mes_interface.write_to_logfile(self.rootname_logfile,
                                            "MES Offset 3",
                                            self.mes_analyze.offset)
        self.database['starhole_chip1'] = self.starhole_chip1 + 2
        self.mes_interface.go_to_mesoffset(2)
    
    ### ----- END MESOFFSET METHODS ----- ###
    
    def get_offset(self):
        """ Return the values that we came here for """
        return self.mes_analyze.offset
    
    
    def process_fits(self, mode, recalc=True, next_step=None):
        """
        Plug some values into fitsUtils and start a new thread to create a
        processed FITS image to be loaded and used
        @param mode:
            A string - either 'star', 'mask', or 'starhole'
        @param framenum:
            The chip1 frame number for the first set of input images
        @param recalc:
            Whether new images should even be processed
        @param next_step:
            The function to be called when this is done
        @returns:
            A threading.Event object to be used if the user ever decides to
            terminate the task
        @raises IOError:
            If the specified images cannot be found
        """
        out_filename = os.path.join(self.work_dir, self.rootname+"_"+mode+".fits")
        
        # if regenerate is off, don't bother with any of this
        if not recalc:
            if os.path.isfile(out_filename):
                if next_step != None:
                    next_step()
            else:
                self.mes_interface.log("No previous image found at "+
                                       out_filename+". Please change your "+
                                       "working directory or rootname, or "+
                                       "enable the 'Regenerate' option",
                                       level='error')
        
        # otherwise, start the appropriate process in a new thread
        else:
            self.go_to_gui('log')
            c, i = self.c_file, self.img_dir
            f = out_filename
            e = threading.Event()
            l = self.mes_interface.log
            if mode == 'star':
                n1, n2 = int(self.star_chip1), int(self.sky_chip1)
            elif mode == 'starhole':
                n1, n2 = int(self.starhole_chip1), int(self.mask_chip1)
            elif mode == 'mask':
                n1, n2 = int(self.mask_chip1), None
            task = lambda: fitsUtils.auto_process_fits(mode,n1,n2,c,i,f,e,l,
                                                       next_step=next_step)
            self.fv.nongui_do(task)
            self.terminate = e
    
    
    def open_fits(self, filename, next_step=None):
        """
        Open a FITS image and display it in ginga, then call a function
        @param filename:
            The name of the fits file
        @param next_step:
            The function to call once the image has been loaded
        """
        full_filename = os.path.join(self.work_dir, filename)
        self.image_set_next_step = next_step
        self.fitsimage.make_callback('drag-drop', [full_filename])
    
    
    def image_set_cb(self, *args):
        """
        Respond to an image being loaded by executing whatever function
        """
        if self.fitsimage.get_image() == None:  # I don't know why this callback sometimes
            return                              # executes for no reason, so I just ignore it.
        if self.image_set_next_step != None:
            self.image_set_next_step()
        self.image_set_next_step = None

#END

