#
# mesLocate.py -- a class designed to help locate a group of objects.
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
from __future__ import absolute_import
import math

# ginga imports
from ginga.gw import Widgets, Viewers

# third-party imports
import numpy as np
from numpy import ma
from six.moves import range



# constants
SELECTION_MODES = ("Automatic", "Crop", "Mask")
BOX_COLORS = ('green','red','blue','yellow','magenta','cyan','orange')



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
    
    
    
    def start(self, initial_data, mode, interact2=True,
              next_step=None):
        """
        Get the positions of a series of objects
        @param initial_data:
            The numpy array containing the approximate positions of the relevant
            objects
        @param mode:
            Either 'star' or 'mask' or 'starhole'; alters the sizes of squares
            and the autocut method
        @param interact2:
            Whether we should give the user a chance to interact with step 2
        @param next_step:
            A function to call when MESLocate is finished
        """
        # read the data
        self.obj_arr, obj0 = parse_data(initial_data)
        self.obj_num = self.obj_arr.shape[0]
        
        # define some attributes
        self.click_history = []     # places we've clicked
        self.click_index = -1       # index of the last click
        self.color_index = -1       # index of the current color
        self.current_obj = 0        # index of the current object
        self.drag_history = [[]]    # places we've click-dragged*
        self.drag_index = [-1]      # index of the current drag for each object
        self.drag_start = None      # the place where we most recently began to drag
        self.obj_centroids = np.zeros(self.obj_arr.shape)    # the new obj_arr based on user input and calculations
        self.square_size =  {'star':30, 'mask':60, 'starhole':20}[mode]  # the apothem of the search regions
        self.exp_obj_size = {'star':4,  'mask':20, 'starhole':4}[mode]  # the maximum expected radius of the objects
        self.interact = interact2    # whether we should interact in step 2
        self.next_step = next_step  # what to do when we're done
        
        # set some values based on mode
        if mode == 'star':
            autocut_method = 'stddev'   # fitsimage autocut method
            self.exp_obj_size = 4       # the maximum expected radius of objects
            self.square_size = 30       # the apothem of the search regions
        elif mode == 'mask':
            autocut_method = 'minmax'
            self.exp_obj_size = 20
            self.square_size = 60
        elif mode == 'starhole':
            autocut_method = 'minmax'
            self.exp_obj_size = 4
            # Use np.nanmax to ignore any objects with radius set to
            # NaN (those are objects that were skipped over in the
            # mask image step)
            self.square_size = np.nanmax(self.obj_arr[:,2])
        
        # creates the list of thumbnails that will go in the GUI
        self.fitsimage.get_settings().set(autocut_method=autocut_method)
        self.thumbnails = create_viewer_list(self.obj_num, self.logger)
        self.viewer_grid.remove_all()
        for row in range(int(math.ceil(self.obj_num/2.0))):
            for col in range(2):
                i = 2*row + col
                if i < len(self.thumbnails):
                    pic = Viewers.GingaViewerWidget(viewer=self.thumbnails[i])
                    self.viewer_grid.add_widget(pic, row, col)
        
        # set the mouse controls and automatically start if this is starhole mode
        self.set_callbacks()
        self.click1_cb(self.canvas, 1, *obj0)
        self.manager.go_to_gui('find')
        if mode == 'starhole':
            self.step2_cb()
        
        
        
    def set_callbacks(self, step=1, selection_mode=0, clear=True):
        """
        Assign all necessary callbacks to the canvas for the current step
        @param step:
            The number of this step - 1 for finding and 2 for centroid-getting
        @param selection_mode:
            0 for 'Automatic', 1 for 'Crop', or 2 for 'Mask'
        @param clear:
            Whether the canvas should be completely cleared
        """
        canvas = self.canvas
        
        # clear all existing callbacks first
        self.manager.clear_canvas(keep_objects=not clear, keep_zoom=not clear)
        
        # for step one, the only callbacks are for right-click and left-click
        if step == 1:
            canvas.add_callback('cursor-up', self.click1_cb)
            canvas.add_callback('draw-up', self.step2_cb)
        
        # for step two, you need callbacks for left-drag and middle-drag, too
        elif step == 2:
            if selection_mode == 2:
                canvas.add_callback('cursor-down', self.start_drag_cb, 'mask')
                canvas.add_callback('cursor-up', self.end_drag_cb, 'mask')
            else:
                canvas.add_callback('cursor-down', self.start_drag_cb, 'crop')
                canvas.add_callback('cursor-up', self.end_drag_cb, 'crop')
            if selection_mode == 1:
                canvas.add_callback('panset-down', self.start_drag_cb, 'crop')
                canvas.add_callback('panset-up', self.end_drag_cb, 'crop')
            else:
                canvas.add_callback('panset-down', self.start_drag_cb, 'mask')
                canvas.add_callback('panset-up', self.end_drag_cb, 'mask')
            canvas.add_callback('draw-up', self.next_obj_cb)
    
        
    def click1_cb(self, _, __, x, y):
        """
        Respond to a left click on the screen in step 1
        @param x:
            The x coordinate of the click
        @param y:
            The y coordiante of the click
        """
        # increment the index
        self.click_index += 1
        self.color_index += 1
        
        # if there are things saved ahead of this index (because of undo), clear them
        if self.click_index < len(self.click_history):
            self.click_history = self.click_history[:self.click_index]
        self.click_history.append((x,y))
        self.select_point(self.click_history[self.click_index])
        
        # also clear step2 variables
        self.current_obj = 0
        self.drag_history = [[]]*self.obj_num
        self.drag_index = [-1]*self.obj_num
        return False
    
    
    def set_position_cb(self, *args):
        """
        Respond to the spinboxes being used by essentially making a new click
        """
        self.canvas.delete_object_by_tag(tag(1, self.click_index))
        self.color_index -= 1
        self.click1_cb(None, None,
                       self.spinboxes['X'].get_value(),
                       self.spinboxes['Y'].get_value())
    
    
    def undo1_cb(self, *args):
        """
        Respond to the undo button in step 1
        by going back one click (if possible)
        """
        if self.click_index > 0:
            self.canvas.delete_object_by_tag(tag(1, self.click_index))
            self.click_index -= 1
            self.color_index -= 1
            self.canvas.delete_object_by_tag(tag(1, self.click_index))
            self.select_point(self.click_history[self.click_index])
    
    
    def redo1_cb(self, *args):
        """
        Respond to the redo button in step 1
        by going forward one click (if possible)
        """
        if self.click_index < len(self.click_history)-1:
            self.click_index += 1
            self.color_index += 1
            self.select_point(self.click_history[self.click_index])
            
            
    def choose_select_cb(self, _, mode_idx):
        """
        Keep track of our selection mode as determined by the combobox
        """
        # update the callbacks to account for this new mode
        self.set_callbacks(step=2, selection_mode=mode_idx, clear=False)
    
    
    def step1_cb(self, *args):
        """
        Respond to back button by returning to step 1
        """
        self.manager.go_to_gui('find')
        self.set_callbacks(step=1)
        self.select_point(self.click_history[self.click_index])
    
    def set_skip_btn_state(self):
        # Disable Skip button for first object. First object is used
        # as reference position and code gets confused if that object
        # is skipped.
        if self.current_obj == 0:
            self.skip_btn.set_enabled(False)
        else:
            self.skip_btn.set_enabled(True)
    
    def step2_cb(self, *args):
        """
        Respond to next button or right click by proceeding to the next step
        """
        # set everything up for the first object of step 2
        self.manager.go_to_gui('centroid')
        self.set_callbacks(step=2)
        # Disable Skip button for first object.
        self.set_skip_btn_state()
        self.select_point(self.click_history[self.click_index], True)
        self.zoom_in_on_current_obj()
        self.mark_current_obj()
        
        # in the event that there are masks here (because of the Back button)...
        for i in range(self.obj_num):
            for j in range(self.drag_index[i]+1):
                self.draw_mask(*self.drag_history[i][j], obj_idx=i, drag_idx=j)
        
        # if interaction is turned off, immediately go to the next object
        if not self.interact:
            self.next_obj_cb()
        
        
    def prev_obj_cb(self, *args):
        """
        Respond to back button in step 2 by going back to the last object
        """
        # if there is no previous object, return to step 1
        if self.current_obj > 0:
            self.current_obj -= 1
            # Current object has changed, so set Skip button state
            # based on current object number.
            self.set_skip_btn_state()
            self.zoom_in_on_current_obj()
            self.mark_current_obj()
        else:
            self.step1_cb()
        
    
    def next_obj_cb(self, *args):
        """
        Respond to next button or right click by proceeding to the next object
        """
        # if there is no next object, finish up
        self.current_obj += 1
        if self.current_obj >= self.obj_num:
            self.finish()
            return
        # Current object has changed, so set Skip button state based
        # on current object number.
        self.set_skip_btn_state()

        x1, y1, x2, y2, r = self.get_current_box()
        # Skip over current object if its x or y coordinates are NaN.
        if math.isnan(x1) or math.isnan(y1) or math.isnan(x2) or math.isnan(y2):
            self.obj_centroids[self.current_obj] = (np.nan, np.nan, np.nan)
            self.current_obj += 1

        if self.current_obj >= self.obj_num:
            self.finish()
            return
        self.set_skip_btn_state()
            
        # if there is one, focus in on it
        self.zoom_in_on_current_obj()
        self.mark_current_obj()

        # if interaction is turned off, immediately go to the next object
        if not self.interact:
            self.next_obj_cb()
    
    
    def skip_obj_cb(self, *args):
        """
        Respond to the skip button by ignoring this star completely
        """
        self.mark_current_obj([float('NaN')]*3)
        self.next_obj_cb()
    
    
    def start_drag_cb(self, c, k, x, y, kind):
        """
        Respond to the mouse finishing a left-drag by finalizing crop selection
        @param kind:
            Either 'mask' or 'crop', depending on the mouse button and the
            current selection mode
        @returns:
            True, in order to prevent the other panset callbacks from going off
        """
        # enable drawing and then start drawing
        self.canvas.enable_draw(True)
        fill = (kind == 'mask')
        self.canvas.set_drawtype(drawtype='rectangle', color='white',
                                 fill=fill, fillcolor='black')
        self.canvas.draw_start(c, k, x, y, self.fitsimage)
        self.drag_start = (x,y)
        return True
    
    
    def end_drag_cb(self, c, k, xf, yf, kind):
        """
        Respond to the mouse finishing a left-drag by finalizing crop selection
        @param xf:
            The final x coordinate of this drag
        @param yf:
            The final y coordinate of this drag
        @param kind:
            Either 'mask' or 'crop', depending on the mouse button and the
            current selection mode
        """
        # if rectangle has area zero, ignore it
        if (xf,yf) == self.drag_start:
            return
        
        # finish the drawing, but make sure nothing is drawn; it won't be visible anyway
        self.canvas.draw_stop(c, k, *self.drag_start, viewer=None)
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
                                      kind))
        
        # shade in the outside areas and remark it
        self.draw_mask(*self.drag_history[self.current_obj][-1])
        self.mark_current_obj()
    
    
    def viewer_redirect_cb(self, _, button, xv, yv, direction):
        """
        Respond to a click on the step2_viewer by adjusting x and y for the
        position of the viewer, and then making the canvas react as though it
        had been clicked on.
        @param button:
            The key code representing the mouse configuration (1 for cursor,
            2 for panset, and 4 for draw)
        @param xv:
            The x coordinate of the click relative to the viewer
        @param yv:
            The y coordinate of the click relative to the viewer
        @param direction:
            The direction of the event ('up' or 'down')
        """
        x0, y0, x1, y1, r = self.get_current_box()
        xf, yf = xv+int(x0), yv+int(y0)
        if button%2 == 1:
            self.canvas.make_callback('cursor-'+direction, button, xf, yf)
        if button%4/2 == 1:
            self.canvas.make_callback('panset-'+direction, button, xf, yf)
        if button%8/4 == 1:
            self.canvas.make_callback('draw-'+direction,   button, xf, yf)
    
    
    def undo2_cb(self, *args):
        """
        Respond to the undo button in step 2
        by going back one drag (if possible)
        """
        co = self.current_obj
        if self.drag_index[co] >= 0:
            self.canvas.delete_object_by_tag(tag(2, co, self.drag_index[co]))
            self.drag_index[co] -= 1
            self.mark_current_obj()
    
    
    def redo2_cb(self, *args):
        """
        Respond to the redo button in step 2
        by going forward one drag (if possible)
        """
        co = self.current_obj
        if self.drag_index[co] < len(self.drag_history[co])-1:
            self.drag_index[co] += 1
            self.draw_mask(*self.drag_history[co][self.drag_index[co]])
            self.mark_current_obj()
    
    
    def select_point(self, point, draw_circle_masks=False):
        """
        Set a point in step 1 as the current location of object #0,
        draws squares where it thinks all the objects are accordingly,
        and updates all thumbnails and spinboxes
        @param point:
            An int tuple containing the location of object #0
        @param draw_circle_masks:
            Whether we should draw the automatic circular masks
        """
        # define some variables before iterating through the objects
        x, y = point
        src_image = self.fitsimage.get_image()
        color = BOX_COLORS[self.color_index%len(BOX_COLORS)]   # cycles through all the colors
        shapes = []
        for i, viewer in enumerate(self.thumbnails):
            dx, dy, r = self.obj_arr[i]
            sq_size = self.square_size
            # Skip this object if its dx or dy are NaN (this is an
            # object that was skipped in previous step)
            if math.isnan(dx) or math.isnan(dy):
                continue
        
            # first, draw squares and numbers
            shapes.append(self.dc.SquareBox(x+dx, y+dy, sq_size, color=color))
            shapes.append(self.dc.Text(x+dx+sq_size, y+dy,
                                       str(i+1), color=color))
            
            # draw the circular mask if necessary
            if draw_circle_masks:
                if r <= sq_size:
                    shapes.append(empty_circle(x+dx, y+dy, r, sq_size, self.dc))
                    shapes.append(self.dc.Circle(x+dx, y+dy, r, color='white'))

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
        
        # update the spinboxes
        if self.spinboxes['X'].get_value() != x:
            self.spinboxes['X'].set_value(x)
        if self.spinboxes['Y'].get_value() != y:
            self.spinboxes['Y'].set_value(y)
    
    
    def draw_mask(self, xd1, yd1, xd2, yd2, kind, obj_idx=None, drag_idx=None):
        """
        Draw the giant rectangles around an object being cropped
        @param xd1, yd1, xd2, yd2:
            floats representing the coordinates of the upper-left-hand corner
            (1) and the bottom-right-hand corner (2) of the drag
        @param kind:
            A string - either 'mask' for an ommission or 'crop' for an inclusion
        @param obj_idx, drag_idx:
            The indices of the object and drag (to use in the tag)
        """
        # use current values for the indices if they are None
        if obj_idx == None:
            obj_idx = self.current_obj
        if drag_idx == None:
            drag_idx = self.drag_index[obj_idx]
        t = tag(2, obj_idx, drag_idx)
        
        # draw whichever kind of mask it is
        if kind == 'crop':
            # calculate the coordinates of the drag and the outer box
            xb1, yb1, xb2, yb2, r = self.get_current_box(idx=obj_idx)
            kwargs = {'color':'black', 'fill':True, 'fillcolor':'black'}
            
            # then draw the thing as a CompoundObject
            self.canvas.add(self.dc.CompoundObject(
                                self.dc.Rectangle(xb1, yb1, xb2, yd1, **kwargs),
                                self.dc.Rectangle(xb1, yd2, xb2, yb2, **kwargs),
                                self.dc.Rectangle(xb1, yd1, xd1, yd2, **kwargs),
                                self.dc.Rectangle(xd2, yd1, xb2, yd2, **kwargs),
                                self.dc.Rectangle(xd1, yd1, xd2, yd2,
                                                  color='white')),
                            tag=t)
        elif kind == 'mask':
            self.canvas.add(self.dc.Rectangle(xd1, yd1, xd2, yd2, color='white',
                                              fill=True, fillcolor='black'),
                            tag=t)
    
    
    def zoom_in_on_current_obj(self):
        """
        Set the position and zoom level on fitsimage such that the user can
        only see the object at index self.current_obj. Also locates and marks it
        """
        x1, y1, x2, y2, r = self.get_current_box()
        self.fitsimage.set_pan((x1+x2)/2, (y1+y2)/2)
        self.fitsimage.zoom_to(350.0/self.square_size)
        self.obj_count_label.set_text("Object {} out of {}".format(
                                            self.current_obj+1, self.obj_num))
        self.mark_current_obj()
    
    
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
            obj = locate_obj(self.get_current_box(),
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
        # fix up the canvas and clear callbacks
        self.manager.clear_canvas(keep_objects=True)
        
        # tell the manager to do whatever comes next
        self.output_data = np.array(self.obj_centroids)
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
        
    
    def get_current_box(self, idx=None):
        """
        Calculates the bounds of the box surrounding the current object
        @precondition:
            This method only works in step 2
        @param idx:
            The object index at the instant that we need the box (defaults to
            self.current_obj)
        @returns x1, y1, x2, y2, r:
            The float bounds and radius of the current box
        """
        if idx == None:
            idx = self.current_obj
        xf, yf = self.click_history[self.click_index]
        dx, dy, r = self.obj_arr[idx]
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

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.NORMAL_FONT)
        txt.set_text("Left click on the object closest to the box labeled "+
                     "'1'. The other objects should appear in the boxes "+
                     "below. Click again to select another position. Click "+
                     "'Next' below or right-click when you are satisfied with "+
                     "your location.\nRemember - bright areas are shown in "+
                     "white.")
        exp.set_widget(txt)
        
        # next, we need the zoomed-in images. This is the grid we put them in
        frm = Widgets.Frame()
        gui.add_widget(frm)
        grd = Widgets.GridBox()
        grd.set_spacing(3)
        frm.set_widget(grd)
        self.viewer_grid = grd

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
        btn.set_tooltip("Accept and proceed to step 2 (right-click)")
        box.add_widget(btn)
        
        # put in a spacer
        box.add_widget(Widgets.Label(''), stretch=True)
        
        # now add a section for more precise control
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = Widgets.VBox()
        box.set_spacing(3)
        frm.set_widget(box)
        
        # put in spinboxes for easy precision-alignment
        self.spinboxes = {}
        for var in ("X", "Y"):
            lbl = Widgets.Label(var+" position:")
            box.add_widget(lbl)
            row = Widgets.HBox()
            box.add_widget(row)
            
            num = Widgets.SpinBox(dtype=float)
            num.set_limits(0, 9999, 5)
            num.add_callback('value-changed', self.set_position_cb)
            num.set_tooltip("Use this to fine-tune the "+var+" value")
            row.add_widget(num, stretch=True)
            self.spinboxes[var] = num
            row.add_widget(Widgets.Label(''), stretch=True)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
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

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.manager.NORMAL_FONT)
        txt.set_text("Help the computer find the centroid of this object. "+
                     "Click and drag to include or exclude regions; "+
                     "left-click will crop to selection and middle-click will "+
                     "mask selection, or you can specify a selection option "+
                     "below. Click 'Next' below or right-click when the "+
                     "centroid has been found.")
        exp.set_widget(txt)
        
        # create a label to display the current object index 
        lbl = Widgets.Label()
        lbl.set_font(self.manager.HEADER_FONT)
        gui.add_widget(lbl)
        self.obj_count_label = lbl
        
        # create a CanvasView for step 2
        viewer = Viewers.CanvasView(logger=self.logger)
        viewer.set_desired_size(420, 420)
        viewer.enable_autozoom('on')
        viewer.enable_autocuts('on')
        viewer.add_callback('button-press', self.viewer_redirect_cb, 'down')
        viewer.add_callback('button-release', self.viewer_redirect_cb, 'up')
        self.step2_viewer = viewer
        
        # put it in a ViewerWidget, and put that in the gui
        frm = Widgets.Frame()
        gui.add_widget(frm)
        pic = Viewers.GingaViewerWidget(viewer=viewer)
        frm.set_widget(pic)
        
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
        btn.set_tooltip("Accept and proceed to the next object (right-click)")
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
        # Save a reference to the Skip button because we need to be
        # able to enable/disable it depending on which object is being
        # displayed. First object cannot be skipped because code uses
        # its coordinates as reference position.
        self.skip_btn = btn
        
        # put in a spacer
        box.add_widget(Widgets.Label(""), stretch=True)
        
        # make a new box for a combobox+label combo
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = Widgets.VBox()
        box.set_spacing(3)
        frm.set_widget(box)
        lbl = Widgets.Label("Selection Mode:")
        box.add_widget(lbl)
        
        # this is the combobox of selection options
        com = Widgets.ComboBox()
        for text in SELECTION_MODES:
            com.append_text(text)
        com.set_index(0)
        com.add_callback('activated', self.choose_select_cb)
        com.set_tooltip("Choose what happens when you click-drag")
        box.add_widget(com)
        
        # space appropriately and return
        gui.add_widget(Widgets.Label(''), stretch=True)
        return gui
    
    
    
    @staticmethod
    def read_sbr_file(filename, logger):
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
            logger.warn('Warning: sbr file %s not found' % filename)
            return np.zeros((1,2))
        
        # declare some variables
        array = []
        line = sbr.readline()
        
        # read and convert the first two variables from each line
        while line != "":
            vals = line.split(', ')
            if vals[0] == 'C':
                sbrX, sbrY = float(vals[1]), float(vals[2])
                array.append(imgXY_from_sbrXY(sbrX, sbrY))
            line = sbr.readline()
        
        sbr.close()
        return np.array(array)



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


def parse_data(data):
    """
    Reads the data and returns it in a more useful form
    @param data:
        A numpy array of two or three columns, representing x, y[, and r]
    @returns:
        A numpy array of three columns of floats representing relative locations
        and radii of objects,
        and a single float tuple (absolute location of first object)
    """
    obj_list = []
    
    for row in data:
        # for each line, get the important values and save them in obj_list
        x, y = row[:2]
        if len(row) >= 3:
            r = row[2]
        else:
            r = float('NaN')
        obj_list.append([x, y, r])
    
    # convert obj_list to ndarray, and extract obj0
    obj_list = np.array(obj_list)
    obj0 = (obj_list[0,0], obj_list[0,1])
    obj_list[:,0:2] -= obj0
    return obj_list, obj0


def create_viewer_list(n, logger=None, width=120, height=120):    # 147x147 is approximately the size it will set it to, but I have to set it manually because otherwise it will either be too small or scale to the wrong size at certain points in the program. Why does it do this? Why can't it seem to figure out how big the window actually is when it zooms? I don't have a clue! It just randomly decides sometime after my plugin's last init method and before its first callback method, hey, guess what, the window is 194x111 now - should I zoom_fit again to match the new size? Nah, that would be TOO EASY. And of course I don't even know where or when or why the widget size is changing because it DOESN'T EVEN HAPPEN IN GINGA! It happens in PyQt4 or PyQt 5 or, who knows, maybe even Pyside. Obviously. OBVIOUSLY. GAGFAGLAHOIFHAOWHOUHOUH~~!!!!!
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
        x1, y1, x2, y2, kind = (int(drag[0])-int(x0)+1, int(drag[1])-int(y0)+1,
                                int(drag[2])-int(x0)+1, int(drag[3])-int(y0)+1,
                                drag[4])
        mask = np.zeros(raw.shape, dtype=bool)
        mask[y1:y2, x1:x2] = True
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


def empty_circle(x, y, r, a, dc):
    """
    Create a ginga canvas mixin (whatever that is) composed of a black
    filled square with a circle removed from the center
    @param x:
        The x coordinate of the center of the circle
    @param y:
        The y coordinate of the center of the circle
    @param r:
        The radius of the circle
    @param a:
        The apothem of the square around the circle
    @param dc:
        The drawing classes module
    @returns:
        A canvas.types.layer.CompoundObject, as described above
    """
    # the verticies of the polygon that will approximate this shape
    vertices = [(x+a, y+a), (x+a, y-a), (x-a, y-a), (x-a, y+a), (x+a, y+a)]
    # draw the circle
    for theta in range(45, 406, 10):
        vertices.append((x + r*math.cos(math.radians(theta)),
                         y + r*math.sin(math.radians(theta))))
    # and then fill in the outside
    return dc.Polygon(vertices, color='black', fill=True, fillcolor='black')


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

