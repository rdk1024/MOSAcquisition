#
# MESAnalyze.py -- a ginga plugin to help analyze data about a group of objects
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import math
import sys

# local imports
import mosplots

# ginga imports
from ginga import GingaPlugin
from ginga.gw import Widgets, Viewers, Plot
from ginga.RGBImage import RGBImage

# third-party imports
import numpy as np



# constants
# the arguments passed in to the outer script
argv = sys.argv



class MESAnalyze(GingaPlugin.LocalPlugin):
    """
    A custom LocalPlugin for ginga that takes some data about some objects'
    positions, graphs them, and asks the user to modify the data if necessary.
    Intended for use as part of the MOS Acquisition software for aligning
    MOIRCS.
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
        # superclass constructor defines self.fv, self.fitsimage, and self.logger:
        super(MESAnalyze, self).__init__(fv, fitsimage)
        fv.set_titlebar("MOIRCS Acquisition")

        # initializes some class constants:
        self.title_font = self.fv.getFont('sansFont', 18)
        self.body_font = self.fv.getFont('sansFont', 10)
        
        # and some attributes
        self.data = readCOO()
        
        # creates the list of plots that will go in the GUI
        self.plots = create_plot_list(self.logger)
        
        # now sets up the ginga.canvas.types.layer.DrawingCanvas self.canvas,
        # which is necessary to draw on the image:
        self.dc = fv.get_draw_classes()
        self.canvas = self.dc.DrawingCanvas()
        self.canvas.enable_draw(False)
        self.set_callbacks()
        self.canvas.set_surface(self.fitsimage)
        self.canvas.register_for_cursor_drawing(self.fitsimage)
        self.canvas.name = 'MOSA-canvas'
        
        # * NOTE: self.drag_history is a list of lists, with one list for each
        #       object; each inner list contains tuples of the form
        #       (float x1, float y1, float x2, float y2, string ['mask'/'crop'])
        
        
        
    def set_callbacks(self):
        """
        Assigns all necessary callbacks to the canvas for the current step
        """
        canvas = self.canvas
        step = self.get_step()
        
        # clear all existing callbacks first
        for cb in ('cursor-down', 'cursor-up',
                    'panset-down', 'panset-up', 'draw-up'):
            canvas.clear_callback(cb)
        
        # for step three, the only callbacks are for right-click and left-click
        if step == 3:
            canvas.add_callback('draw-down', self.step4_cb)
    
    
    def step4_cb(self, *args):
        """
        Responds to the Finish button in step 3 by ending the program
        """
        self.stack.set_index(1)
        self.fv.showStatus("Read the MES Offset values!")
        self.set_callbacks()
        
        
    def finish_cb(self, *args):
        """
        Responds to the Exit button in step 4 by closing ginga
        """
        self.close()
        self.fv.quit()
    
    
    def update_plots(self):
        """
        Graphs data on all plots and displays it
        """
        for plot in self.plots:
            try:
                plot.set_data(process_data(self.data))
            except TypeError:
                self.fv.showStatus("Could not locate one or more objects")
                return
            
        self.plots[0].plot_x_y()
        self.plots[1].plot_residual()
        
        
    def get_step(self):
        """
        Deduces which step we are on
        @returns:
            An int: 3 for step 3 and 4 for step 4
        """
        try:
            return self.stack.get_index()+3
        except AttributeError:
            return 3
        
        
    def make_gui3(self, orientation='vertical'):
        """
        Construct a GUI for the third step: viewing the graph
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # create a label to title this step
        lbl = Widgets.Label("Step 3")
        lbl.set_font(self.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Look at the graphs. If a datum seems out of place, or "+
                     "wrongfully deleted, right-click it to delete it or left-"+
                     "click to restore it. Click 'Finish' below or press 'Q' "+
                     "once the data is satisfactory.")
        exp.set_widget(txt)
        
        # now make an HBox to hold the main controls
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the finish button ends the program
        btn = Widgets.Button("Finish")
        btn.add_callback('activated', self.step4_cb)
        btn.set_tooltip("Get the MES Offset values!")
        box.add_widget(btn)
        
        # now a framed vbox to put the plots in
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = Widgets.VBox()
        box.set_spacing(3)
        frm.set_widget(box)
        
        # finally, add all three plots in frames
        for graph in self.plots:
            plt = Plot.PlotWidget(graph)
            graph.set_callback('cursor-down', lambda w: self.close())
            box.add_widget(plt)
        
        # space gui appropriately and return it
        gui.add_widget(Widgets.Label(""), stretch=1)
        return gui
    
    
    def make_gui4(self, orientation='vertical'):
        """
        Construct a GUI for the fourth step: getting the offset
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # create a label to title this step
        lbl = Widgets.Label("Step 3")
        lbl.set_font(self.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Enter the numbers you see below into your other computer.")
        exp.set_widget(txt)
        
        # make the three TextAreas to hold the final values
        for i in range(3):
            txt = Widgets.TextArea(wrap=True, editable=False)
            txt.set_font(self.title_font)
            txt.set_text("Value {}:\n42".format(i))
            gui.add_widget(txt)
        
        btn = Widgets.Button("Exit")
        btn.add_callback('activated', self.finish)
        gui.add(btn)
        
        # space gui appropriately and return it
        gui.add_widget(Widgets.Label(""), stretch=1)
        return gui
        

    def build_gui(self, container):
        """
        Called when the plugin is invoked; sets up all the components of the GUI
        One of the required LocalPlugin methods
        @param container:
            The widget.VBox this GUI will be added into
        """
        # create the outer Box that will hold the stack of GUIs and close button
        out, out_wrapper, orientation = Widgets.get_oriented_box(container)
        out.set_border_width(4)
        out.set_spacing(3)
        container.add_widget(out_wrapper)
        
        # the rest depends on which step we are on
        stk = Widgets.StackWidget()
        stk.add_widget(self.make_gui3(orientation))
        stk.add_widget(self.make_gui4(orientation))
        out.add_widget(stk)
        self.stack = stk    # this stack is important, so save it for later

        # end is an HBox that comes at the very end, after the rest of the gui
        end = Widgets.HBox()
        end.set_spacing(3)
        out.add_widget(end)
            
        # throw in a close button at the very end, just in case
        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        end.add_widget(btn)
        end.add_widget(Widgets.Label(''), stretch=True)
        
    
    def close(self):
        """
        Called when the plugin is closed
        One of the required LocalPlugin methods
        @returns:
            True. I'm not sure why.
        """
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True


    def start(self):
        """
        Called when the plugin is invoked, right after build_gui()
        One of the required LocalPlugin methods
        """
        # set the autocut to make things easier to see
        self.fitsimage.get_settings().set(autocut_method='stddev')
        
        # set the initial status message
        self.fv.showStatus("Analyze and trim the data.")
        
        # stick our own canvas on top of the fitsimage canvas
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag='main-canvas')
        
        # clear the canvas
        self.canvas.delete_all_objects()


    def pause(self):
        """
        Called when the plugin is unfocused
        One of the required LocalPlugin methods
        """
        self.canvas.ui_setActive(False)


    def resume(self):
        """
        Called when the plugin is refocused
        One of the required LocalPlugin methods
        """
        # activate the GUI
        self.canvas.ui_setActive(True)


    def stop(self):
        """
        Called when the plugin is stopped
        One of the required LocalPlugin methods
        """
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag('main-canvas')
        except:
            pass
        self.canvas.ui_setActive(False)


    def redo(self):
        """
        Called whenever a new image is loaded
        One of the required LocalPlugin methods
        """
        pass


    def __str__(self):
        return "MESAnalyze"
    
    
def create_plot_list(logger=None):
    """
    Create a list of two ginga.util.plots.Plot objects for step 3 of mesoffset1
    @param logger:
        A Logger object to pass into the new Viewers
    @param obj_list:
        A list of float tuples representing the relative position of each object
    @param offset:
        An optional float tuple to offset all object positions by
    @returns:
        A list of plots.Plot objects
    """
    output = [mosplots.ObjXYPlot(logger=logger),
              mosplots.YResidualPlot(logger=logger)]
    return output


def readCOO():
    """
    Read the COO file and return the data within as a list of float tuples
    @returns:
        A list of tuples of floats representing (x_in, y_in, x_out, y_out)
    """
    # define variables
    val_list = []
    
    # try to open the file
    try:
        sbr = open(argv[1], 'r')
    except IOError:
        try:
            sbr = open("sbr_elaisn1rev_starmask.coo")
        except IOError:
            return [(0, 0, 0, 0)]
    
    # now parse it!
    line = sbr.readline()
    while line != "":
        # for each line, get the important values and save them in val_list
        vals = [float(word) for word in line.split()]
        val_list.append(vals)
        line = sbr.readline()
        
    return val_list

#END

