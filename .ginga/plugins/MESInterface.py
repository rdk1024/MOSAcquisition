#
# MESInterface.py -- a ginga plugin that manages the other MES plugins.
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import math
import sys

# local imports
from util.mosplugin import MESPlugin

# ginga imports
from ginga.gw import Widgets, Viewers

# third-party imports
import numpy as np
from numpy import ma



# constants
# main menu parameters
main_params = [
        {'name':"Frame Number", 'type':'number', 'default':227463,
         'desc':"The frame number for the chip1 star FITS image",
         'format':"MCSA{}.fits"},
         
         {'name':"Root Name", 'type':'string', 'default':"sbr_elaisn1rev",
         'desc':"The filename of the SBR file, which is used as rootname",
         'format':"{}.sbr"},
         
         {'name':"Image Directory", 'type':'string', 'default':"RAW",
         'desc':"The directory in which the input FITS images can be found",
         'format':"{}/"},
         
         {'name':"Execution Mode", 'type':'choice', 'default':0,
         'desc':"The desired level of precision of alignment",
         'options':["Normal", "Fine"]},
         
         {'name':"Config File", 'type':'string', 'default':"dir_mcsred$DATAMASE/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file",
         'format':None},
         
         {'name':"Mode", 'type':'choice', 'default':0,
         'desc':"I don't know what this means. Remind me to look it up later.",
         'options':["q1"]}
           ]



class MESInterface(MESPlugin):
    """
    A custom LocalPlugin for ginga that takes input from the user, opens and
    handles the other three MES plugins, and replaces the xgterminal from the
    old mesoffset IRAF scripts. Intended for use as part of the MOS Acquisition
    software for aligning MOIRCS.
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
        # LocalPlugin constructor defines self.fv, self.fitsimage, self.logger;
        # MESPlugin constructor defines self.dc, self.canvas, and some fonts
        super(MESInterface, self).__init__(fv, fitsimage)
        
        
        
    def build_specific_gui(self, stack, orientation='vertical'):
        """
        Combine the GUIs necessary for this particular plugin
        Must be implemented for each MESPlugin
        @param stack:
            The stack in which each part of the GUI will be stored
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        """
        stack.add_widget(self.make_gui_main(orientation))
        stack.add_widget(self.make_gui_log(orientation))
        
        
    def make_gui_main(self, orientation='vertical'):
        """
        Construct a GUI for the main menu, which prepares to launch MESOffset
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Use the widgets below to specify the parameters for "+
                     "MESOffset. Hover over each one to get a description of "+
                     "what it means. When you are finished, press the 'Go!' "+
                     "button, which will begin step 1.")
        exp.set_widget(txt)

        # create a grid to group the different controls
        frm = Widgets.Frame()
        gui.add_widget(frm)
        grd, self.get_value = self.build_control_layout(main_params)
        frm.set_widget(grd)
        
        return gui
        
        
    def make_gui_log(self, orientation='vertical'):
        """
        Construct a GUI for the second step: cropping the stars
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # label the log
        lbl = Widgets.Label("Please wait...")
        lbl.set_font(self.header_font)
        gui.add_widget(lbl)

        # the only thing here is a gigantic text box
        txt = Widgets.TextArea(wrap=False, editable=False)
        txt.set_font(self.body_font)
        gui.add_widget(txt, stretch=True)
        self.log_textarea = txt
        
        return gui
        
    
    def build_control_layout(self, controls):
        """
        Build a grid full of labels on the left and input widgets on the right.
        @param controls:
            A list of dictionary where each dictionary has the keys 'name' (the
            name of the parameter), 'type' (string, number, etc.), 'default'
            (the starting value), 'desc' (the tooltip), possibly 'format' (puts
            labels on either side of the input), and possibly 'options' (the
            list of possible values, if type is 'combobox')
        @returns:
            A Widgets.GridBox containing controls for all of the layouts,
            and a dictionary whose keys are parameter names and whose values
            are functions to return those parameter values
        """
        grd = Widgets.GridBox(rows=len(controls), columns=4)
        getters = {}
        
        # put each of the controls in a row on the grid
        for i, param in enumerate(controls):
            # start by labelling the parameter
            lbl = Widgets.Label(param['name']+":", halign='right')
            lbl.set_tooltip(param['desc'])
            grd.add_widget(lbl, i, 0)
            
            # create a widget based on type
            if param['type'] == 'string':
                wdg = Widgets.TextEntry(editable=True)
                wdg.set_text(param['default'])
                getters[param['name']] = wdg.get_text
            elif param['type'] == 'number':
                wdg = Widgets.SpinBox()
                wdg.set_limits(0, 99999999)
                wdg.set_value(param['default'])
                getters[param['name']] = wdg.get_value
            elif param['type'] == 'choice':
                wdg = Widgets.ComboBox()
                for option in param['options']:
                    wdg.append_text(option)
                wdg.set_index(param['default'])
                getters[param['name']] = wdg.get_index
            else:
                raise TypeError("{} is not a valid parameter type.".format(
                                                                param['type']))
            wdg.set_tooltip(param['desc'])
            
            # surround the widget with text, if necessary
            if param.has_key('format') and param['format'] != None:
                format_str = param['format']
                idx = format_str.index('{}')
                prefix = format_str[:idx]
                suffix = format_str[idx+2:]
                if prefix:
                    grd.add_widget(Widgets.Label(prefix, 'right'), i, 1)
                grd.add_widget(wdg, i, 2)
                if suffix:
                    grd.add_widget(Widgets.Label(suffix, 'left'), i, 3)
            else:
                grd.add_widget(wdg, i, 2)
                
        return grd, getters
    
    
    def start(self):
        """
        Called when the plugin is opened for the first time
        """
        super(MESInterface, self).start()
        
        # set the initial status message
        self.fv.showStatus("Waiting to start the MESOffset process.")
        
        
    def log(self, text):
        print "What should I do with this text?"
        print "text"
        self.logger.log(text)
        self.log_textarea.append_text(text, autoscroll=True)
        

def tag(step, mod_1, mod_2=None):
    """
    Create a new tag given the step and some modifiers,
    to be used by self.canvas
    @param step:
        Which step we are on
    @param mod_1:
        The primary modifer to distinguish it from other objects
    @param mod_2:
        The secondary modifier, if it is needed for additional distinction
    @returns:
        A 'tag', probably a string, to be passed into CanvasMixin.add
    
    >>> tag(1, 3, 'pt')
    '@1:3:pt'
    """
    if mod_2 == None:
        return '@{}:{}'.format(step, mod_1)
    else:
        return '@{}:{}:{}'.format(step, mod_1, mod_2)

#END

