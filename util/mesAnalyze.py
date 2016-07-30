#
# mesAnalyze.py -- a class to help analyze data about a group of objects
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import math
import os
import sys

# local imports
from util import mosPlots

# ginga imports
from ginga.gw import Widgets, Viewers, Plot

# third-party imports
import numpy as np



class MESAnalyze(object):
    """
    A class that graphs some data about some objects' positions and
    asks the user to modify the data if necessary. Intended for use as part of
    the MOS Acquisition software for aligning MOIRCS.
    """
    
    def __init__(self, manager):
        """
        Class constructor
        @param manager:
            The MESOffset plugin that this class communicates with
        """
        manager.initialise(self)
    
    
    
    def start(self, star_pos, hole_pos, next_step=None):
        """
        Analyze the data from MESLocate
        @param star_pos:
            A three column (x,y,r) array specifying the star locations and sizes
        @param hole_pos:
            A three column (x,y,r) array specifying the hole locations and sizes
        @param rootname:
            The string that will be used for all temporary filenames
        @param next_step:
            The function to call when this process is done
        """
        # set attributes
        self.data, self.active = self.parse_data(star_pos, hole_pos)
        self.next_step = next_step
        
        # set the mouse controls
        self.set_callbacks()
        
        # adjust the cut levels to make the points easier to see
        self.fitsimage.get_settings().set(autocut_method='stddev')
        
        # initialize the plots
        self.delete_outliers()
        
        # show the GUI
        self.manager.go_to_gui('plots')
    
    
    def set_callbacks(self, step=3):
        """
        Assign all necessary callbacks to the canvas for the current step
        """
        canvas = self.canvas
        
        # clear all existing callbacks first
        for cb in ('cursor-down', 'cursor-up',
                    'panset-down', 'panset-up',
                    'draw-down', 'draw-up'):
            canvas.clear_callback(cb)
        
        # the only callbacks are for right-click and left-click
        if step == 3:
            canvas.add_callback('cursor-down', self.set_active_cb, True)
            canvas.add_callback('draw-down', self.set_active_cb, False)
    
    
    def step4_cb(self, *args):
        """
        Respond to the Next button in step 3 by displaying the offset values
        """
        self.set_callbacks(step=4)
        self.manager.go_to_gui('values')
        self.display_values()
        
        
    def finish_cb(self, *args):
        """
        Respond to the 'Finish' button in step 4 by finishing up
        """
        self.canvas.delete_all_objects()
        if self.next_step != None:
            self.next_step()
        
        
    def set_active_cb(self, _, __, x, y, val):
        """
        Respond to right click by deleting the datum nearest the cursor
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
    
    
    def update_plots(self):
        """
        Calculates self.transformation, graph data on all plots, and display it
        @returns:
            The x and y residuals in numpy array form
        """
        data = self.data[np.nonzero(self.active)]
        
        # calculate the optimal transformation from the input data
        centroid = np.mean(data, axis=0)
        data = data - centroid
        p_i = np.asmatrix(data[:, 0:2])
        p_f = np.asmatrix(data[:, 2:4])
        u, s, v = np.linalg.svd(p_i.T * p_f)
        rot_mat = u * v
        shift =  centroid[2:4] - centroid[0:2]*rot_mat
        theta = np.mean([math.acos(rot_mat[0,0]), math.asin(rot_mat[1,0])])
        self.transformation = (shift[0,0], shift[0,1], theta)
        
        # use its results to calculate some stuff
        xref = self.data[:, 0]
        yref = self.data[:, 1]
        xin  = self.data[:, 2]
        yin  = self.data[:, 3]
        xcalc, ycalc = self.transform(xin, yin, self.transformation)
        xres = xcalc - xref
        yres = ycalc - yref
        
        # graph residual data on the plots
        self.plots[0].residual(xref, xres, self.active, var_name="X")
        self.plots[1].residual(yref, yres, self.active, var_name="Y")
        
        # update the vectors on the canvas, as well
        for i in range(0, self.data.shape[0]):
            self.draw_vector_on_canvas(xref[i], yref[i], xres[i], yres[i], i)
        
        return xres, yres
    
    
    def draw_vector_on_canvas(self, xref, yref, xres, yres, idx):
        """
        Draws the residual vector at the given point on the canvas
        @param xref:
            The float observed x coordinate of this object
        @param yref:
            The float observed y coordinate of this object
        @param xres:
            The float residual x coordinate of this object
        @param yres:
            The float residual y coordinate of this object
        @param idx:
            The index of this object
        """
        # first calculate the endpoints of the vector
        startX = xref
        startY = yref
        endX = startX + 300*xres
        endY = startY + 300*yres
        magnitude = math.hypot(xres, yres)
        
        # determine the color based on activity and magnitude
        if not self.active[idx]:
            color = 'grey'
        elif magnitude <= 0.5:
            color = 'green'
        elif magnitude <= 1.0:
            color = 'yellow'
        else:
            color = 'red'
        
        # delete the old vector
        self.canvas.delete_object_by_tag(str(idx))
        
        # and draw in the new one
        self.canvas.add(self.dc.CompoundObject(
                                self.dc.Line(startX, startY, endX, endY,
                                             color=color, arrow='end',
                                             showcap=True, alpha = 0.7),
                                self.dc.Text((startX+endX)/2, (startY+endY)/2,
                                             "{:.1f}p".format(magnitude),
                                             color=color)),
                        tag=str(idx))
    
    
    def display_values(self):
        """
        Shows the final MES Offset values on the screen, based on
        self.transformation
        """
        # collect values from other sources
        xcenter = 1024.0
        ycenter = 1750.0
        xshift, yshift, thetaR = self.transformation
        thetaD = math.degrees(thetaR)
        
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
        self.final_displays["dx"].set_text("{:,.2f} pix".format(dx))
        self.final_displays["dy"].set_text("{:,.2f} pix".format(dy))
        self.final_displays["Rotate"].set_text(u"{:,.4f}\u00B0".format(thetaD))
        self.offset = (dx, dy, thetaD)

        
    def delete_outliers(self):
        """
        Remove any data points with residuals of absolute values greater than 1.
        Also updates the plots
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
        
        
    def gui_list(self, orientation='vertical'):
        """
        Combine the GUIs necessary for the MESAnalyze part of the plugin
        Must be implemented for each MESPlugin
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A list of Widgets that will be placed in a stack
        """
        return [('plots',  self.make_gui_plot(orientation)),
                ('values', self.make_gui_vals(orientation))]
    
    
    def make_gui_plot(self, orientation='vertical'):
        """
        Construct a GUI for the third step: viewing the plots
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
        lbl.set_font(self.manager.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.normal_font)
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
        
        # put in a spacer
        box.add_widget(Widgets.Label(""), stretch=True)
        
        # now a framed vbox to put the plots in
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = Widgets.VBox()
        box.set_spacing(3)
        frm.set_widget(box)
        
        # finally, add both plots in frames
        self.plots = []
        for i in range(2):
            self.plots.append(mosPlots.MOSPlot(logger=self.logger))
            fig = Plot.PlotWidget(self.plots[i])
            box.add_widget(fig)
        
        return gui
    
    
    def make_gui_vals(self, orientation='vertical'):
        """
        Construct a GUI for the fourth step: getting the offset values
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
        lbl.set_font(self.manager.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.normal_font)
        txt.set_text("Enter the numbers you see below into the ANA window. dx "+
                     "and dy values are in pixels, and rotation value is in "+
                     "degrees. Values of less than 0.5 pixels and 0.01 "+
                     "degrees have been ignored. Click 'Finish' below when "+
                     "you are done.")
        exp.set_widget(txt)
        
        # make a frame for the results
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = Widgets.VBox()
        box.set_spacing(3)
        frm.set_widget(box)
        
        # make the three TextAreas to hold the final values
        self.final_displays = {}
        for val in ("dx", "dy", "Rotate"):
            lbl = Widgets.Label(val+" =")
            lbl.set_font(self.manager.header_font)
            box.add_widget(lbl)
            txt = Widgets.TextArea(editable=False)
            txt.set_font(self.manager.title_font)
            box.add_widget(txt)
            self.final_displays[val] = txt
        
        btn = Widgets.Button("Finish")
        btn.add_callback('activated', self.finish_cb)
        btn.set_tooltip("Close Ginga")
        gui.add_widget(btn)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
    
    
    
    @staticmethod
    def parse_data(data1, data2):
        """
        Read the data and return it in a more useful format: a four-columned
        numpy array with the nans removed
        @param data1:
            The first input array: the star locations and sizes, or ref values
        @param data2:
            The second input array: the hole locations and sizes, or in values
        @returns:
            A four-column array representing the star positions and hole
            positions, and a 1-dimensional array of Trues
        """
        data = np.hstack((data2[:,:2], data1[:,:2]))
        real_idx = np.logical_not(np.any(np.isnan(data), axis=1))
        data = data[np.nonzero(real_idx)]
        
        return data, np.ones(data.shape[0], dtype=bool)
    
    
    @staticmethod
    def get_transformation(filename):
        """
        Read the DBS file written by iraf.geomap and return the useful data within
        @param filename:
            The str name of the file in which the transformation info can be found
        @returns:
            A tuple of three floats: (x_shift, y_shift, rotation in degrees)
            or None if no transformation was found
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
        try:
            x_shift = float(lines[-21].split()[1])
            y_shift = float(lines[-20].split()[1])
            x_rot = float(lines[-17].split()[1])
            y_rot = float(lines[-16].split()[1])
        except IndexError:
            return None
        
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
            or NaN, NaN if trans was None
        """
        if trans == None:
            return float('NaN'), float('NaN')
        
        xshift, yshift, thetaR = trans
        newX = (x - xshift)*math.cos(thetaR) - (y - yshift)*math.sin(thetaR)
        newY = (x - xshift)*math.sin(thetaR) + (y - yshift)*math.cos(thetaR)
        return newX, newY

#END

