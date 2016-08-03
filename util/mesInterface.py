#
# mesInterface.py -- a class that creates a nice GUI
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
from time import strftime

# ginga imports
from ginga.gw import Widgets



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
        
    
    
    def start_process_cb(self, _, idx):
        """
        Take the parameters from the gui and begin mesoffset{idx}
        @param idx:
            The index for the process we are going to start - 0, 1, 2, or 3
        """
        self.log("Starting MES Offset {}...".format(idx))
        try:
            self.update_parameters(self.get_value[idx])
        except NameError as e:
            self.log("NameError: "+str(e), level='e')
            return
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
        Scan all strings for variables
        @param getters:
            The dictionary of getter methods for parameter values
        @raises NameError:
            If one of the values contains an undefined variable
        """
        new_params = {}
        for key, get_val in getters.items():
            if type(get_val()) in (str, unicode):
                value = process_filename(get_val(), self.manager.variables)
            else:
                value = get_val()
            new_params[key] = value
        self.manager.database.update(new_params)
    
    
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
    
    
    def wait(self, idx, next_step=None):
        """
        Go to the 'wait' gui at this index to get more info from the user, and
        prepare to execute the next step.
        @param idx:
            The index of the process that this interrupts
        @param next_step:
            The function to be called when the 'Go!' button is pressed
        """
        if idx == 1:
            self.set_defaults(4)
        elif idx == 3:
            self.set_defaults(5)
        self.manager.go_to_gui('wait '+str(idx))
        self.resume_mesoffset[idx] = next_step
    
    
    def resume_process_cb(self, _, idx):
        """
        Take the parameters from the intermediate gui and resume
        @param idx:
            The index for the process we must resume - 1 or 3
        """
        try:
            if idx == 1:
                self.update_parameters(self.get_value[4])
            elif idx == 3:
                self.update_parameters(self.get_value[5])
        except NameError as e:
            self.log("NameError: "+str(e), level='e')
            return
        self.resume_mesoffset[idx]()
    
    
    def check_locations(self, data, last_step=None, next_step=None):
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
        self.manager.go_to_gui('check')
    
    
    def execute_cb(self, _, name):
        """
        A little method I wrote to manage callbacks for check_locations
        @param name:
            The name of the method to run
        """
        self.canvas.delete_all_objects()
        if name == 'last_step':
            self.last_step()
        elif name == 'next_step':
            self.next_step()
    
    
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
            self.manager.go_to_gui('error')
        else:
            self.logger.critical(text.strip())
            self.log_textarea.append_text("CRIT: "+text+"\n", autoscroll=True)
            self.err_textarea.set_text("CRITICAL!\n"+text)
            self.manager.go_to_gui('error')
    
    
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
                ('check',  self.make_gui_check(orientation)),
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
        txt.set_font(self.manager.normal_font)
        txt.set_text("Use the widgets below to specify the parameters for "+
                     name+". Hover over each one to get a description of "+
                     "what it means. When you are finished, press the 'Go!' "+
                     "button, which will begin "+name+".")
        exp.set_widget(txt)
        
        # chose the params
        if idx == 0:
            params = self.manager.params_0
        elif idx == 1:
            params = self.manager.params_1
        elif idx == 2:
            params = self.manager.params_2
        elif idx == 3:
            params = self.manager.params_3

        # create a grid to group the different controls
        frm = Widgets.Frame(name)
        gui.add_widget(frm)
        grd, getters, setters = build_control_layout(params)
        self.get_value.append(getters)
        self.set_value.append(setters)
        frm.set_widget(grd)
        
        # create a box for the defined variables
        frm = Widgets.Frame("Defined Variables")
        gui.add_widget(frm)
        box = build_dict_labels(self.manager.variables)
        frm.set_widget(box)
        
        # the go button will go in a box
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the go button is important
        btn = Widgets.Button("Go!")
        btn.add_callback('activated', self.start_process_cb, idx)
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
        txt.set_font(self.manager.normal_font)
        txt.set_text("Verify parameters in order to continue "+name+", using "+
                     "the widgets below. When you are finished and the "+
                     "specified files are ready for analysis, press the 'Go!' "+
                     "button, which will resume "+name+".")
        exp.set_widget(txt)
        
        # chose the params
        if idx == 1:
            params = self.manager.params_1p5
        elif idx == 3:
            params = self.manager.params_3p5
        
        # create a grid to group the different controls
        frm = Widgets.Frame()
        gui.add_widget(frm)
        grd, getters, setters = build_control_layout(params)
        self.get_value.append(getters)  # NOTE that these getters and setters
        self.set_value.append(setters)  # will have different indices than idx
        frm.set_widget(grd)
        
        # create a box for the defined variables
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = build_dict_labels(self.manager.variables)
        frm.set_widget(box)
        
        # the go button will go in a box
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the go button is important
        btn = Widgets.Button("Go!")
        btn.add_callback('activated', self.resume_process_cb, idx)
        btn.set_tooltip("Continue "+name+" with the given parameters")
        box.add_widget(btn)
        box.add_widget(Widgets.Label(''), stretch=True)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
    
    
    def make_gui_check(self, orientation='vertical'):
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
        txt.set_font(self.manager.normal_font)
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
        txt.set_font(self.manager.mono_font)
        gui.add_widget(txt)
        self.results_textarea = txt
        
        # now make an HBox for the controls
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the Try Again button goes to the last step
        btn = Widgets.Button("Try Again")
        btn.add_callback('activated', self.execute_cb, 'last_step')
        btn.set_tooltip("Go back and take these measurements again")
        box.add_widget(btn)
        
        # the Start Over button goes to the main menu
        btn = Widgets.Button("Start Over")
        btn.add_callback('activated', lambda w: self.manager.go_to_gui('epar'))
        btn.set_tooltip("Return to the main menu to edit your parameters")
        box.add_widget(btn)
        
        # the Continue button goes to the next step
        btn = Widgets.Button("Continue")
        btn.add_callback('activated', self.execute_cb, 'next_step')
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
        # the only thing here is a gigantic text box
        scr = Widgets.ScrollArea()
        txt = Widgets.TextArea(wrap=False, editable=False)
        txt.set_font(self.manager.body_font)
        self.log_textarea = txt
        scr.set_widget(txt)
        
        return scr
    
    
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
        lbl.set_font(self.manager.header_font)
        gui.add_widget(lbl)
        
        # now for the error box itself
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.body_font)
        gui.add_widget(txt)
        self.err_textarea = txt
        
        # finish off with a box of important controls at the end
        box = Widgets.HBox()
        gui.add_widget(box)
        
        # in it is a back button
        btn = Widgets.Button("Return to Menu")
        btn.add_callback('activated', lambda w: self.manager.go_to_gui('epar'))
        btn.set_tooltip("Correct the error and try again")
        box.add_widget(btn)
        box.add_widget(Widgets.Label(''), stretch=True)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui



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
            wdg.set_text('')
            getters[name] = wdg.get_text
            setters[name] = wdg.set_text
        elif param['type'] == 'number':
            wdg = Widgets.SpinBox()
            wdg.set_limits(0, 99999999)
            wdg.set_value(0)
            getters[name] = wdg.get_value
            setters[name] = wdg.set_value
        elif param['type'] == 'choice':
            wdg = Widgets.ComboBox()
            for option in param['options']:
                wdg.append_text(option)
            wdg.set_index(0)
            getters[name] = wdg.get_index
            setters[name] = wdg.set_index
        elif param['type'] == 'boolean':
            wdg = Widgets.CheckBox()
            wdg.set_state(True)
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


def build_dict_labels(dictionary):
    """
    Build a gui that displays the dictionary keys and values
    @param dictionary:
        A dict populated with str keys and str values
    @returns:
        A Widget object that displays the contents of the dictionary
    """
    grd = Widgets.GridBox(rows=len(dictionary), columns=2)
    grd.set_spacing(3)
    for i, key in enumerate(dictionary):
        lbl1 = Widgets.Label("$"+key+":",     halign='right')
        lbl2 = Widgets.Label(dictionary[key], halign='left')
        grd.add_widget(lbl1, i, 0)
        grd.add_widget(lbl2, i, 1)
    return grd


def process_filename(filename, variables):
    """
    Take a filename and modifies it to account for any variables
    @param filename:
        The input filename to be processed
    @param variables:
        The dictionary of variable names to variable values
    @returns:
        The updated filename
    @raises NameError:
        If there is an undefined variable
    """
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

#END

