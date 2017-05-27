#
# mesAnalyze.py -- a class to help analyze data about a group of objects
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
from __future__ import absolute_import
import math

# ginga imports
from ginga.gw import Widgets, Plot
from ginga.util import plots

# third-party imports
import numpy as np
from six.moves import range



# constants
VALUE_NAMES = (("dX","pix"), ("dY","pix"), ("dPA",u"\u00B0"))



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
            A 2-3 column (x,y[,r]) array specifying the star locations and sizes
        @param hole_pos:
            A 2-3 column (x,y[,r]) array specifying the hole locations and sizes
        @param rootname:
            The string that will be used for all temporary filenames
        @param next_step:
            The function to call when this process is done
        """
        # set attributes
        self.data, self.active = parse_data(star_pos, hole_pos)
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
        self.manager.clear_canvas()
        
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
    
    
    def set_active_cb(self, _, __, x, y, val):
        """
        Respond to a right or left click on the main ImageViewer by altering the
        datum nearest the cursor
        @param x:
            The x coordinate of the click
        @param y:
            The y coordinate of the click
        @param val:
            The new active value for the point - should be boolean
        """
        distance_from_click = np.hypot(self.data[:,0] - x, self.data[:,1] - y)
        idx = np.argmin(distance_from_click)
        self.active[idx] = val
        self.update_plots()
    
    
    def toggle_active_x_cb(self, e):
        """ Redirect to toggle_active_cb """
        self.toggle_active_cb(e, self.plots[0])
    
    
    def toggle_active_y_cb(self, e):
        """ Redirect to toggle_active_cb """
        self.toggle_active_cb(e, self.plots[1])
    
    
    def toggle_active_cb(self, event, plt):
        """
        Respond to right or left click on one of the plots by altering the datum
        nearest the cursor
        @param event:
            The matplotlib.backend_bases.MouseEvent instance containing all
            important information
        @param plt:
            The MOSPlot that got clicked on
        """
        # first check that the click was on a plot
        x_click, y_click = event.xdata, event.ydata
        if x_click == None or y_click == None:
            return
        
        # extract some info from plt and use it to calculate distances
        fig, x_arr, y_arr = plt.get_data()
        (left, bottom), (right, top) = plt.get_axis().viewLim.get_points()
        dx = (x_arr - x_click) * fig.get_figwidth() / (right - left)
        dy = (y_arr - y_click) * fig.get_figheight() / (top - bottom)
        distance_from_click = np.hypot(dx, dy)
        
        # adjust self.active accordinly
        idx = np.argmin(distance_from_click)
        if event.button == 1:
            self.active[idx] = True
        elif event.button == 3:
            self.active[idx] = False
        self.update_plots()
    
    
    def finish_cb(self, *args):
        """
        Respond to the 'Finish' button in step 4 by finishing up
        """
        self.manager.clear_canvas()
        if self.next_step != None:
            self.next_step()
    
    
    def update_plots(self):
        """
        Calculates self.transformation, graph data on all plots, and display it
        @returns:
            The x and y residuals in numpy array form
        """
        data = self.data[np.nonzero(self.active)]

        # calculate the optimal transformation from the input data
        # Algorithm is Kabsch algorithm for calculating the optimal
        # rotation matrix that minimizes the RMSD (root mean squared
        # deviation) between two paired sets of points. This code
        # replaces the IRAF geomap task for the case when
        # fitgeometry=rotate.
        centroid = np.mean(data, axis=0)
        data = data - centroid
        p_i = np.asmatrix(data[:, 0:2])
        p_f = np.asmatrix(data[:, 2:4])
        u, s, v = np.linalg.svd(p_i.T * p_f)
        rot_mat = u * v
        shift =  centroid[2:4] - centroid[0:2]*rot_mat
        try:
            theta = np.mean([math.acos(rot_mat[0,0]), math.asin(rot_mat[1,0])])
        except ValueError:
            theta = 0
        self.transformation = (shift[0,0], shift[0,1], theta)
        
        # use its results to calculate some stuff
        xref = self.data[:, 0]
        yref = self.data[:, 1]
        xin  = self.data[:, 2]
        yin  = self.data[:, 3]
        xcalc, ycalc = transform(xref, yref, self.transformation)
        xres = xin - xcalc
        yres = yin - ycalc
        
        # graph residual data on the plots
        plot_residual(self.plots[0], xref, xres, self.active, var_name="X")
        plot_residual(self.plots[1], yref, yres, self.active, var_name="Y")
        
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
        if not math.isnan(xres) and not math.isnan(yres):
            endX = startX + 300*xres
            endY = startY + 300*yres
        else:
            endX = startX
            endY = startY
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
        self.final_displays["dX"].set_text("{:,.2f}".format(dx))
        self.final_displays["dY"].set_text("{:,.2f}".format(dy))
        self.final_displays["dPA"].set_text(u"{:,.4f}".format(thetaD))
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

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.NORMAL_FONT)
        txt.set_text("Look at the graphs. Remove any data with residuals "+
                     "greater than 1.0 or less than -1.0. Delete points by "+
                     "right clicking, and restore them by left-clicking. "+
                     "Click 'Next' below when the data is satisfactory.")
        exp.set_widget(txt)
        
        # now a framed vbox to put the plots in
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = Widgets.VBox()
        box.set_spacing(3)
        frm.set_widget(box)
        
        # add both plots to the frame
        self.plots = []
        for i in range(2):
            self.plots.append(plots.Plot(logger=self.logger))
            fig = Plot.PlotWidget(self.plots[i], width=300, height=300)
            box.add_widget(fig)
        self.plots[0].fig.canvas.mpl_connect("button_press_event",
                                             self.toggle_active_x_cb)
        self.plots[1].fig.canvas.mpl_connect("button_press_event",
                                             self.toggle_active_y_cb)
        
        # now make an HBox to hold the main controls
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the next button shows the values
        btn = Widgets.Button("Next")
        btn.add_callback('activated', self.step4_cb)
        btn.set_tooltip("Get the MES Offset values!")
        box.add_widget(btn)
        box.add_widget(Widgets.Label(''), stretch=True)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
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

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.NORMAL_FONT)
        txt.set_text("Enter the numbers you see below into the ANA window. dx "+
                     "and dy values are in pixels, and rotation value is in "+
                     "degrees. Values of less than 0.5 pixels and 0.01 "+
                     "degrees have been ignored. Click 'Finish' below when "+
                     "you are done.")
        exp.set_widget(txt)
        
        # now make a frame for the results
        frm = Widgets.Frame()
        gui.add_widget(frm)
        grd = Widgets.GridBox(3, 3)
        grd.set_spacing(3)
        frm.set_widget(grd)
        
        # make the three TextAreas to hold the final values
        self.final_displays = {}
        for i, (val, unit) in enumerate(VALUE_NAMES):
            lbl = Widgets.Label(val+" =", halign='right')
            lbl.set_font(self.manager.HEADER_FONT)
            grd.add_widget(lbl, i, 0)
            
            txt = Widgets.TextArea(editable=False)
            txt.set_font(self.manager.HEADER_FONT)
            grd.add_widget(txt, i, 1, stretch=True)
            self.final_displays[val] = txt
            
            lbl = Widgets.Label(unit+"\t", halign='left')
            lbl.set_font(self.manager.HEADER_FONT)
            grd.add_widget(lbl, i, 2)
        
        # make a box to hold the one control
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the only necessary button is this 
        btn = Widgets.Button("Finish")
        btn.add_callback('activated', self.finish_cb)
        btn.set_tooltip("Close Ginga")
        box.add_widget(btn)
        box.add_widget(Widgets.Label(''), stretch=True)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui



def parse_data(data1, data2):
    """
    Read the data and return it in a more useful format: a four-columned
    numpy array with the nans removed
    @param data1:
        The first input array: the star locations and/or sizes (ref values)
    @param data2:
        The second input array: the hole locations and/or sizes (in values)
    @returns:
        A four-column array representing the star positions and hole
        positions, and a 1-dimensional array of Trues
    """
    data = np.hstack((data2[:,:2], data1[:,:2]))
    real_idx = np.logical_not(np.any(np.isnan(data), axis=1))
    data = data[np.nonzero(real_idx)]
    
    return data, np.ones(data.shape[0], dtype=bool)


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
    Algorithm is from IRAF geomap documentation at
    http://stsdas.stsci.edu/cgi-bin/gethelp.cgi?geomap#description
    """
    if trans == None:
        return float('NaN'), float('NaN')
    
    xshift, yshift, thetaR = trans
    b = math.cos(thetaR)
    c = math.sin(thetaR)
    e = -c
    f = b
    newX = xshift + b * x + c * y
    newY = yshift + e * x + f * y

    return newX, newY


def plot_residual(plot, z_observe, z_residual, active, var_name=""):
    """
    Plot the residual of this data against the real value.
    Residual is defined as the difference between the calculated value of
    zref and the observed value of zref.
    @param plot:
        A ginga.util.plots.Plot object, onto which to draw the graph
    @param z_observe:
        A numpy array of the observed values of this variable
    @param z_residual:
        A numpy array of the residuals for this variable
    @param active:
        A numpy array representing which data are active, and which are not
    @param var_name:
        The name of this variable, if it has one
    """
    # separate the active and inactive data
    inactive = np.logical_not(active)
    active_x = z_observe[np.nonzero(active)]
    active_y = z_residual[np.nonzero(active)]
    inactive_x = z_observe[np.nonzero(inactive)]
    inactive_y = z_residual[np.nonzero(inactive)]
    
    # then plot reference values by residual values
    try:
        plot.clear()
    except AttributeError:
        plot.add_axis()
    plot.plot(active_x, active_y,
              linestyle='None', marker='+', color='blue')
    plot.plot(inactive_x, inactive_y,
              linestyle='None', marker='x', color='grey',
              xtitle="{0} Position (pixels)".format(var_name),
              ytitle="{0} Residual (pixels)".format(var_name),
              title="{0} Residual by {0}-axis".format(var_name))
    plot.xdata = z_observe
    plot.ydata = z_residual
    
    # shade in regions y > 1 and y < -1
    xlimits = plot.get_axis().get_xlim()
    ylimits = plot.get_axis().get_ylim()
    plot.get_axis().fill_between(xlimits, 1, ylimits[1]+1,
                                 color='red', alpha=0.3)
    plot.get_axis().fill_between(xlimits, -1, ylimits[0]-1,
                                 color='red', alpha=0.3)
    plot.get_axis().set_xlim(left=xlimits[0], right=xlimits[1])
    plot.get_axis().set_ylim(bottom=ylimits[0], top=ylimits[1])
    
    plot.draw()

#END

