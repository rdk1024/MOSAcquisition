#
# mesInterface.py -- a class that creates a nice GUI
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import math
import sys
from time import strftime

# local imports

# ginga imports
from ginga.gw import Widgets, Viewers

# third-party imports
import numpy as np
from numpy import ma



# constants
# database folder location
DBS = "../../MCSRED2/DATABASE"
# main menu parameters
params_0 = [    # TODO: get rid of these defaults; they're just for my convinience
        {'name':'star_chip1',
         'label':"Star Frame", 'type':'number', 'default':227463, 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 star FITS image"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':'string', 'default':"sbr_elaisn1rev", 'format':"{}.sbr",
         'desc':"The filename of the SBR file, which is used as rootname"},
        
        {'name':'c_file',
         'label':"Config File", 'type':'string', 'default':DBS+"/ana_apr16.cfg",
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':'string', 'default':"RAW",
         'desc':"The directory in which the input FITS images can be found"},
        
        {'name':'exec_mode',
         'label':"Execution Mode", 'type':'choice', 'options':["Normal","Fine"],
         'desc':"Choose 'Fine' to skip MES Offset 1"},
        
        {'name':'mode',
         'label':"Mode", 'type':'choice', 'options':["q1"],
         'desc':"I don't know what this means. Remind me to look it up later."}
        ]

# mesoffset1 parameters
params_1 = [
        {'name':'star_chip1',
         'label':"Star Frame", 'type':'number', 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 star FITS image"},
        
        {'name':'sky_chip1',
         'label':"Sky Frame", 'type':'number', 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 sky FITS image"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':'string', 'format':"{}.sbr",
         'desc':"The filename of the SBR file, which is used as rootname"},
        
        {'name':'c_file',
         'label':"Config File", 'type':'string',
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':'string',
         'desc':"The directory in which the raw FITS images can be found"},
        
        {'name':'reuse1',   # TODO: change reuse to recalculate or something
         'label':"Reuse Star", 'type':'boolean',
         'desc':"Do you want to reuse mosaiced star images from last time?"},
        
        {'name':'reuse2',
         'label':"Reuse Mask", 'type':'boolean',
         'desc':"Do you want to reuse mosaiced mask images from last time?"},
        
        {'name':'interact1',
         'label':"Interact Star", 'type':'boolean',
         'desc':"Do you want to interact with star position measurement?"},
        
        {'name':'interact2',
         'label':"Interact Hole", 'type':'boolean',
         'desc':"Do you want to interact with hole position measurement?"},
        
        {'name':'list1',
         'label':"List 1", 'type':'string',
         'desc':"something something something something something something "},
        
        {'name':'list2',
         'label':"List 2", 'type':'string',
         'desc':"I'm sorry, were you hoping for a descriptive tooltip?"},
        
        {'name':'mode',
         'label':"Mode", 'type':'choice', 'options':["q1"],
         'desc':"I don't know what this means. Remind me to look it up later."}
        ]

# mesoffset2 parameters
params_2 = [
        {'name':'starhole_chip1',
         'label':"Star-Hole Frame", 'type':'number', 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 star-hole FITS image"},
        
        {'name':'sky_chip1',
         'label':"Sky Name", 'type':'number', 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 sky FITS image"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':'string', 'format':"{}.sbr",
         'desc':"The filename of the SBR file, which is used as rootname"},
        
        {'name':'c_file',
         'label':"Config File", 'type':'string',
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':'string',
         'desc':"The directory in which the raw FITS images can be found"},
        
        {'name':'reuse3',
         'label':"Reuse", 'type':'boolean',
         'desc':"Do you want to reuse mosaiced images from last time?"},
        
        {'name':'interact3',
         'label':"Interact", 'type':'boolean',
         'desc':"Do you want to interact with star position measurement?"},
        
        {'name':'list1',
         'label':"List 1", 'type':'string',#TODO: what are the lists?
         'desc':"something something something something something something "},
        
        {'name':'mode',
         'label':"Mode", 'type':'choice', 'options':["q1"],
         'desc':"I don't know what this means. Remind me to look it up later."}
        ]

# mesoffset3 parameters
params_3 = [
        {'name':'starhole_chip1',
         'label':"Star-Hole Frame", 'type':'number', 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 star-hole FITS image"},
        
        {'name':'sky_chip1',
         'label':"Sky Name", 'type':'number', 'format':"MCSA{}.fits",
         'desc':"The frame number for the chip1 sky FITS image"},
        
        {'name':'rootname',
         'label':"Root Name", 'type':'string', 'format':"{}.sbr",
         'desc':"The filename of the SBR file, which is used as rootname"},
        
        {'name':'c_file',
         'label':"Config File", 'type':'string',
         'desc':"The location of the MCSRED configuration file"},
        
        {'name':'img_dir',
         'label':"Image Directory", 'type':'string',
         'desc':"The directory in which the raw FITS images can be found"},
        
        {'name':'reuse4',
         'label':"Reuse Mask", 'type':'boolean',
         'desc':"Do you want to reuse mosaiced mask images from last time?"},
        
        {'name':'reuse5',
         'label':"Reuse Star-Hole", 'type':'boolean',
         'desc':"Do you want to reuse mosaiced star-hole images from last time?"},
        
        {'name':'interact4',
         'label':"Interact Hole", 'type':'boolean',
         'desc':"Do you want to interact with hole position measurement?"},
        
        {'name':'interact5',
         'label':"Interact Star-Hole", 'type':'boolean',
         'desc':"Do you want to interact with star position measurement?"},
        
        {'name':'list1',
         'label':"List 1", 'type':'string',
         'desc':"something something something something something something "},
        
        {'name':'mode',
         'label':"Mode", 'type':'choice', 'options':["q1"],
         'desc':"I don't know what this means. Remind me to look it up later."}
        ]



class MESInterface(object):
    """
    A class that takes parameters from the user in a user-friendly menu.
    Intended for use as part of the MOS Acquisition software for aligning
    MOIRCS.
    """
    
    def __init__(self, manager):
        """
        Class constructor
        @param manager:
            The MESOffset plugin that this class communicates with
        """
        manager.initialise(self)
        
        # attributes
        self.get_value = []     # getter methods for all parameters
        self.set_value = []     # setter methods for all parameters
        
    
    
    def start(self):
        """
        Get user input so that we can start MES Locate/Analyze
        """
        # set the initial status message
        self.fv.showStatus("Waiting to start the MESOffset process.")
    
    
    def start_process_cb(self, _, idx):
        """
        Take the parameters from the gui and begin mesoffset{idx}
        @param n:
            The index for the process we are going to start - 0, 1, 2, or 3
        """
        self.log("Starting MES Offset {}...".format(idx))
        self.update_parameters(self.get_value[idx])
        if idx == 0:
            self.manager.execute_mesoffset0()
        elif idx == 1:
            self.manager.begin_mesoffset1()
        elif idx == 2:
            self.manager.begin_mesoffset2()
        elif idx == 3:
            self.manager.begin_mesoffset3()
    
    
    def update_parameters(self, getters):
        """
        Read parameter values from getters and saves them in self.manager
        @param getters:
            The dictionary of getter methods for parameter values
        """
        new_params = {key:get_val() for key, get_val in getters.items()}
        self.manager.database.update(new_params)
        
        
    def set_defaults(self, page_num):
        """
        Set the default values for the gui on page page_num
        @param page_num:
            The number for the GUI whose defaults we must set
        """
        setters = self.set_value[page_num]
        for key in setters:
            if self.manager.database.has_key(key):
                setters[key](self.manager.database[key])
    
    
    def go_to_mesoffset(self, idx):
        """
        Go to the 'epar' TabWidget and ask the user for parameters for this
        mesoffset process
        @param idx:
            The index of the process we want parameters for
        """
        self.set_defaults(idx)
        self.parameter_tabs.set_index(idx)
        self.manager.go_to_gui('epar')
        
    
    
    def wait(self, condition_string, next_step=None):
        """
        Set the 'wait' GUI to wait for a certain condition, and prepare to
        execute the next step.
        @param condition_string:
            The text the user will see above the 'Go!' button
        @param next_step:
            The function to be called when the 'Go!' button is pressed
        """
        self.fitsimage.zoom_fit()
        self.fitsimage.center_image()
        self.waiting_text.set_text(condition_string)
        if next_step != None:
            self.waiting_button.set_callback('activated', next_step)
        
        
    def log(self, text, *args, **kwargs):
        """
        Print text to the logger TextArea
        @param text:
            The string to be logged
        """
        if text.find("WARN: ") == 0:
            self.logger.warning(text[6:].strip(), *args, **kwargs)
        elif text.find("ERROR: ") == 0:
            self.logger.error(text[7:].strip(),   *args, **kwargs)
        else:
            self.logger.info(text.strip(),        *args, **kwargs)
        self.log_textarea.append_text(text+"\n", autoscroll=True)
    
    
    def write_to_logfile(self, filename, header, values):
        """
        Write args to a log file
        @param filename:
            The name of the log file
        @param header:
            The string that will serve as the first line of this log file entry
        @param args:
            The tuple of float values to be logged in the form (dx, dy, rotate)
        """
        # write the informaton to the file
        f = open(filename, 'a')
        f.write("="*50+"\n")
        f.write(header+"\n")
        f.write(strftime("%a %b %d %H:%M:%S %Z %Y\n"))
        f.write(("dx = {:7,.2f} (pix) dy = {:7,.2f} (pix) "+
                 "rotate = {:7,.4f} (degree) \n").format(*values))
        f.close()
        
        
    def gui_list(self, orientation='vertical'):
        """
        Combine the GUIs necessary for the interface part of this plugin
        Must be implemented for each MESPlugin
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A list of tuples with strings (names) and Widgets (guis)
        """
        # the interface is unique in that it has a tabwidget of similar guis
        tab = Widgets.TabWidget()
        tab.add_widget(self.make_gui_epar(0, orientation), "MESOffset 0")
        tab.add_widget(self.make_gui_epar(1, orientation), "MESOffset 1")
        tab.add_widget(self.make_gui_epar(2, orientation), "MESOffset 2")
        tab.add_widget(self.make_gui_epar(3, orientation), "MESOffset 3")
        self.parameter_tabs = tab
        
        return [('epar', self.parameter_tabs),
                ('wait', self.make_gui_wait(orientation)),
                ('log',  self.make_gui_log(orientation))]
        
        
    def make_gui_epar(self, idx, orientation='vertical'):
        """
        Construct a GUI for the parameter menu, which prepares to launch process
        @param idx:
            The index of this MESOffset process
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
        txt.set_font(self.manager.normal_font)
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
        btn.add_callback('activated', self.start_process_cb, idx)
        gui.add_widget(btn)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
    
    
    def make_gui_wait(self, orientation='vertical'):
        """
        Construct a GUI that waits for the user to press a button
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # make a textbox
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.body_font)
        gui.add_widget(txt)
        self.waiting_text = txt

        # make a button
        btn = Widgets.Button("Go!")
        btn.set_tooltip("Press once the above condition has been met.")
        gui.add_widget(btn)
        self.waiting_button = btn
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
        
        
    def make_gui_log(self, orientation='vertical'):
        """
        Construct a GUI for the log: a simple textbox
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
        lbl.set_font(self.manager.header_font)
        gui.add_widget(lbl)

        # the only thing here is a gigantic text box
        txt = Widgets.TextArea(wrap=False, editable=False)
        txt.set_font(self.manager.body_font)
        txt.set_text("\n"*100)  #XXX find a better way to stretch it
        gui.add_widget(txt, stretch=True)
        self.log_textarea = txt
        
        return gui
    
    
    
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
        grd.set_column_spacing(0)
        getters = {}
        setters = {}
        
        # put each of the controls in a row on the grid
        for i, param in enumerate(controls):
            name = param['name']
            # start by labelling the parameter
            lbl = Widgets.Label(param['label']+":  ", halign='right')
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
                    grd.add_widget(Widgets.Label(prefix, 'right'), i, 1)    #TODO: can I vertically align these
                grd.add_widget(wdg, i, 2)
                if suffix:
                    grd.add_widget(Widgets.Label(suffix, 'left'), i, 3)
            else:
                grd.add_widget(wdg, i, 2)
                
        return grd, getters, setters

#END

