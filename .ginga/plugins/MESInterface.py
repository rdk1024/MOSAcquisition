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
params_0 = [    # TODO: get rid of these defaults; they're just for my convinience
        {'name':'frame_star',
         'label':"Star Frame", 'type':'number', 'default':227463,
         'desc':"The frame number for the chip1 star FITS image",
         'format':"MCSA{}.fits"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':'string', 'default':"sbr_elaisn1rev",
         'desc':"The filename of the SBR file, which is used as rootname",
         'format':"{}.sbr"},
        
        {'name':'c_file',
         'label':"Config File", 'type':'string', 'default':"dir_mcsred$DATABASE/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':'string', 'default':"RAW/",
         'desc':"The directory in which the input FITS images can be found"},
        
        {'name':'exec_mode',
         'label':"Execution Mode", 'type':'choice', 'default':0,
         'desc':"The desired level of precision of alignment",
         'options':["Normal", "Fine"]},
        
        {'name':'mode',
         'label':"Mode", 'type':'choice', 'default':0,
         'desc':"I don't know what this means. Remind me to look it up later.",
         'options':["q1"]}
        ]

# mesoffset1 parameters
params_1 = [
        {'name':'star_chip1',
         'label':"Star Frame", 'type':'number',
         'desc':"The frame number for the chip1 star FITS image",
         'format':"MCSA{}.fits"},
        
        {'name':'sky_chip1',
         'label':"Sky Frame", 'type':'number',
         'desc':"The frame number for the chip1 sky FITS image",
         'format':"MCSA{}.fits"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':'string',
         'desc':"The filename of the SBR file, which is used as rootname",
         'format':"{}.sbr"},
        
        {'name':'c_file',
         'label':"Config File", 'type':'string', 'default':"dir_mcsred$DATABASE/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':'string', 'default':"data$",
         'desc':"The directory in which the raw FITS images can be found"},
        
        {'name':'retry1',
         'label':"Reuse Star", 'type':'boolean',
         'desc':"Do you want to reuse mosaiced star images last time?"},
        
        {'name':'retry2',
         'label':"Reuse Mask", 'type':'boolean',
         'desc':"Do you want to reuse mosaiced mask images last time?"},
        
        {'name':'inter1',
         'label':"Interact Star", 'type':'boolean',
         'desc':"Do you want to interact with star position measurement?"},
        
        {'name':'inter2',
         'label':"Interact Hole", 'type':'boolean',
         'desc':"Do you want to interact with hole position measurement?"},
        
        {'name':'list1',
         'label':"List 1", 'type':'string',
         'desc':"something something something something something something "},
        
        {'name':'list2',
         'label':"List 2", 'type':'string',
         'desc':"I'm sorry, were you hoping for a descriptive tooltip?"},
        
        {'name':'mode',
         'label':"Mode", 'type':'choice',
         'desc':"I don't know what this means. Remind me to look it up later.",
         'options':["q1"]}
        ]

# mesoffset2 parameters
params_2 = [
        {'name':'starhole_chip1',
         'label':"Star-Hole Frame", 'type':'number',
         'desc':"The frame number for the chip1 star-hole FITS image",
         'format':"MCSA{}.fits"},
        
        {'name':'sky_chip1',
         'label':"Sky Name", 'type':'number',
         'desc':"The frame number for the chip1 sky FITS image",
         'format':"MCSA{}.fits"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':'string',
         'desc':"The filename of the SBR file, which is used as rootname",
         'format':"{}.sbr"},
        
        {'name':'c_file',
         'label':"Config File", 'type':'string', 'default':"dir_mcsred$DATABASE/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':'string', 'default':"data$",
         'desc':"The directory in which the raw FITS images can be found"},
        
        {'name':'retry1',
         'label':"Reuse", 'type':'boolean', 'default':False,
         'desc':"Do you want to reuse mosaiced images last time?"},
        
        {'name':'interac1',
         'label':"Interact", 'type':'boolean',
         'desc':"Do you want to interact with star position measurement?"},
        
        {'name':'list1',
         'label':"List 1", 'type':'string',
         'desc':"something something something something something something "},
        
        {'name':'mode',
         'label':"Mode", 'type':'choice',
         'desc':"I don't know what this means. Remind me to look it up later.",
         'options':["q1"]}
        ]

# mesoffset3 parameters
params_3 = [
        {'name':'star_chip1',
         'label':"Star-Hole Frame", 'type':'number', 'default':226725,
         'desc':"The frame number for the chip1 star-hole FITS image",
         'format':"MCSA{}.fits"},
        
        {'name':'sky_chip1',
         'label':"Sky Name", 'type':'number', 'default':226725,
         'desc':"The frame number for the chip1 sky FITS image",
         'format':"MCSA{}.fits"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':'string',
         'desc':"The filename of the SBR file, which is used as rootname",
         'format':"{}.sbr"},
        
        {'name':'c_file',
         'label':"Config File", 'type':'string', 'default':"dir_mcsred$DATABASE/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':'string', 'default':"data$",
         'desc':"The directory in which the raw FITS images can be found"},
        
        {'name':'retry1',
         'label':"Reuse Star", 'type':'boolean',
         'desc':"Do you want to reuse mosaiced star images last time?"},
        
        {'name':'retry2',
         'label':"Reuse Mask", 'type':'boolean',
         'desc':"Do you want to reuse mosaiced mask images last time?"},
        
        {'name':'interac1',
         'label':"Interact Hole", 'type':'boolean',
         'desc':"Do you want to interact with hole position measurement?"},
        
        {'name':'interac2',
         'label':"Interact Star-Hole", 'type':'boolean',
         'desc':"Do you want to interact with star-hole position measurement?"},
        
        {'name':'list1',
         'label':"List 1", 'type':'string',
         'desc':"something something something something something something "},
        
        {'name':'mode',
         'label':"Mode", 'type':'choice',
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
        
        # attributes
        self.autorun = False    # whether it should progress automatically
        self.get_value = []     # getter methods for all parameters
        self.set_value = []     # setter methods for all parameters
        self.parameters = {}    # dictionary of parameter values
        
        
        
    def build_specific_gui(self, stack, orientation='vertical'):
        """
        Combine the GUIs necessary for this particular plugin
        Must be implemented for each MESPlugin
        @param stack:
            The stack in which each part of the GUI will be stored
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        """
        stack.add_widget(self.make_gui_epar(0, self.mesoffset0, orientation))
        stack.add_widget(self.make_gui_epar(1, self.mesoffset1, orientation))
        stack.add_widget(self.make_gui_epar(2, self.mesoffset2, orientation))
        stack.add_widget(self.make_gui_epar(3, self.mesoffset3, orientation))
        stack.add_widget(self.make_gui_log(orientation))
        
        
    def make_gui_epar(self, idx, process, orientation='vertical'):
        """
        Construct a GUI for the parameter menu, which prepares to launch process
        @param idx:
            The index of this MESOffset process
        @param process:
            The function that the GO! button will call
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        name = "MES Offset {}".format(idx)
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Use the widgets below to specify the parameters for "+
                     name+". Hover over each one to get a description of "+
                     "what it means. When you are finished, press the 'Go!' "+
                     "button, which will begin "+name+".")
        exp.set_widget(txt)
        
        # chose the params
        if idx == 0:
            params = params_0
        elif idx == 1:
            params = params_1
        elif idx == 2:
            params = params_2
        elif idx == 3:
            params = params_3

        # create a grid to group the different controls
        frm = Widgets.Frame(name)
        gui.add_widget(frm)
        grd, getters, setters = self.build_control_layout(params)
        self.get_value.append(getters)
        self.set_value.append(setters)
        frm.set_widget(grd)
        
        # the go button is important
        btn = Widgets.Button("Go!")
        btn.add_callback('activated', process)
        gui.add_widget(btn)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
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
    
    
    def start(self):
        """
        Called when the plugin is opened for the first time
        """
        super(MESInterface, self).start()
        
        # set the initial status message
        self.fv.showStatus("Waiting to start the MESOffset process.")
    
    
    def mesoffset0(self, *args):
        """
        Runs all three procedures of MOS Acquisition
        """
        self.update_parameters(self.get_value[0].items())
        self.autorun = True
        self.go_to_page(1)
    
    
    def mesoffset1(self, *args):
        """
        Runs the first procedure of MOS Acquisition:
        star and mask measurements
        """
        # first, open the log
        self.stack.set_index(4)
        
        self.update_parameters(self.get_value[1].items())
        self.log("Checking header data...")
        self.log("Processing star frames")
        self.log("Measuring star positions...")
        self.log("Waiting for mask images")
        self.log("Processing mask frames...")
        self.log("Measuring hole positions...")
        self.log("Analyzing results...")
        if self.autorun:
            self.log("Going to MES Offset 1...")
        else:
            self.log("Done!")
        self.go_to_page(2)
    
    
    def mesoffset2(self, *args):
        """
        Runs the second procedure of MOS Acquisition:
        starhole measurements
        """
        self.update_parameters(self.get_value[2].items())
        self.log("Checking header data...")
        self.log("Processing star frames")
        self.log("Measuring star positions...")
        self.log("Waiting for mask images")
        self.log("Processing mask frames...")
        self.log("Measuring hole positions...")
        self.log("Analyzing results...")
        if self.autorun:
            self.log("Going to MES Offset 2...")
        else:
            self.log("Done!")
        self.go_to_page(3)
    
    
    def mesoffset3(self, *args):
        """
        Runs the third procedure of MOS Acquisition:
        mask and starhole measurements
        """
        self.update_parameters(self.get_value[3].items())
        self.log("Checking header data...")
        self.log("Processing star frames")
        self.log("Measuring star positions...")
        self.log("Waiting for mask images")
        self.log("Processing mask frames...")
        self.log("Measuring hole positions...")
        self.log("Analyzing results...")
        if self.autorun:
            self.log("Going to MES Offset 3...")
        else:
            self.log("Done!")
        self.go_to_page(0)
    
    
    def update_parameters(self, getters):
        """
        Updates the parameters instance variable with the values found from
        getters
        @param getters:
            The dictionary of getter methods for parameter values
        """
        self.parameters.update({key:get_val() for key, get_val in getters})
    
    
    def go_to_page(self, page_num):
        """
        Takes the user to the interface for mesoffset{page_num}, and fills in
        default values
        @param page_num:
            The index of this mesoffset
        """
        setters = self.set_value[page_num]
        for key in setters:
            if self.parameters.has_key(key):
                setters[key](self.parameters[key])
        self.stack.set_index(page_num)
        
        
    def log(self, text, *args, **kwargs):
        """
        Prints text to the logger TextArea
        @param text:
            The string to be logged
        """
        self.logger.info(text, *args, **kwargs)
        self.log_textarea.append_text(text, autoscroll=True)
        
    
    
    @staticmethod
    def build_control_layout(controls):
        """
        Build a grid full of labels on the left and input widgets on the right.
        @param controls:
            A list of dictionary where each dictionary has the keys 'name' (the
            name of the parameter), 'type' (string, number, etc.), 'default'
            (the starting value), 'desc' (the tooltip), possibly 'format' (puts
            labels on either side of the input), and possibly 'options' (the
            list of possible values, if type is 'combobox')
        @returns:
            A Widgets.Box containing controls for all of the layouts,
            and a dictionary whose keys are parameter names and whose values
            are functions to return those parameter values,
            and a dictionary whose keys are parameter names and whose values
            are functions to set those parameter values
        """
        grd = Widgets.GridBox(rows=len(controls), columns=4)
        getters = {}
        setters = {}
        
        # put each of the controls in a row on the grid
        for i, param in enumerate(controls):
            name = param['name']
            # start by labelling the parameter
            lbl = Widgets.Label(param['label']+":", halign='right')
            lbl.set_tooltip(param['desc'])
            grd.add_widget(lbl, i, 0)
            
            # create a widget based on type
            if param['type'] == 'string':
                wdg = Widgets.TextEntry(editable=True)
                getters[name] = wdg.get_text
                setters[name] = wdg.set_text
            elif param['type'] == 'number':
                wdg = Widgets.SpinBox()
                wdg.set_limits(0, 99999999)
                getters[name] = wdg.get_value
                setters[name] = wdg.set_value
            elif param['type'] == 'choice':
                wdg = Widgets.ComboBox()
                for option in param['options']:
                    wdg.append_text(option)
                getters[name] = wdg.get_index
                setters[name] = wdg.set_index
            elif param['type'] == 'boolean':
                wdg = Widgets.CheckBox()
                getters[name] = wdg.get_state
                setters[name] = wdg.set_state
            else:
                raise TypeError("{} is not a valid parameter type.".format(
                                                                param['type']))
            wdg.set_tooltip(param['desc'])
            
            # insert a default, if necessary
            if param.has_key('default'):
                setters[name](param['default'])
            
            # surround the widget with text, if necessary
            if param.has_key('format'):
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
                
        return grd, getters, setters

#END

