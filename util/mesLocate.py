#
# mesLocate.py -- a class designed to help locate a group of objects.
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#

    # TODO: are pieces of stars in starhole getting cropped out? I hope not...

# standard imports
import math

# ginga imports
from ginga.gw import Widgets, Viewers

# third-party imports
import numpy as np
from numpy import ma



# constants
selection_modes = ("Automatic", "Star", "Mask")
colors = ('green','red','blue','yellow','magenta','cyan','orange')



class MESLocate(object):
    """
    A class that locates a set of calibration objects, asks for users to help
    locate anomolies and artifacts on its images of those objects, and then
    calculates their centers of masses. Intended for use as part of the MOS
    Acquisition software for aligning MOIRCS.
    """
    
    def __init__(self, manager):
        """
        Class constructor
        @param manager:
            The MESOffset plugin that this class communicates with
        """
        manager.initialise(self)
    
    
    
    def start(self, input_data, mode, interact2=True,
              next_step=None):
        """
        Get the positions of a series of objects
        @param input_data:
            The numpy array containing the object positions we search for
        @param mode:
            Either 'star' or 'mask' or 'starhole'; alters the sizes of squares
            and the autocut method
        @param interact2:
            Whether we should give the user a chance to interact with step 2
        @param next_step:
            A function to call when MESLocate is finished
        """
        # read the data
        self.obj_list, self.obj0 = self.parse_data(input_data)
        self.obj_num = len(self.obj_list)
        
        # define some attributes
        self.click_history = []     # places we've clicked
        self.click_index = -1       # index of the last click
        self.current_obj = 0        # index of the current object
        self.drag_history = [[]]*self.obj_num   # places we've click-dragged*
        self.drag_index = [-1]*self.obj_num     # index of the current drag for each object
        self.drag_start = None      # the place where we most recently began to drag
        self.obj_centroids = [None]*self.obj_num    # the new obj_list based on user input and calculations
        self.square_size =  {'star':25, 'mask':60, 'starhole':25}[mode]  # the size of the search regions
        self.exp_obj_size = {'star':4,  'mask':20, 'starhole':4}[mode]  # the maximum expected radius of the objects
        self.interact = interact2    # whether we should interact in step 2
        self.next_step = next_step  # what to do when we're done
        
        # set the autocut to make things easier to see
        if mode == 'star':
            method = 'stddev'
        else:
            method = 'minmax'
        self.fitsimage.get_settings().set(autocut_method=method)
        
        # creates the list of thumbnails that will go in the GUI
        self.thumbnails = self.create_viewer_list(self.obj_num, self.logger)
        for row in range(int(math.ceil(self.obj_num/2.0))):
            for col in range(2):
                try:
                    i = 2*row + col
                    pic = Viewers.GingaViewerWidget(viewer=self.thumbnails[i])
                    self.viewer_grid.add_widget(pic, row, col)
                except IndexError:
                    pass
        
        # set the mouse controls and automatically start if this is starhole mode
        self.set_callbacks()
        self.click1_cb(self.canvas, 1, *self.obj0)
        self.manager.go_to_gui('find')
        if mode == 'starhole':
            self.step2_cb()
        
        
        
    def set_callbacks(self, step=1, selection_mode="Automatic"):
        """
        Assign all necessary callbacks to the canvas for the current step
        @param step:
            The number of this step - 1 for finding and 2 for centroid-getting
        @param selection_mode:
            Either 'Automatic', 'Star', or 'Mask'. It decides what happens
            when we click and drag
        """
        canvas = self.canvas
        
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
            if selection_mode == "Star":
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
        self.manager.go_to_gui('find')
        self.set_callbacks(step=1)
        self.fitsimage.center_image()
        self.fitsimage.zoom_fit()
    
    
    def step2_cb(self, *args):
        """
        Responds to next button or right click by proceeding to the next step
        """
        # set everything up for the first object of step 2
        self.manager.go_to_gui('centroid')
        self.set_callbacks(step=2)
        self.canvas.delete_all_objects()
        self.select_point(self.click_history[self.click_index])
        self.zoom_in_on_current_obj()
        self.mark_current_obj()
        
        # if interaction is turned off, immediately go to the next object
        if not self.interact:
            self.next_obj_cb()
        
        
    def prev_obj_cb(self, *args):
        """
        Responds to back button in step 2 by going back to the last object
        """
        # if there is no previous object, return to step 1
        if self.current_obj > 0:
            self.current_obj -= 1
            self.zoom_in_on_current_obj()
            self.mark_current_obj()
        else:
            self.step1_cb()
        
    
    def next_obj_cb(self, *args):
        """
        Responds to next button or right click by proceeding to the next object
        """
        # if there is no next object, finish up
        self.current_obj += 1
        if self.current_obj >= self.obj_num:
            self.finish()
            return
            
        # if there is one, focus in on it
        self.zoom_in_on_current_obj()
        self.mark_current_obj()
        
        # if interaction is turned off, immediately go to the next object
        if not self.interact:
            self.next_obj_cb()
    
    
    def skip_obj_cb(self, *args):
        """
        Responds to the skip button by ignoring this star completely
        """
        self.mark_current_obj([float('NaN')]*3)
        self.next_obj_cb()
    
    
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
        x1, y1, x2, y2, r = self.get_current_box()
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
        x1, y1, x2, y2, r = self.get_current_box()
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
            self.canvas.delete_object_by_tag(tag(1, self.click_index))
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
        self.set_callbacks(step=2, selection_mode=selection_modes[mode_idx])
    
    
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
            dx, dy, r = self.obj_list[i]
            sq_size = self.square_size
        
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
            xb1, yb1, xb2, yb2, r = self.get_current_box()
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
        x1, y1, x2, y2, r = self.get_current_box()
        
        # then move and zoom
        self.fitsimage.set_pan((x1+x2)/2, (y1+y2)/2)
        self.fitsimage.zoom_to(360.0/self.square_size)
    
    
    def mark_current_obj(self, obj=None):
        """
        Puts a point and/or circle on the current object
        @param obj:
            The exact coordinates (x, y, r) of this object. If none are
            provided, they will be calculated using locate_obj
        """
        # if there is already a point for this object, delete it
        t = tag(2, self.current_obj, 'pt')
        self.canvas.delete_object_by_tag(t)
        
        # then locate and draw the point (if it exists)
        sq_size = self.square_size
        if obj == None:
            co = self.current_obj
            obj = self.locate_obj(self.get_current_box(),
                                  self.drag_history[co][:self.drag_index[co]+1],
                                  self.fitsimage.get_image(),
                                  min_search_radius=self.exp_obj_size,
                                  viewer=self.step2_viewer)
        
        # if any of the coordinates are NaN, then a red x will be drawn in the middle
        if True in [math.isnan(x) for x in obj]:
            x1, y1, x2, y2, r = self.get_current_box()
            self.canvas.add(self.dc.Point((x1+x2)/2, (y1+y2)/2, sq_size/3,
                                          color='red', linewidth=1,
                                          linestyle='dash'),
                            tag=t)
        else:
            self.canvas.add(self.dc.CompoundObject(
                                    self.dc.Circle(obj[0], obj[1], obj[2],
                                                   color='green', linewidth=1),
                                    self.dc.Point(obj[0], obj[1], sq_size/3,
                                                  color='green', linewidth=1)),
                            tag=t)
        
        self.obj_centroids[self.current_obj] = obj
    
    
    def finish(self):
        """
        Finishes up and goes to the next step
        """
        # fix up the canvas
        self.canvas.delete_all_objects()
        self.fitsimage.zoom_fit()
        self.fitsimage.center_image()
        
        # output the findings
        self.output_data = np.array(self.obj_centroids)
        
        # do whatever comes next
        if self.next_step != None:
            self.next_step()
        
        
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
        @returns x1, y1, x2, y2, r:
            The float bounds and radius of the current box
        """
        xf, yf = self.click_history[self.click_index]
        dx, dy, r = self.obj_list[self.current_obj]
        s = self.square_size
        if math.isnan(r):
            r = 1.42*s
        return (xf+dx-s, yf+dy-s, xf+dx+s, yf+dy+s, r)
        
            
    def gui_list(self, orientation='vertical'):
        """
        Combine the GUIs necessary for the MESLocate part of the plugin
        Must be implemented for each MESPlugin
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A list of tuples with strings (names) and Widgets (guis)
        """
        return [('find',     self.make_gui_find(orientation)),
                ('centroid', self.make_gui_cent(orientation))]
        
        
    def make_gui_find(self, orientation='vertical'):
        """
        Construct a GUI for the first step: finding the objects
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # create a label to title this step
        lbl = Widgets.Label("Pick First Hole")
        lbl.set_font(self.manager.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.normal_font)
        txt.set_text("Left click on the object closest to the box labeled "+
                     "'1'. The other objects should appear in the boxes "+
                     "below. Click again to select another position. Click "+
                     "'Next' below or right-click when you are satisfied with "+
                     "your location.\nRemember - bright areas are shown in "+
                     "white.")
        exp.set_widget(txt)

        # create a box to group the primary control buttons together
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
        
        # put in a spacer
        box.add_widget(Widgets.Label(""), stretch=True)
        
        # lastly, we need the zoomed-in images. This is the grid we put them in
        frm = Widgets.Frame()
        gui.add_widget(frm, stretch=True)
        grd = Widgets.GridBox()
        frm.set_widget(grd)
        self.viewer_grid = grd
        
        return gui
        
        
    def make_gui_cent(self, orientation='vertical'):
        """
        Construct a GUI for the second step: calculating the centroids
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # create a label to title this step
        lbl = Widgets.Label("Determine Centroids")
        lbl.set_font(self.manager.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.normal_font)
        txt.set_text("Help the computer find the centroid of this object. "+
                     "Click and drag to include or exclude regions; "+
                     "left-click will crop to selection and middle-click will "+
                     "mask selection, or you can specify a selection option "+
                     "below. Click 'Next' below or right-click when the "+
                     "centroid has been found.")
        exp.set_widget(txt)
        
        # now make an HBox to hold the primary controls
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
        
        # put in a spacer
        box.add_widget(Widgets.Label(""), stretch=True)
        
        # another HBox holds the skip button, because it doesn't fit on the first line
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)
        
        # the skip button sets this object to NaN and moves on
        btn = Widgets.Button("Skip")
        btn.add_callback('activated', self.skip_obj_cb)
        btn.set_tooltip("Remove this object from the data set")
        box.add_widget(btn)
        
        # put in a spacer
        box.add_widget(Widgets.Label(""), stretch=True)
        
        # make a new box for a combobox+label combo
        box = Widgets.VBox()
        box.set_spacing(3)
        gui.add_widget(box)
        lbl = Widgets.Label("Selection Mode:")
        box.add_widget(lbl)
        
        # this is the combobox of selection options
        com = Widgets.ComboBox()
        for text in selection_modes:
            com.append_text(text)
        com.add_callback('activated', self.choose_select_cb)
        box.add_widget(com)
        
        # create a CanvasView for step 2
        viewer = Viewers.CanvasView(logger=self.logger)
        viewer.set_desired_size(420, 420)
        viewer.enable_autozoom('on')
        viewer.enable_autocuts('on')
        self.step2_viewer = viewer
        
        # put it in a ViewerWidget, and put that in the gui
        frm = Widgets.Frame()
        gui.add_widget(frm)
        pic = Viewers.GingaViewerWidget(viewer=viewer)
        frm.set_widget(pic)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
        
        
    
    @staticmethod
    def create_viewer_list(n, logger=None, width=147, height=147):    # 147x147 is approximately the size it will set it to, but I have to set it manually because otherwise it will either be too small or scale to the wrong size at certain points in the program. Why does it do this? Why can't it seem to figure out how big the window actually is when it zooms? I don't have a clue! It just randomly decides sometime after my plugin's last init method and before its first callback method, hey, guess what, the window is 194x111 now - should I zoom_fit again to match the new size? Nah, that would be TOO EASY. And of course I don't even know where or when or why the widget size is changing because it DOESN'T EVEN HAPPEN IN GINGA! It happens in PyQt4 or PyQt 5 or, who knows, maybe even Pyside. Obviously. OBVIOUSLY. GAGFAGLAHOIFHAOWHOUHOUH~~!!!!!
        """
        Create a list of n viewers with certain properties
        @param n:
            An integer - the length of the desired list
        @param width:
            The desired width of each viewer
        @param height:
            The desired height of each veiwer
        @param logger:
            A Logger object to pass into the new Viewers
        @returns:
            A list of Viewers.CanvasView objects
        """
        output = []
        for i in range(n):
            viewer = Viewers.CanvasView(logger=logger)
            viewer.set_desired_size(width, height)
            viewer.enable_autozoom('on')
            viewer.enable_autocuts('on')
            output.append(viewer)
        return output

    
    @staticmethod
    def read_sbr_file(filename):
        """
        Read the file and return the data within, structured as the position
        of the first star as well as the positions of the other stars
        @param filename:
            The name of the file which contains the data
        @returns:
            A numpy array of two columns, containing the first two data in each
            row of the sbr file
        """
        # open the file
        try:
            sbr = open(filename, 'r')
        except IOError:
            return np.zeros((1,2))
        
        # declare some variables
        array = []
        line = sbr.readline()
        
        # read and convert the first two variables from each line
        while line != "":
            vals = line.split(', ')
            if vals[0] == 'C':
                sbrX, sbrY = float(vals[1]), float(vals[2])
                array.append(MESLocate.imgXY_from_sbrXY(sbrX, sbrY))
            line = sbr.readline()
        
        sbr.close()
        return np.array(array)


    @staticmethod
    def imgXY_from_sbrXY(sbrX, sbrY):
        """
        Converts coordinates from the SBR file to coordinates
        compatible with FITS files
        @param sbr_coords:
            A string or float tuple of x and y read from *.sbr
        @returns:
            A float tuple of x amd u that will work with the rest of Ginga
        """
        # I'm sorry; I have no idea what any of this math is.
        fX = 1078.0 - float(sbrX)*17.57789
        fY = 1857.0 + float(sbrY)*17.57789
        fHoleX = 365.0 + (fX-300.0)
        fHoleY = 2580.0 + (fY-2660.0)
        return (fHoleX, fHoleY)
        
    
    @staticmethod
    def parse_data(data):
        """
        Reads the data and returns it in a more useful form
        @param data:
            A numpy array of two or three columns, representing x, y[, and r]
        @returns:
            A tuple containing a list of tuples of three floats representing
            relative locations and radii of objects, and a single float tuple
            (absolute location of first object)
        """
        obj_list = []
        obj0 = None
        
        for row in data:
            # for each line, get the important values and save them in obj_list
            x, y = row[:2]
            if len(row) >= 3:
                r = row[2]
            else:
                r = float('NaN')
            
            # if this is the first one, put something in obj0
            if obj0 == None:
                obj0 = (x, y)
                obj_list.append((0, 0, r))
            else:
                obj_list.append((x - obj0[0], y - obj0[1], r))
            
        return obj_list, obj0
        
    
    @staticmethod
    def locate_obj(bounds, masks, image, viewer=None,
                   min_search_radius=None, thresh=3):
        """
        Finds the center of an object using center of mass calculation
        @param bounds:
            A tuple of floats x1, y1, x2, y2, r. The object should be within
            this box
        @param masks:
            A list of tuples of the form (x1, y1, x2, y2, kind) where kind is either
            'mask' or 'crop' and everything else is floats. Each tuple in masks
            is one drag of the mouse that ommitted either its interior or its
            exterior
        @param image:
            The AstroImage containing the data necessary for this calculation
        @param viewer:
            The viewer object that will display the new data, if desired
        @param min_search_radius:
            The smallest radius that this will search
        @param thresh:
            The number of standard deviations above the mean a data point must
            be to be considered valid
        @returns:
            A tuple of two floats representing the actual location of the object
            or a tuple of NaNs if no star could be found
        """
        # start by getting the raw data from the image matrix
        raw, x0,y0,x1,y1 = image.cutout_adjust(*bounds[:4])
        search_radius = bounds[4]
        x_cen, y_cen = raw.shape[0]/2.0, raw.shape[1]/2.0
        yx = np.indices(raw.shape)
        x_arr, y_arr = yx[1], yx[0]
        
        # crop data to circle
        mask_tot = np.hypot(x_arr - x_cen, y_arr - y_cen) > search_radius
        
        # mask data based on masks
        for drag in masks:
            x1, y1, x2, y2, kind = (int(drag[0]-bounds[0]), int(drag[1]-bounds[1]),
                                    int(drag[2]-bounds[0]), int(drag[3]-bounds[1]),
                                    drag[4])
            mask = np.zeros(raw.shape, dtype=bool)
            mask[y1:y2, x1:x2] = np.ones((y2-y1, x2-x1), dtype=bool)
            if kind == 'crop':
                mask = np.logical_not(mask)
            mask_tot = np.logical_or(mask_tot, mask)
        
        # apply mask, calculate threshold, normalize, and coerce data positive
        data = ma.masked_array(raw, mask=mask_tot)
        threshold = thresh*ma.std(data) + ma.mean(data)
        data = data - threshold
        data = ma.clip(data, 0, float('inf'))
        
        # display the new data on the viewer, if necessary
        if viewer != None:
            viewer.get_settings().set(autocut_method='minmax')
            viewer.set_data(data)
        
        # exit if the entire screen is masked
        if np.all(mask_tot):
            return (float('NaN'), float('NaN'), float('NaN'))
        
        # iterate over progressively smaller search radii
        if min_search_radius == None:
            min_search_radius = search_radius/2
        has_not_executed_yet = True
        while search_radius >= min_search_radius or has_not_executed_yet:
            has_not_executed_yet = False
            old_x_cen, old_y_cen = float('-inf'), float('-inf')
            
            # repeat the following until you hit an assymptote:
            while np.hypot(x_cen-old_x_cen, y_cen-old_y_cen) >= 0.5:
                # define an array for data constrained to its search radius
                circle_mask = np.hypot(x_arr-x_cen, y_arr-y_cen) > search_radius
                local_data = ma.masked_array(data, mask=circle_mask)
                
                # calculate some moments and stuff
                mom1x = float(ma.sum(local_data*(x_arr)))
                mom1y = float(ma.sum(local_data*(y_arr)))
                mom0 = float(ma.sum(local_data))
                area = float(ma.sum(np.sign(local_data)))
                
                # now try a center-of-mass calculation to find the size and centroid
                try:
                    old_x_cen = x_cen
                    old_y_cen = y_cen
                    x_cen = mom1x/mom0
                    y_cen = mom1y/mom0
                    radius = math.sqrt(area/math.pi)
                except ZeroDivisionError:
                    return (float('NaN'), float('NaN'), float('NaN'))
            
            search_radius = search_radius/2
        
        return (x0 + x_cen - 0.5, y0 + y_cen - 0.5, radius)
        

def tag(step, mod_1, mod_2=None):
    """
    Create a new tag given the step and some modifiers,
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


# * NOTE: self.drag_history is a list of lists, with one list for each
#       object; each inner list contains tuples of the form
#       (float x1, float y1, float x2, float y2, string ['mask'/'crop'])

#END

