#
# MESLocate -- a ginga plugin designed to help locate a group of objects.
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
# the object we are looking for
mode = 'star' if 'star' in argv[1] else 'hole'
# the size of the object-finding squares (dependent on whether we look for holes or stars)
sq_size = 25 if mode == 'star' else 60
# the difference between the threshold and the mean, in standard deviations
threshold_dist = 3 if mode == 'star' else -.2
# the colors of said squares
colors = ('green','red','blue','yellow','magenta','cyan','orange')
# the different ways we can select things
selection_modes = ("Automatic", "Crop", "Mask")



class MESLocate(GingaPlugin.LocalPlugin):
    """
    A custom LocalPlugin for ginga that locates a set of calibration objects,
    asks for users to help locate anomolies and artifacts on its images
    of those objects, and then calculates their centers of masses. Intended
    for use as part of the MOS Acquisition software for aligning MOIRCS.
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
        super(MESLocate, self).__init__(fv, fitsimage)
        fv.set_titlebar("MOIRCS Acquisition")

        # initializes some class constants:
        self.title_font = self.fv.getFont('sansFont', 18)
        self.body_font = self.fv.getFont('sansFont', 10)

        # reads the given SBR file to get the object positions
        self.obj_list, self.obj0 = readSBR()
        self.obj_num = len(self.obj_list)
        # creates the list of thumbnails and plots that will go in the GUI
        self.thumbnails = create_viewer_list(self.obj_num, self.logger)
        self.plots = create_plot_list(self.logger)
        # and creates some other attributes:
        self.click_history = []     # places we've clicked
        self.click_index = -1       # index of the last click
        self.current_obj = 0        # index of the current object
        self.drag_history = [[]]*self.obj_num   # places we've click-dragged*
        self.drag_index = [-1]*self.obj_num     # index of the current drag for each object
        self.drag_start = None      # the place where we most recently began to drag
        self.obj_centroids = [None]*self.obj_num     # the new obj_list based on user input and calculations
        
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
        
        
        
    def set_callbacks(self, selection_mode="Automatic"):
        """
        Assigns all necessary callbacks to the canvas for the current step
        @param selection_mode:
            Either 'Automatic', 'Crop', or 'Mask'. It decides what happens
            when we click and drag
        """
        canvas = self.canvas
        step = self.get_step()
        
        # clear all existing callbacks first
        for cb in ('cursor-down', 'cursor-up',
                    'panset-down', 'panset-up', 'draw-up'):
            canvas.clear_callback(cb)
        
        # for step one, the only callbacks are for right-click and left-click
        if step == 1:
            canvas.add_callback('cursor-up', self.click1_cb)
            canvas.add_callback('draw-up', self.step2_cb)
        
        # for step two, you need callbacks for left-drag and middle-drag, too
        elif step == 2:
            if selection_mode == "Mask":
                canvas.add_callback('cursor-down', self.start_select_mask_cb)
                canvas.add_callback('cursor-up', self.end_select_mask_cb)
            else:
                canvas.add_callback('cursor-down', self.start_select_crop_cb)
                canvas.add_callback('cursor-up', self.end_select_crop_cb)
            if selection_mode == "Crop":
                canvas.add_callback('panset-down', self.start_select_crop_cb)
                canvas.add_callback('panset-up', self.end_select_crop_cb)
            else:
                canvas.add_callback('panset-down', self.start_select_mask_cb)
                canvas.add_callback('panset-up', self.end_select_mask_cb)
            canvas.add_callback('draw-up', self.next_obj_cb)
    
    
    def step1_cb(self, *args):
        """
        Responds to back button by returning to step 1
        """
        self.stack.set_index(0)
        self.fv.showStatus("Locate the object labeled '1' by clicking.")
        self.set_callbacks()
        self.fitsimage.center_image()
        self.fitsimage.zoom_fit()
    
    
    def step2_cb(self, *args):
        """
        Responds to next button or right click by proceeding to the next step
        """
        # set everything up for the first object of step 2
        self.stack.set_index(1)
        self.fv.showStatus("Crop each object image by clicking and dragging")
        self.set_callbacks()
        self.canvas.delete_all_objects()
        self.select_point(self.click_history[self.click_index])
        self.zoom_in_on_current_obj()
        self.mark_current_obj()
        
        # if interaction is turned off, immediately go to the next object
        if argv[4][0].lower() == 'n':
            self.next_obj_cb()
        
        
    def prev_obj_cb(self, *args):
        """
        Responds to back button in step 2 by going back to the last object
        """
        # if there is no previous object, return to step 1
        if self.current_obj > 0:
            self.current_obj -= 1
            self.zoom_in_on_current_obj()
        else:
            self.step1_cb()
        
    
    def next_obj_cb(self, *args):
        """
        Responds to next button or right click by proceeding to the next object
        """
        # if there is no next object, finish up
        self.current_obj += 1
        if self.current_obj >= self.obj_num:
            self.stack.set_index(2)
            self.fv.showStatus("View the graphs and filter the data")
            self.set_callbacks()
            self.fitsimage.center_image()
            self.fitsimage.zoom_fit()
            try:
                self.update_plots()
            except:
                import traceback
                traceback.print_exc()
            self.finish_cb()
            return
            
        # if there is one, focus in on it
        self.zoom_in_on_current_obj()
        self.mark_current_obj()
        
        # if interaction is turned off, immediately go to the next object
        if argv[4][0].lower() == 'n':
            self.next_obj_cb()
        
        
    def finish_cb(self, *args):
        """
        Responds to the Finish button in step 3 by ending the program
        """
        f = open(argv[3], 'w')
        if mode == 'star':
            for x, y, r in self.obj_centroids:
                f.write("%7.1f, %7.1f \n" % (x, y))
        else:
            for x, y, r in self.obj_centroids:
                f.write("%7.1f, %7.1f, %7.1f \n" % (x, y, r))
        f.close()
        self.close()
        self.fv.quit()
    
    
    def click1_cb(self, _, __, x, y):
        """
        Responds to a left click on the screen in step 1
        @param x:
            The x coordinate of the click
        @param y:
            The y coordiante of the click
        """
        # increment the index
        self.click_index += 1
        # if there are things saved ahead of this index (because of undo), clear them
        if self.click_index < len(self.click_history):
            self.click_history = self.click_history[:self.click_index]
        self.click_history.append((x,y))
        self.select_point(self.click_history[self.click_index])
        return False
        
        
    def start_select_crop_cb(self, _, __, x, y):
        """
        Responds to the mouse starting a left-drag by starting to select a crop
        @param x:
            An int corresponding to the x coordinate of where the click happened
        @param y:
            An int corresponding to the y coordinate of where the click happened
        @returns:
            True, in order to cancel the panset callback that comes after it
        """
        # enable drawing and then start drawing
        self.canvas.enable_draw(True)
        self.canvas.set_drawtype(drawtype='rectangle', color='white',
                                 fill=False)
        self.canvas.draw_start(self.canvas, 1, x, y, self.fitsimage)
        self.drag_start = (x,y)
        return True
        
        
    def start_select_mask_cb(self, _, __, x, y):
        """
        Responds to the mouse starting a middle-drag by starting to draw a mask
        @param x:
            An int corresponding to the x coordinate of where the click happened
        @param y:
            An int corresponding to the y coordinate of where the click happened
        @returns:
            True, in order to cancel the panset callback that comes after it
        """
        # enable drawing and then start drawing
        self.canvas.enable_draw(True)
        self.canvas.set_drawtype(drawtype='rectangle', color='white',
                                 fill=True, fillcolor='black')
        self.canvas.draw_start(self.canvas, 1, x, y, self.fitsimage)
        self.drag_start = (x,y)
        return True
        
        
    def end_select_crop_cb(self, _, __, xf, yf):
        """
        Responds to the mouse finishing a left-drag by finalizing crop selection
        @param x:
            An int corresponding to the x coordinate of where the click happened
        @param y:
            An int corresponding to the y coordinate of where the click happened
        """
        # if rectangle has area zero, ignore it
        if (xf,yf) == self.drag_start:
            return
            
        # finish the drawing, but make sure nothing is drawn; it won't be visible anyway
        self.canvas.draw_stop(None, None, *self.drag_start, viewer=None)
        self.canvas.enable_draw(False)
        # if anything is ahead of this in drag_history, clear it
        co = self.current_obj
        self.drag_index[co] += 1
        if self.drag_index[co] < len(self.drag_history[co]):
            self.drag_history[co] = self.drag_history[co][:self.drag_index[co]]
        
        # now save that crop
        x1, y1, x2, y2 = self.get_current_box()
        xi, yi = self.drag_start
        self.drag_history[co].append((min(max(min(xi, xf), x1), x2),
                                      min(max(min(yi, yf), y1), y2),
                                      min(max(max(xi, xf), x1), x2),
                                      min(max(max(yi, yf), y1), y2),
                                      'crop'))
        
        # shade in the outside areas and remark it
        self.draw_mask(*self.drag_history[self.current_obj][-1])
        self.mark_current_obj()
        
        
    def end_select_mask_cb(self, _, __, xf, yf):
        """
        Responds to the mouse finishing a middle-drag by finalizing object mask
        @param x:
            An int corresponding to the x coordinate of where the click happened
        @param y:
            An int corresponding to the y coordinate of where the click happened
        """
        # if rectangle has area zero, ignore it
        if (xf,yf) == self.drag_start:
            return
            
        # finish the drawing, but make sure nothing is drawn; we need to specify the tag
        self.canvas.draw_stop(None, None, *self.drag_start, viewer=None)
        self.canvas.enable_draw(False)
        # if anything is ahead of this in drag_history, clear it
        co = self.current_obj
        self.drag_index[co] += 1
        if self.drag_index[co] < len(self.drag_history[co]):
            self.drag_history[co] = self.drag_history[co][:self.drag_index[co]]
        
        # now save that mask (sorted and coerced in bounds)
        x1, y1, x2, y2 = self.get_current_box()
        xi, yi = self.drag_start
        self.drag_history[co].append((min(max(min(xi, xf), x1), x2),
                                      min(max(min(yi, yf), y1), y2),
                                      min(max(max(xi, xf), x1), x2),
                                      min(max(max(yi, yf), y1), y2),
                                      'mask'))
                                      
        # shade that puppy in and remark it
        self.draw_mask(*self.drag_history[self.current_obj][-1])
        self.mark_current_obj()
            
            
    def undo1_cb(self, *args):
        """
        Responds to the undo button in step 1
        by going back one click (if possible)
        """
        if self.click_index > 0:
            self.canvas.delete_object_by_tag(tag(1, self.click_index))
            self.click_index -= 1
            self.select_point(self.click_history[self.click_index])
    
    
    def redo1_cb(self, *args):
        """
        Responds to the redo button in step 1
        by going forward one click (if possible)
        """
        if self.click_index < len(self.click_history)-1:
            self.click_index += 1
            self.select_point(self.click_history[self.click_index])
            
            
    def undo2_cb(self, *args):
        """
        Responds to the undo button in step 2
        by going back one drag (if possible)
        """
        co = self.current_obj
        if self.drag_index[co] >= 0:
            self.canvas.delete_object_by_tag(tag(2, co, self.drag_index[co]))
            self.drag_index[co] -= 1
            self.mark_current_obj()
    
    
    def redo2_cb(self, *args):
        """
        Responds to the redo button in step 2
        by going forward one drag (if possible)
        """
        co = self.current_obj
        if self.drag_index[co] < len(self.drag_history[co])-1:
            self.drag_index[co] += 1
            self.draw_mask(*self.drag_history[co][self.drag_index[co]])
            self.mark_current_obj()
            
            
    def choose_select_cb(self, _, mode_idx):
        """
        Keeps track of our selection mode as determined by the combobox
        """
        # update the callbacks to account for this new mode
        self.set_callbacks(selection_mode=selection_modes[mode_idx])
    
    
    def select_point(self, point):
        """
        Sets a point in step 1 as the current location of object #0,
        draws squares where it thinks all the objects are accordingly,
        and updates all thumbnails
        @param point:
            An int tuple containing the location of object #0
        """
        # define some variables before iterationg through the objects
        x, y = point
        src_image = self.fitsimage.get_image()
        color = colors[self.click_index%len(colors)]   # cycles through all the colors
        shapes = []
        for i, viewer in enumerate(self.thumbnails):
            dx, dy = self.obj_list[i]
        
            # first, draw squares and numbers
            shapes.append(self.dc.SquareBox(x+dx, y+dy, sq_size, color=color))
            shapes.append(self.dc.Text(x+dx+sq_size, y+dy,
                                       str(i+1), color=color))

            # then, update the little pictures
            x1, y1, x2, y2 = (x-sq_size+dx, y-sq_size+dy,
                              x+sq_size+dx, y+sq_size+dy)
            cropped_data = src_image.cutout_adjust(x1,y1,x2,y2)[0]
            viewer.set_data(cropped_data)
            self.fitsimage.copy_attributes(viewer,
                                           ['transforms','cutlevels','rgbmap'])
                                           
        # draw all the squares and numbers to the canvas as one object
        self.canvas.add(self.dc.CompoundObject(*shapes),
                        tag=tag(1, self.click_index))
                        
                        
    def draw_mask(self, xd1, yd1, xd2, yd2, kind):
        """
        Draws the giant rectangles around an object when you crop it
        @param xd1, yd1, xd2, yd2:
            floats representing the coordinates of the upper-left-hand corner
            (1) and the bottom-right-hand corner (2) of the drag
        @param kind:
            A string - either 'mask' for an ommission or 'crop' for an inclusion
        """
        if kind == 'crop':
            # calculate the coordinates of the drag and the outer box
            xb1, yb1, xb2, yb2 = self.get_current_box()
            kwargs = {'color':'black', 'fill':True, 'fillcolor':'black'}
            
            # then draw the thing as a CompoundObject
            self.canvas.add(self.dc.CompoundObject(
                                self.dc.Rectangle(xb1, yb1, xb2, yd1, **kwargs),
                                self.dc.Rectangle(xb1, yd2, xb2, yb2, **kwargs),
                                self.dc.Rectangle(xb1, yd1, xd1, yd2, **kwargs),
                                self.dc.Rectangle(xd2, yd1, xb2, yd2, **kwargs),
                                self.dc.Rectangle(xd1, yd1, xd2, yd2,
                                                  color='white')),
                            tag=tag(2, self.current_obj,
                                    self.drag_index[self.current_obj]))
        elif kind == 'mask':
            self.canvas.add(self.dc.Rectangle(xd1, yd1, xd2, yd2, color='white',
                                              fill=True, fillcolor='black'),
                            tag=tag(2, self.current_obj,
                                    self.drag_index[self.current_obj]))
        
        
    def zoom_in_on_current_obj(self):
        """
        Set the position and zoom level on fitsimage such that the user can
        only see the object at index self.current_obj. Also locates and marks it
        """
        # get the bounding box that must be zoomed to
        x1, y1, x2, y2 = self.get_current_box()
        
        # then move and zoom
        self.fitsimage.set_pan((x1+x2)/2, (y1+y2)/2)
        self.fitsimage.zoom_to(360.0/sq_size)
    
    
    def mark_current_obj(self):
        """
        Puts a point and/or circle on the current object
        """
        # if there is already a point for this object, delete it
        t = tag(2, self.current_obj, 'pt')
        self.canvas.delete_object_by_tag(t)
        
        # then locate and draw the point (if it exists)
        obj = (float('NaN'), float('NaN'), float('NaN'))
        try:
            co = self.current_obj
            obj = locate_obj(self.get_current_box(),
                            self.drag_history[co][:self.drag_index[co]+1],
                            self.fitsimage.get_image())
            self.canvas.add(self.dc.CompoundObject(
                                    self.dc.Circle(obj[0], obj[1], obj[2],
                                                   color='green', linewidth=2),
                                    self.dc.Point(obj[0], obj[1], sq_size/4,
                                                  color='green', linewidth=2)),
                            tag=t)
        except ZeroDivisionError:
            x1, y1, x2, y2 = self.get_current_box()
            self.canvas.add(self.dc.Point((x1+x2)/2, (y1+y2)/2, sq_size/4,
                                          color='red', linewidth=2,
                                          linestyle='dash'), tag=t)
        
        self.obj_centroids[self.current_obj] = obj
                                          
                                          
    def update_plots(self):
        """
        Graphs data on all plots and displays it
        """
        for plot in self.plots:
            try:
                plot.set_data(self.obj_centroids)
            except TypeError:
                self.fv.showStatus("Could not locate one or more objects")
                return
            
        self.plots[0].plot_x_y()
        self.plots[1].plot_residual()
        
        
    def get_step(self):
        """
        Deduces which step we are on
        @returns:
            An int: 1 for step 1 and 2 for step 2
        """
        try:
            return self.stack.get_index()+1
        except AttributeError:
            return 1
            
    
    def get_current_box(self):
        """
        Calculates the bounds of the box surrounding the current object
        @precondition:
            This method only works in step 2
        @returns x1, y1, x2, y2:
            The float bounds of the current box
        """
        xf, yf = self.click_history[self.click_index]
        dx, dy = self.obj_list[self.current_obj]
        return (xf+dx-sq_size, yf+dy-sq_size, xf+dx+sq_size, yf+dy+sq_size)
        
        
    def make_gui1(self, orientation='vertical'):
        """
        Constructs a GUI for the first step: finding the objects
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # create a label to title this step
        lbl = Widgets.Label("Step 1")
        lbl.set_font(self.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Left click on the object labeled '1'. The other objects "+
                     "should appear in the boxes below. Click again to select "+
                     "another position. Click 'Next' below or right-click "+
                     "when you are satisfied with your location.\n"+
                     "Remember - bright areas are shown in white.")
        exp.set_widget(txt)

        # create a box to group the control buttons together
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)

        # the undo button goes back a click
        btn = Widgets.Button("Undo")
        btn.add_callback('activated', self.undo1_cb)
        btn.set_tooltip("Undo a single click (if a click took place)")
        box.add_widget(btn)

        # the redo button goes forward
        btn = Widgets.Button("Redo")
        btn.add_callback('activated', self.redo1_cb)
        btn.set_tooltip("Undo an undo action (if an undo action took place)")
        box.add_widget(btn)

        # the clear button erases the canvas
        btn = Widgets.Button("Clear")
        btn.add_callback('activated', lambda w: self.canvas.delete_all_objects())
        btn.set_tooltip("Erase all marks on the canvas")
        box.add_widget(btn)
        
        # the next button moves on to step 2
        btn = Widgets.Button("Next")
        btn.add_callback('activated', self.step2_cb)
        btn.set_tooltip("Accept and proceed to step 2")
        box.add_widget(btn)
        
        # lastly, we need the zoomed-in images. This is the grid we put them in
        num_img = self.obj_num   # total number of alignment objects
        columns = 2                       # pictures in each row
        rows = int(math.ceil(float(num_img)/columns))
        grd = Widgets.GridBox(rows=rows, columns=columns)
        gui.add_widget(grd)
        
        # these are the images we put in the grid
        for row in range(0, rows):
            for col in range(0, columns):
                i = row*columns + col
                if i < num_img:
                    pic = Viewers.GingaViewerWidget(viewer=self.thumbnails[i])
                    grd.add_widget(pic, row, col)
        
        # space gui appropriately and return it
        gui.add_widget(Widgets.Label(""), stretch=1)
        return gui
        
        
    def make_gui2(self, orientation='vertical'):
        """
        Constructs a GUI for the second step: cropping the stars
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # create a label to title this step
        lbl = Widgets.Label("Step 2")
        lbl.set_font(self.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Help the computer find the centroid of this object. "+
                     "Click and drag to include or exclude regions; "+
                     "left-click will crop to selection and middle-click will "+
                     "mask selection, or you can specify a selection option "+
                     "below. Click 'Next' below or right-click when the "+
                     "centroid has been found.")
        exp.set_widget(txt)
        
        # now make an HBox to hold the main controls
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the undo button goes back a crop
        btn = Widgets.Button("Undo")
        btn.add_callback('activated', self.undo2_cb)
        btn.set_tooltip("Undo a single selection (if a selection took place)")
        box.add_widget(btn)

        # the redo button goes forward
        btn = Widgets.Button("Redo")
        btn.add_callback('activated', self.redo2_cb)
        btn.set_tooltip("Undo an undo action (if an undo action took place)")
        box.add_widget(btn)

        # the clear button nullifies all crops
        btn = Widgets.Button("Back")
        btn.add_callback('activated', self.prev_obj_cb)
        btn.set_tooltip("Go back to the previous object")
        box.add_widget(btn)
        
        # the next button moves on to the next object
        btn = Widgets.Button("Next")
        btn.add_callback('activated', self.next_obj_cb)
        btn.set_tooltip("Accept and proceed to the next object")
        box.add_widget(btn)
        
        # make a box for a combobox+label combo
        box = Widgets.VBox()
        box.set_spacing(3)
        gui.add_widget(box)
        lbl = Widgets.Label("Selection Mode:")
        box.add_widget(lbl)
        
        # last is the combobox of selection options
        com = Widgets.ComboBox()
        for text in selection_modes:
            com.append_text(text)
        com.add_callback('activated', self.choose_select_cb)
        box.add_widget(com)
        
        # space gui appropriately and return it
        gui.add_widget(Widgets.Label(""), stretch=1)
        return gui
        
        
    def make_gui3(self, orientation='vertical'):
        """
        Constructs a GUI for the third step: viewing the graph
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
        btn.add_callback('activated', self.finish_cb)
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
        stk.add_widget(self.make_gui1(orientation))
        stk.add_widget(self.make_gui2(orientation))
        stk.add_widget(self.make_gui3(orientation))
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
        
        # stick our own canvas on top of the fitsimage canvas
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag='main-canvas')
        
        # clear the canvas
        self.canvas.delete_all_objects()
        
        # automatically select the first point and start
        self.click1_cb(self.canvas, 1, *self.obj0)


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
        self.fv.showStatus("Locate the object labeled '1' by clicking.")


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
        return "MESLocate"
        
        

def create_viewer_list(n, logger=None):
    """
    Create a list of n viewers with certain properties
    @param n:
        An integer - the length of the desired list
    @param logger:
        A Logger object to pass into the new Viewers
    @returns:
        A list of Viewers.CanvasView objects
    """
    output = []
    for i in range(n):
        viewer = Viewers.CanvasView(logger=logger)
        viewer.set_desired_size(194,141)    # this is approximately the size it will set it to, but I have to set it manually because otherwise it will either be too small or scale to the wrong size at certain points in the program. Why does it do this? Why can't it seem to figure out how big the window actually is when it zooms? I don't have a clue! It just randomly decides sometime after my plugin's last init method and before its first callback method, hey, guess what, the window is 194x111 now - should I zoom_fit again to match the new size? Nah, that would be TOO EASY. And of course I don't even know where or when or why the widget size is changing because it DOESN'T EVEN HAPPEN IN GINGA! It happens in PyQt4 or PyQt 5 or, who knows, maybe even Pyside. Obviously. OBVIOUSLY. GAGFAGLAHOIFHAOWHOUHOUH~~!!!!!
        viewer.enable_autozoom('on')
        viewer.enable_autocuts('on')
        output.append(viewer)
    return output
    
    
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


def readSBR():
    """
    Reads the SBR file and returns the position of the first active
    object as well as the relative positions of all the other objects in a list
    @returns:
        A tuple containing a list of float tuples, relative locations of objects
        and a single float tuple (absolute location of first object)
    """
    # define variables
    obj_list = []
    obj0 = None
    
    # open the file
    try:
        sbr = open(argv[2], 'r')
    except IOError:
        try:
            sbr = open("sbr_elaisn1rev.sbr")
        except IOError:
            return [(dx, dy) for dx in [0,1,-1] for dy in [0,1,-1]], (0,0)
    
    # now parse it!
    line = sbr.readline()
    while line != "":
        # for each line, get the important values and save them in obj_list
        vals = [word.strip(" \n") for word in line.split(",")]
        if vals[0] == "C":
            newX, newY = imgXY_from_sbrXY((vals[1], vals[2]))
            if obj0 == None:
                obj_list.append((0, 0))
                obj0 = (newX, newY)
            else:
                obj_list.append((newX-obj0[0],   # don't forget to shift it so object #0 is at the origin
                                  newY-obj0[1]))
        line = sbr.readline()
        
    return obj_list, obj0


def imgXY_from_sbrXY(sbr_coords):
    """
    Converts coordinates from the SBR file to coordinates
    compatible with FITS files
    @param sbr_coords:
        A string or float tuple of x and y read from *.sbr
    @returns:
        A float tuple of x amd u that will work with the rest of Ginga
    """
    # I'm sorry; I have no idea what any of this math is.
    sbrX, sbrY = sbr_coords
    fX = 1078.0 - float(sbrX)*17.57789
    fY = 1857.0 + float(sbrY)*17.57789
    fHoleX = 365.0 + (fX-300.0)
    fHoleY = 2580.0 + (fY-2660.0)
    return (fHoleX, fHoleY)
    
    
def locate_obj(bounds, masks, image):
    """
    Finds the center of an object using center of mass calculation
    @param bounds:
        A tuple of floats x1, y1, x2, y2. The object should be within this box
    @param masks:
        A list of tuples of the form (x1, y1, x2, y2, kind) where kind is either
        'mask' or 'crop' and everything else is floats. Each tuple in masks
        is one drag of the mouse that ommitted either its interior or its
        exterior
    @param image:
        The AstroImage containing the data necessary for this calculation
    @returns:
        A tuple of two floats representing the actual location of the object
    @raises ZeroDivisionError:
        If no object is visible in the frame
    """
    # start by cropping the image to get the data matrix
    data, x0,y0 = image.cutout_adjust(*bounds)[0:3]
    
    # omit data based on masks
    mask_tot = np.ones(data.shape)
    for drag in masks:
        x1, y1, x2, y2, kind = (int(drag[0]-bounds[0]), int(drag[1]-bounds[1]),
                                int(drag[2]-bounds[0]), int(drag[3]-bounds[1]),
                                drag[4])
        mask = np.ones(data.shape)
        mask[y1:y2, x1:x2] = np.zeros((y2-y1, x2-x1))
        if kind == 'crop':
            mask = 1-mask
        mask_tot = mask_tot*mask
    
    # apply mask, calculate threshold, coerce data positive, and reapply mask
    data = data * mask_tot
    threshold = threshold_dist*np.std(data) + np.mean(data)
    data = data - threshold
    data = np.clip(data, 0, float('inf'))
    data = np.square(data)
    data = data * mask_tot
    np.seterr(all='raise')
    # now do a center-of mass calculation to find the size and centroid
    x = np.tile(np.arange(0, data.shape[1]), (data.shape[0], 1))
    y = np.tile(np.arange(0, data.shape[0]), (data.shape[1], 1)).T
    x_sum = float(np.sum(data*x))
    y_sum = float(np.sum(data*y))
    data_sum = float(np.sum(data))
    area = float(np.sum(np.sign(data)))
    
    x_cen = x_sum/data_sum
    y_cen = y_sum/data_sum
    radius = math.sqrt(area/math.pi)
    return (x0 + x_cen, y0 + y_cen, radius)
    

def tag(step, mod_1, mod_2=None):
    """
    Creates a new tag given the step and some modifiers,
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

