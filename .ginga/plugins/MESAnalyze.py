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
from util import mosplots

# ginga imports
from ginga import GingaPlugin
from ginga.gw import Widgets, Viewers, Plot

# third-party imports
import numpy as np



# constants
# the arguments passed in to the outer script
argv = sys.argv
# usage: %prog( FITS_filename, input_coo_filename, output_coo_filename )



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
        self.active = np.ones(self.data.shape[0], dtype=np.bool)
        
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
            canvas.add_callback('cursor-down', self.set_active_cb, True)
            canvas.add_callback('draw-down', self.set_active_cb, False)
    
    
    def step4_cb(self, *args):
        """
        Responds to the Finish button in step 3 by displaying the offset values
        """
        # write the ammended data back into coo
        coo = open(argv[2], 'w')
        for i in range(self.data.shape[0]):
            if self.active[i]:
                for j in range(self.data.shape[1]):
                    coo.write(str(self.data[i, j]))
                    coo.write(' ')
                coo.write('\n')
        
        # then move on to step 4
        self.stack.set_index(1)
        self.fv.showStatus("Read the MES Offset values!")
        self.set_callbacks()
        
        
    def exit_cb(self, *args):
        """
        Responds to the Exit button in step 4 by closing ginga
        """
        self.close()
        self.fv.quit()
        
        
    def set_active_cb(self, _, __, x, y, val):
        """
        Responds to right click by deleting the datum nearest the cursor
        @param val:
            The new active value for the point - should be boolean
        @param x:
            The x coordinate of the click
        @param y:
            The y coordinate of the click
        """
        distance_from_click = np.hypot(self.data[:,0] - x, self.data[:,1] - y)
        idx = np.argmin(distance_from_click)
        self.active[idx] = val
        self.update_plots()
    
    
    def update_plots(self, updated_index=None):
        """
        Graphs data on all plots and displays it
        @param updated_index:
            The index of the datum that changed. If none is provided, then all
            points will be updated
        """
        # graph residual data on the plots
        self.plots[0].x_residual(self.data)
        self.plots[1].y_residual(self.data)
        
        # show the object position(s) on the canvas
        if updated_index == None:
            for i in range(0, self.data.shape[0]):
                self.draw_obj_on_canvas(i)
        else:
            self.draw_obj_on_canvas(updated_index)
        
                
    def draw_obj_on_canvas(self, idx):
        """
        Draws the point at the given index on the canvas
        @param idx:
            The index of the datum to be drawn
        """
        # delete the corresponding points
        self.canvas.delete_objects_by_tag([str(idx)+'ref', str(idx)+'in'])
        
        # then draw the new one
        xref, yref, xin, yin = self.data[idx, :]
        # color depends on whether this object is active or not
        if self.active[idx]:
            self.canvas.add(self.dc.Point(xref, yref, 30, color='blue'),
                            tag=str(idx)+'ref')
            self.canvas.add(self.dc.Point(xin,  yin,  30, color='green'),
                            tag=str(idx)+'in')
        else:
            self.canvas.add(self.dc.Point(xref, yref, 30, color='grey'),
                            tag=str(idx)+'ref')
            self.canvas.add(self.dc.Point(xin,  yin,  30, color='grey'),
                            tag=str(idx)+'in')
        
        
        
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
        btn.add_callback('activated', self.exit_cb)
        gui.add_widget(btn)
        
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
        
        # initialize the plots
        self.update_plots()


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
    @param data:
        The numpy array from which this is to read
    @param offset:
        An optional float tuple to offset all object positions by
    @returns:
        A list of plots.Plot objects
    """
    output = []
    for i in range(2):
        output.append(mosplots.MOSPlot(logger=logger))
    return output


def readCOO():
    """
    Read the COO file and return the data within as a numpy array
    @returns:
        A list of tuples of floats representing (x_in, y_in, x_out, y_out)
    """
    # define variables
    val_list = []
    
    # try to open the file
    try:
        coo = open(argv[2], 'r')
    except IOError:
        try:
            coo = open("sbr_elaisn1rev_starmask.coo")
        except IOError:
            return np.array([[0, 0, 0, 0]])
    
    # now parse it!
    line = coo.readline()
    while line != "":
        # for each line, get the important values and save them in val_list
        vals = [float(word) for word in line.split()]
        val_list.append(vals)
        line = coo.readline()
        
    return np.array(val_list)

#END

