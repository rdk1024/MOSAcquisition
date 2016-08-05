#
# mesInterface.py -- a class that creates a nice GUI
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import os
from time import strftime

# ginga imports
from ginga.gw import Widgets
from ginga.misc.Callback import CallbackError



# constants
DIR_MCSRED = '../../MCSRED2/'
PAR_FILENAME = 'mesoffset_parameters.txt'
VAR_FILENAME = 'mesoffset_directories.txt'



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
        self.get_value = []         # getter methods for all parameters
        self.set_value = []         # setter methods for all parameters
        self.resume_mesoffset = {}  # intermediate functions to call after waiting
        self.last_wait_gui = 0      # the last 'wait' gui we were at
        self.variables = read_variables()   # defined variables
    
    
    
    def start_process_cb(self, *args):
        """
        Take the parameters from the gui and begin mesoffset{idx}
        """
        proc_num = self.parameter_tabs.get_index()
        self.log("Starting MES Offset {}...".format(proc_num))
        try:
            self.update_parameters(self.get_value[proc_num], proc_num == 0)
        except NameError as e:
            self.log("NameError: "+str(e), level='e')
            return
        if proc_num == 0:
            self.manager.execute_mesoffset0()
        elif proc_num == 1:
            self.manager.begin_mesoffset1()
        elif proc_num == 2:
            self.manager.begin_mesoffset2()
        elif proc_num == 3:
            self.manager.begin_mesoffset3()
    
    
    def update_parameters(self, getters, write_to_file=False):
        """
        Read parameter values from getters and save them in self.manager, as
        well as in MCSRED2/mesoffset.par
        Scan all strings for variables
        @param getters:
            The dictionary of getter methods for parameter values
        @param write_to_file:
            Whether we should write these parameters to the .par file
        @raises NameError:
            If one of the values contains an undefined variable
        """
        # if DIR_MCSRED is a directory, write to the parameter file in it
        if write_to_file and os.path.isdir(DIR_MCSRED):
            par_file = open(DIR_MCSRED+PAR_FILENAME, 'w')
        else:
            par_file = None
        
        # now cycle through getters and update the file and manager
        new_params = {}
        for key, get_val in getters.items():
            value = get_val()
            if par_file != None:
                par_file.write('{},{}\n'.format(key,value))
            if type(value) in (str, unicode):
                value = process_filename(value, self.variables)
            new_params[key] = value
        self.manager.database.update(new_params)
    
    
    def go_to_mesoffset(self, idx):
        """
        Go to the 'epar' TabWidget and ask the user for parameters for this
        mesoffset process
        @param idx:
            The index of the process we want parameters for
        """
        self.last_wait_gui = 0
        self.set_defaults(idx)
        self.parameter_tabs.set_index(idx)
        self.go_to_gui('epar')
    
    
    def wait(self, idx, next_step=None):
        """
        Go to the 'wait' gui at this index to get more info from the user, and
        prepare to execute the next step.
        @param idx:
            The index of the process that this interrupts
        @param next_step:
            The function to be called when the 'Go!' button is pressed
        """
        self.last_wait_gui = idx
        if idx == 1:
            self.set_defaults(4)
        elif idx == 3:
            self.set_defaults(5)
        self.go_to_gui('wait '+str(idx))
        self.resume_mesoffset[idx] = next_step
    
    
    def return_to_menu_cb(self, *args):
        """
        Go back to the last parameter menu you were at - either 'epar' or 'wait'
        """
        if self.last_wait_gui:
            self.go_to_gui('wait '+str(self.last_wait_gui))
        else:
            self.go_to_gui('epar')
    
    
    def resume_process_cb(self, *args):
        """
        Take the parameters from the waiting gui and resume the current process
        """
        try:
            if self.last_wait_gui == 1:
                self.update_parameters(self.get_value[4])
            elif self.last_wait_gui == 3:
                self.update_parameters(self.get_value[5])
        except NameError as e:
            self.log("NameError: "+str(e), level='e')
            return
        self.resume_mesoffset[self.last_wait_gui]()
    
    
    def check(self, data, last_step=None, next_step=None):
        """
        Go to the 'check' GUI and let the user review their data, and decide
        whether they want to remeasure those locations or move on
        @param data:
            The location data in the form of a 2-3 column numpy array (x,y[,r])
        @param last_step:
            The function to be executed if these data are unsatisfactory
        @param next_step:
            The function to be executed if these data are deemed good enough
        """
        if data.shape[1] == 2:
            res_string = "   x      y\n"
            fmt_string = "{:5.0f}  {:5.0f}\n"
        elif data.shape[1] == 3:
            res_string = "   x      y      r\n"
            fmt_string = "{:5.0f}  {:5.0f}  {:5.1f}\n"
        
        for row in data:
            res_string += fmt_string.format(*row)
        self.results_textarea.set_text(res_string)
        self.last_step = last_step
        self.next_step = next_step
        self.go_to_gui('check')
    
    
    def retake_measurements_cb(self, *args):
        """
        Execute self.last_step
        """
        self.manager.clear_canvas()
        self.last_step()
    
    
    def use_measurements_cb(self, *args):
        """
        Execute self.next_step
        """
        self.manager.clear_canvas()
        self.next_step()
    
    
    def go_to_gui(self, gui_name):
        """
        Go to the appropriate GUI, and set appropriate callbacks
        @param gui_name:
            The string identifier for this GUI
        """
        if gui_name == 'check':
            self.set_callbacks(right_click=self.use_measurements_cb)
        if gui_name == 'error':
            self.set_callbacks(right_click=self.return_to_menu_cb)
        self.manager.go_to_gui(gui_name)
    
    
    def set_callbacks(self, left_click=None, right_click=None):
        """
        Set some basic callbacks
        @param left_click:
            The function to run when the user left clicks
        @param right_click:
            Guess.
        @param enter:
            The function to run when the user hits return
        """
        self.manager.clear_canvas(keep_objects=True)
        self.canvas.clear_callback('cursor-up')
        if left_click != None:
            self.canvas.add_callback('cursor-up', left_click)
        self.canvas.clear_callback('draw-up')
        if right_click != None:
            self.canvas.add_callback('draw-up', right_click)
    
    
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
    
    
    def log(self, *args, **kwargs):
        """
        Print text to the logger TextArea from the main thread
        """
        self.fv.gui_do(self._log, *args, **kwargs)
    
    
    def _log(self, text, level='i'):
        """
        Print text to the logger TextArea
        @param text:
            The string to be logged
        @param level:
            The level of urgency ('d' for debug, 'i' for info, etc.)
        """
        if level[0].lower() == 'd':
            self.logger.debug(text.strip())
        elif level[0].lower() == 'i':
            self.logger.info(text.strip())
            self.log_textarea.append_text(text+"\n", autoscroll=True)
        elif level[0].lower() == 'w':
            self.logger.warning(text.strip())
            self.log_textarea.append_text("WARN: "+text+"\n", autoscroll=True)
        elif level[0].lower() == 'e':
            self.logger.error(text.strip())
            self.log_textarea.append_text("ERROR: "+text+"\n", autoscroll=True)
            self.err_textarea.set_text(text)
            self.go_to_gui('error')
        else:
            self.logger.critical(text.strip())
            self.log_textarea.append_text("CRIT: "+text+"\n", autoscroll=True)
            self.err_textarea.set_text("CRITICAL!\n"+text)
            self.go_to_gui('error')
    
    
    def terminate_process_cb(self, *args):
        """
        Stop the process currently connected to self.manager.terminate,
        wait for the process to receive the signal, and then go to the main menu
        """
        if hasattr(self.manager, 'terminate'):
            if self.manager.terminate != None:
                self.manager.terminate.set()
    
    
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
        self.get_value = []
        self.set_value = []
        tab = Widgets.TabWidget()
        tab.add_widget(self.make_gui_epar(0, orientation), "MESOffset 0")
        tab.add_widget(self.make_gui_epar(1, orientation), "MESOffset 1")
        tab.add_widget(self.make_gui_epar(2, orientation), "MESOffset 2")
        tab.add_widget(self.make_gui_epar(3, orientation), "MESOffset 3")
        self.parameter_tabs = tab
        
        return [('epar',   self.parameter_tabs),
                ('wait 1', self.make_gui_wait(1, orientation)),
                ('wait 3', self.make_gui_wait(3, orientation)),
                ('check',  self.make_gui_look(orientation)),
                ('log',    self.make_gui_log(orientation)),
                ('error',  self.make_gui_err(orientation))]
        
        
    def make_gui_epar(self, idx, orientation='vertical'):
        """
        Construct a GUI for the parameter menu, which prepares to launch process
        @param idx:
            The index of this MESOffset process, or None for an ambiguous epar
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
        txt.set_font(self.manager.NORMAL_FONT)
        txt.set_text("Use the widgets below to specify the parameters for "+
                     name+". Hover over each one to get a description of "+
                     "what it means. When you are finished, press the 'Go!' "+
                     "button, which will begin "+name+".")
        exp.set_widget(txt)
        
        # chose the params
        if idx == 0:
            params = self.manager.PARAMS_0
        elif idx == 1:
            params = self.manager.PARAMS_1
        elif idx == 2:
            params = self.manager.PARAMS_2
        elif idx == 3:
            params = self.manager.PARAMS_3

        # create a grid to group the different controls
        frm = Widgets.Frame(name)
        gui.add_widget(frm)
        grd, getters, setters = build_control_layout(params,
                                                     self.start_process_cb)
        self.get_value.append(getters)
        self.set_value.append(setters)
        frm.set_widget(grd)
        
        # create a box for the defined variables
        frm = Widgets.Frame("Defined Variables")
        gui.add_widget(frm)
        box = build_dict_labels(self.variables)
        frm.set_widget(box)
        
        # the go button will go in a box
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the go button is important
        btn = Widgets.Button("Go!")
        btn.add_callback('activated', self.start_process_cb)
        btn.set_tooltip("Start "+name+" with the given parameters")
        box.add_widget(btn)
        box.add_widget(Widgets.Label(''), stretch=True)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
    
    
    def make_gui_wait(self, idx, orientation='vertical'):
        """
        Construct an intermediate epar GUI, as a break in the middle of a
        process
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
        txt.set_font(self.manager.NORMAL_FONT)
        txt.set_text("Verify parameters in order to continue "+name+", using "+
                     "the widgets below. When you are finished and the "+
                     "specified files are ready for analysis, press the 'Go!' "+
                     "button, which will resume "+name+".")
        exp.set_widget(txt)
        
        # chose the params
        if idx == 1:
            params = self.manager.PARAMS_1p5
        elif idx == 3:
            params = self.manager.PARAMS_3p5
        
        # create a grid to group the different controls
        frm = Widgets.Frame()
        gui.add_widget(frm)
        grd, getters, setters = build_control_layout(params,
                                                     self.resume_process_cb)
        self.get_value.append(getters)  # NOTE that these getters and setters
        self.set_value.append(setters)  # will have different indices than idx
        frm.set_widget(grd)
        
        # create a box for the defined variables
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = build_dict_labels(self.variables)
        frm.set_widget(box)
        
        # the go button will go in a box
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the go button is important
        btn = Widgets.Button("Go!")
        btn.add_callback('activated', self.resume_process_cb)
        btn.set_tooltip("Continue "+name+" with the given parameters")
        box.add_widget(btn)
        box.add_widget(Widgets.Label(''), stretch=True)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
    
    
    def make_gui_look(self, orientation='vertical'):
        """
        Construct a GUI for checking results
        @param orientaiton:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # fill a text box with brief instructions and put them in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.NORMAL_FONT)
        txt.set_text("Look at the results below. If they seem correct, click "+
                     "'Continue' to proceed to the next step. If they seem "+
                     "inadequate, click 'Try Again', and you will be taken "+
                     "back to the previous step to retake measurements. If "+
                     "you wish to edit the parameters for this process, click "+
                     "'Start Over' to abort and return to the main menu.")
        exp.set_widget(txt)
        
        # put in a label to ask the question:
        lbl = Widgets.Label("Are the results satisfactory?")
        gui.add_widget(lbl)
        
        # now add in the textbox for the results
        txt = Widgets.TextArea(wrap=False, editable=False)
        txt.set_font(self.manager.MONO_FONT)
        gui.add_widget(txt, stretch=True)
        self.results_textarea = txt
        
        # now make an HBox for the controls
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the Try Again button goes to the last step
        btn = Widgets.Button("Try Again")
        btn.add_callback('activated', self.retake_measurements_cb)
        btn.set_tooltip("Go back and take these measurements again")
        box.add_widget(btn)
        
        # the Start Over button goes to the main menu
        btn = Widgets.Button("Start Over")
        btn.add_callback('activated', self.return_to_menu_cb)
        btn.set_tooltip("Return to the menu to edit your parameters")
        box.add_widget(btn)
        
        # the Continue button goes to the next step
        btn = Widgets.Button("Continue")
        btn.add_callback('activated', self.use_measurements_cb)
        btn.set_tooltip("Proceed to the next part of the process")
        box.add_widget(btn)
        
        # space the buttons
        box.add_widget(Widgets.Label(''), stretch=True)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
    
    
    def make_gui_log(self, orientation='vertical'):
        """
        Construct a GUI for the log: a simple textbox
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widget object containing all necessary buttons, labels, etc.
        """
        # there is a box with a single button
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # the 'log' is a gigantic text box
        scr = Widgets.ScrollArea()
        gui.add_widget(scr, stretch=True)
        txt = Widgets.TextArea(wrap=False, editable=False)
        txt.set_font(self.manager.BODY_FONT)
        self.log_textarea = txt
        scr.set_widget(txt)
        
        # underneath it is a 'Stop' button TODO: does this ruin the textbox size?
        box = Widgets.HBox()
        gui.add_widget(box)
        btn = Widgets.Button("Stop")
        btn.set_tooltip("Terminate the current process")
        btn.add_callback('activated', self.terminate_process_cb)
        box.add_widget(btn)
        box.add_widget(Widgets.Label(''), stretch=True)
        
        return gui
    
    
    def make_gui_err(self, orientation='vertical'):
        """
        Construct a GUI for errors: there must be a textbox and a back button
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all the necessary stuff
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # start with a label to tell the user why they are here
        lbl = Widgets.Label("Sumimasen! :(")
        lbl.set_font(self.manager.HEADER_FONT)
        gui.add_widget(lbl)
        
        # now for the error box itself
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.BODY_FONT)
        gui.add_widget(txt, stretch=True)
        self.err_textarea = txt
        
        # finish off with a box of important controls at the end
        box = Widgets.HBox()
        gui.add_widget(box)
        
        # in it is a back button
        btn = Widgets.Button("Return to Menu")
        btn.add_callback('activated', self.return_to_menu_cb)
        btn.set_tooltip("Correct the error and try again")
        box.add_widget(btn)
        box.add_widget(Widgets.Label(''), stretch=True)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
    
    
    
    @staticmethod
    def write_to_logfile(filename, header, values):
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



def build_control_layout(controls, callback=None):
    """
    Build a grid full of labels on the left and input widgets on the right.
    @param controls:
        A list of dictionary where each dictionary has the keys 'name' (the
        name of the parameter), 'type' (str, in, etc.), 'default'
        (the starting value), 'desc' (the tooltip), possibly 'format' (puts
        labels on either side of the input), and possibly 'options' (the
        list of possible values, if type is 'combobox')
    @param callback:
        The function, if any, to be called when 'enter' is pressed
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
    old_pars = read_parameters()
    
    # put each of the controls in a row on the grid
    for i, param in enumerate(controls):
        name = param['name']
        # start by labelling the parameter
        lbl = Widgets.Label(param['label']+":  ", halign='right')
        lbl.set_tooltip(param['desc'])
        grd.add_widget(lbl, i, 0)
        
        # create a widget based on type
        if param.has_key('options'):
            wdg = Widgets.ComboBox()
            for option in param['options']:
                wdg.append_text(option)
            wdg.set_index(0)
            getters[name] = wdg.get_index
            setters[name] = wdg.set_index
        elif param['type'] == int:
            wdg = Widgets.SpinBox(dtype=int)
            wdg.set_limits(0, 99999999)
            wdg.set_value(0)
            getters[name] = wdg.get_value
            setters[name] = wdg.set_value
        elif param['type'] == str:
            wdg = Widgets.TextEntry(editable=True)
            wdg.set_text("")
            if callback != None:
                wdg.add_callback('activated', callback)
            getters[name] = wdg.get_text
            setters[name] = wdg.set_text
        elif param['type'] == bool:
            wdg = Widgets.CheckBox()
            wdg.set_state(True)
            getters[name] = wdg.get_state
            setters[name] = wdg.set_state
        else:
            raise TypeError("{} is not a valid par-type.".format(param['type']))
        
        # apply the description and default
        wdg.set_tooltip(param['desc'])
        if old_pars != None and old_pars.has_key(param['name']):
            try:
                old_value = param['type'](old_pars[param['name']])
                setters[param['name']](old_value)
            except ValueError:
                pass
        elif param.has_key('default'):
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


def build_dict_labels(dictionary):
    """
    Build a gui that displays the dictionary keys and values
    @param dictionary:
        A dict populated with str keys and str values
    @returns:
        A Widget object that displays the contents of the dictionary
    """
    grd = Widgets.GridBox(rows=len(dictionary), columns=3)
    grd.set_spacing(3)
    for i, key in enumerate(dictionary):
        lbl1 = Widgets.Label("$"+key+":  ",     halign='left')
        lbl2 = Widgets.Label(dictionary[key], halign='left')
        grd.add_widget(lbl1, i, 0)
        grd.add_widget(lbl2, i, 1)
        grd.add_widget(Widgets.Label(''), i, 2, stretch=True)
    return grd


def process_filename(filename, variables=None):
    """
    Take a filename and modifies it to account for any variables
    @param filename:
        The input filename to be processed
    @param variables:
        The dictionary of defined variable names to values
    @returns:
        The updated filename
    @raises NameError:
        If there is an undefined variable
    """
    if variables == None:
        variables = read_variables()
    
    # scan the filename for dollar signs
    while "$" in filename:
        ds_idx = filename.find("$")
        sl_idx = filename[ds_idx:].find("/")
        if sl_idx == -1:
            sl_idx = len(filename)
        var_name = filename[ds_idx+1:sl_idx]
        
        # if it is a defined variable, replace it
        if variables.has_key(var_name.upper()):
            filename = filename.replace("$"+var_name,
                                        variables[var_name.upper()])
        
        # otherwise, raise an error
        else:
            err_msg = ("$"+var_name+" is not a defined variable. Defined "+
                       "variables are:\n")
            for key in variables:
                err_msg += "    ${}: {}\n".format(key, variables[key])
            err_msg += "Please check your spelling and try again."
            raise NameError(err_msg)
    
    return filename


def read_parameters():
    """
    Get the last parameters that were used for mesoffset
    @returns:
        A dictionary where keys are parameter names, and values are values,
        or None if the file could not be found or was in the wrong format.
    """
    try:
        output = {}
        par_file = open(DIR_MCSRED+PAR_FILENAME, 'r')
        line = par_file.readline().strip()
        while line != "":
            idx = line.index(',')
            output[line[:idx]] = line[idx+1:]
            line = par_file.readline().strip()
        return output
    except Exception as e:
        pass


def read_variables():
    """
    Get the defined variable dictionary from mesoffset_directories.txt
    @returns:
        A dictionary where keys are variable names, and values are values
    """
    output = {}
    try:
        var_file = open(DIR_MCSRED+VAR_FILENAME, 'r')
        line = var_file.readline()
        while line != "":
            words = line.split()
            output[words[0]] = words[1]
            line = var_file.readline()
        var_file.close()
    except IOError:
        output["DATABASE"] = "../../MCSRED2/DATABASE"
    return output

#END

