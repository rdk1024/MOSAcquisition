#
# MESAnalyze.py -- a ginga plugin to help analyze data about a group of objects
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import math
import os
import sys
import time

# local imports
from util import mosplots
from util.mosplugin import MESPlugin

# ginga imports
from ginga.gw import Widgets, Viewers, Plot

# third-party imports
import numpy as np
from pyraf.iraf import geomap, INDEF



# constants
# the arguments passed in to the outer script
argv = sys.argv
fits_image = argv[1]
input_coo = argv[2]
output_dbs = argv[3]
log_file = argv[4]
if len(argv) > 5:
    output_res = argv[5][argv[5].rfind('=')+1:]
else:
    output_res = ""



class MESAnalyze(MESPlugin):
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
        # LocalPlugin constructor defines self.fv, self.fitsimage, self.logger;
        # MESPlugin constructor defines self.dc, self.canvas, and some fonts
        super(MESAnalyze, self).__init__(fv, fitsimage)
        
        # and some attributes
        self.data = self.read_input_file()
        self.active = np.ones(self.data.shape[0], dtype=np.bool)
        self.offset = (0, 0, 0)
        self.final_displays = {}
        
        # creates the list of plots that will go in the GUI
        self.plots = [mosplots.MOSPlot(logger=self.logger),
                      mosplots.MOSPlot(logger=self.logger)]
        
        # sets the mouse controls
        self.set_callbacks()
        
        
        
    def build_specific_gui(self, stack, orientation='vertical'):
        """
        Combine the GUIs necessary for this particular plugin
        Must be implemented for each MESPlugin
        @param stack:
            The stack in which each part of the GUI will be stored
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        """
        stack.add_widget(self.make_gui_3(orientation))
        stack.add_widget(self.make_gui_4(orientation))
    
    
    def make_gui_3(self, orientation='vertical'):
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
        lbl = Widgets.Label("Manage Residuals")
        lbl.set_font(self.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Look at the graphs. Remove any data with residuals "+
                     "greater than 1.0 or less than -1.0. Delete points by "+
                     "right clicking, and restore them by left-clicking. "+
                     "Click 'Next' below when the data is satisfactory.")
        exp.set_widget(txt)
        
        # now make an HBox to hold the main controls
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the next button shows the values
        btn = Widgets.Button("Next")
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
        gui.add_widget(Widgets.Label(""), stretch=True)
        return gui
    
    
    def make_gui_4(self, orientation='vertical'):
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
        lbl = Widgets.Label("Get Offset Values")
        lbl.set_font(self.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Enter the numbers you see below into the ANA window. dx "+
                     "and dy values are in pixels, and rotation value is in "+
                     "degrees. Values of less than 0.5 pixels and 0.01 "+
                     "degrees have been ignored. Click 'Exit' below when you "+
                     "are done.")
        exp.set_widget(txt)
        
        # make a frame for the results
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = Widgets.VBox()
        box.set_spacing(3)
        frm.set_widget(box)
        
        # make the three TextAreas to hold the final values
        for val in ("dx", "dy", "Rotate"):
            lbl = Widgets.Label(val+" =")
            lbl.set_font(self.header_font)
            box.add_widget(lbl)
            txt = Widgets.TextArea(editable=False)
            txt.set_font(self.title_font)
            box.add_widget(txt)
            self.final_displays[val] = txt
        
        btn = Widgets.Button("Exit")
        btn.add_callback('activated', self.exit_cb)
        btn.set_tooltip("Close Ginga")
        gui.add_widget(btn)
        
        # space gui appropriately and return it
        gui.add_widget(Widgets.Label(""), stretch=True)
        return gui
    
    
    def start(self):
        """
        Called when the plugin is invoked, right after build_gui()
        One of the required LocalPlugin methods
        """
        super(MESAnalyze, self).start()
        
        # adjust the cut levels to make the points easier to see
        self.fitsimage.get_settings().set(autocut_method='zscale')
        
        # set the initial status message
        self.fv.showStatus("Analyze and trim the data.")
        
        # initialize the plots
        self.delete_outliers()
        self.update_plots()
    
    
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
        Responds to the Next button in step 3 by displaying the offset values
        """
        self.stack.set_index(1)
        self.fv.showStatus("Read the MES Offset values!")
        self.set_callbacks()
        self.display_values()
        
        
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
        self.update_plots(idx)
    
    
    def update_plots(self, updated_index=None):
        """
        Graphs data on all plots and displays it
        @param updated_index:
            The index of the datum that changed. If none is provided, then all
            points will be updated
        @returns:
            The x and y residuals in numpy array form
        """
        # first, update the objects on the canvas
        if updated_index == None:
            for i in range(0, self.data.shape[0]):
                self.draw_obj_on_canvas(i)
        else:
            self.draw_obj_on_canvas(updated_index)
        
        # then record the new data
        self.overwrite_data(input_coo, self.data, self.active)
        
        # delete some files and call iraf.geomap
        try:
            os.remove(output_res)
        except OSError:
            pass
        try:
            geomap(input_coo, output_dbs, INDEF, INDEF, INDEF, INDEF,
                   fitgeom="rotate", results=output_res)
        except IOError:
            geomap("sbr_elaisn1rev_starmask.coo", "sbr_elaisn1rev_starmask.dbs",
                   xmin=INDEF, xmax=INDEF, ymin=INDEF, ymax=INDEF,
                   fitgeom="rotate", results="sbr_elaisn1rev_starholemask.res")
        
        # use its results to calculate some stuff
        xref = self.data[:, 0]
        yref = self.data[:, 1]
        xin  = self.data[:, 2]
        yin  = self.data[:, 3]
        self.offset = self.get_transformation(output_dbs)
        xcalc, ycalc = self.transform(xin, yin, self.offset)
        xres = xcalc - xref
        yres = ycalc - yref
        
        # graph residual data on the plots
        self.plots[0].residual(xref, xres, self.active, var_name="X")
        self.plots[1].residual(yref, yres, self.active, var_name="Y")
        
        return xres, yres
        
        
                
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
            self.canvas.add(self.dc.Point(xref, yref, radius=30,
                                          color='blue', style='plus'),
                            tag=str(idx)+'ref')
            self.canvas.add(self.dc.Point(xin,  yin,  radius=30,
                                          color='green', style='plus'),
                            tag=str(idx)+'in')
        else:
            self.canvas.add(self.dc.Point(xref, yref, radius=30,
                                          color='grey', style='cross'),
                            tag=str(idx)+'ref')
            self.canvas.add(self.dc.Point(xin,  yin,  radius=30,
                                          color='grey', style='cross'),
                            tag=str(idx)+'in')
                            
                            
    def display_values(self):
        """
        Shows the final MES Offset values on the screen, based on self.offset
        """
        # collect values from other sources
        xcenter = 1024.0
        ycenter = 1750.0
        xshift, yshift, thetaD = self.offset
        thetaR = math.radians(thetaD)
        
        # calculate dx and dy (no idea what all this math is)
        dx = -yshift + xcenter*math.sin(thetaR) + ycenter*(1-math.cos(thetaR))
        dy = xshift + xcenter*(math.cos(thetaR)-1) + ycenter*math.sin(thetaR)
        # normalize thetaD to the range [-180, 180)
        thetaD = (thetaD+180)%360 - 180
        
        # ignore values with small absolute values
        if abs(dx) < 0.5:
            dx = 0
        if abs(dy) < 0.5:
            dy = 0
        if abs(thetaD) < 0.01:
            thetaD = 0
        
        # then display all values
        self.final_displays["dx"].set_text("{:,.1f} pix".format(dx))
        self.final_displays["dy"].set_text("{:,.1f} pix".format(dy))
        self.final_displays["Rotate"].set_text(u"{:,.3f}\u00B0".format(thetaD))
        
        # now log it!
        self.write_to_log(dx, dy, thetaD)
        
    
    def write_to_log(self, *args):
        """
        Writes important information to log_file
        @param args:
            The values to be written to log - must be (dx, dy, rotate)
        """
        log = open(log_file, 'a')
        log.write(time.strftime("%a %b %d %H:%M:%S %Z %Y\n"))
        log.write(("dx = {:6,.1f} (pix) dy = {:6,.1f} (pix) "+
                   "rotate = {:7,.3f} (degree) \n").format(*args))
        log.close()

        
    def delete_outliers(self):
        """
        Removes any data points with residuals of absolute values greater than 1
        """
        active = self.active
        
        xres, yres = self.update_plots()
        residual_mag = np.hypot(xres, yres)*active
        
        # as long as some residuals are out of bounds,
        while np.any(residual_mag > 1):
            # delete the point with the worst residual
            idx = np.argmax(residual_mag)
            active[idx] = False
            
            xres, yres = self.update_plots()
            residual_mag = np.hypot(xres, yres)*active
    
    
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
    
    
    
    @staticmethod
    def read_input_file():
        """
        Read the COO file and return the data within as a numpy array
        @returns:
            A list of tuples of floats representing (x_in, y_in, x_out, y_out)
        """
        # define variables
        val_list = []
        
        # try to open the file
        try:
            coo = open(input_coo, 'r')
        except IOError:
            try:
                coo = open("sbr_elaisn1rev_starmask.coo")
            except IOError:
                return np.array([[0., 0., 0., 0.]])
        
        # now parse it!
        line = coo.readline()
        while line != "":
            # for each line, get the important values and save them in val_list
            vals = [float(word) for word in line.split()]
            val_list.append(vals)
            line = coo.readline()
        
        coo.close()
        return np.array(val_list)

    
    @staticmethod
    def overwrite_data(filename, new_data, active):
        """
        Writes the new data to the filename
        @param filename:
            The name of a .coo file
        @param new_data:
            A numpy array
        @active
            A boolean array specifying which of the data are valid
        """
        coo = open(filename, 'w')
        data = new_data[np.nonzero(active)]
        for row in data:
            for datum in row:
                coo.write(str(datum))
                coo.write(' ')
            coo.write('\n')
        coo.close()
        
    
    @staticmethod
    def get_transformation(filename):
        """
        Read the DBS file written by iraf.geomap and return the useful data within
        @param filename:
            The str name of the file in which the transformation info can be found
        @returns:
            A tuple of three floats: (x_shift, y_shift, rotation in degrees)
        """
        try:
            dbs = open(filename, 'r')
        except IOError:
            try:
                dbs = open("sbr_elaisn1rev_starmask.dbs", 'r')
            except IOError:
                return (0., 0., 0.)
        
        # now skip to and read the important bits
        lines = dbs.readlines()
        dbs.close()
        x_shift = float(lines[-21].split()[1])
        y_shift = float(lines[-20].split()[1])
        x_rot = float(lines[-17].split()[1])
        y_rot = float(lines[-16].split()[1])
        return (x_shift, y_shift, (x_rot+y_rot)/2)
        
    
    @staticmethod
    def transform(x, y, trans):
        """
        Applies the given transformation to the given points
        @param x:
            A numpy array of x positions
        @param y:
            A numpy array of y positions
        @param trans:
            A tuple of floats: (x_shift, y_shift, rotation in degrees)
        @returns:
            A tuple of the new x value array and the new y value array
        """
        xshift, yshift, thetaD = trans
        thetaR = math.radians(thetaD)
        newX = (x - xshift)*math.cos(thetaR) - (y - yshift)*math.sin(thetaR)
        newY = (x - xshift)*math.sin(thetaR) + (y - yshift)*math.cos(thetaR)
        return newX, newY

#END

