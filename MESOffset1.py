#
# MOSAcquisition -- a ginga plugin designed to help measure the offset of the MOIRCS (works in conjunction with mesoffset scripts)
#
# Justin Kunimune
#



# standard imports
import math

# ginga imports
from ginga import GingaPlugin
from ginga.gw import Widgets, Viewers
from ginga.RGBImage import RGBImage
from ginga.util import iqcalc

# third-party imports
import numpy as np



# constants
sq_size = 30
colors = ('green','red','blue','yellow','magenta','cyan','orange')
selection_modes = ("Automatic", "Star", "Mask")



class MESOffset1(GingaPlugin.LocalPlugin):
    """
    A custom LocalPlugin for ginga that locates a set of calibration stars,
    asks for users to help locate anomolies and artifacts on its images
    of those stars, and then calculates their centers of masses. Intended
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
        super(MESOffset1, self).__init__(fv, fitsimage)
        fv.set_titlebar("MES Offset 1")

        # initializes some class constants:
        self.title_font = self.fv.getFont('sansFont', 18)
        self.body_font = self.fv.getFont('sansFont', 10)
        self.iqcalc = iqcalc.IQCalc(logger=self.logger)

        # reads the given SBR file to get the star positions
        self.star_list, self.star0 = readSBR()
        self.star_num = len(self.star_list)
        # creates the list of thumbnails that will go in the GUI
        self.thumbnails = create_viewer_list(self.star_num, self.logger)
        # and creates some other attributes:
        self.click_history = []     # places we've clicked
        self.click_index = -1       # index of the last click
        self.current_star = 0       # index of the current star
        self.drag_history = [[]]*self.star_num    # places we've click-dragged*
        self.drag_index = [-1]*self.star_num      # index of the current drag for each star
        self.drag_start = None      # the place where we most recently began to drag
        
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
        #       star; each inner list contains tuples of the form
        #       (float x1, float y1, float x2, float y2, string ['mask'/'star'])
        
        
        
    def set_callbacks(self, selection_mode="Automatic"):
        """
        Assigns all necessary callbacks to the canvas for the current step
        @param selection_mode:
            Either 'Automatic', 'Star', or 'Mask'. It decides what happens
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
                canvas.add_callback('cursor-down', self.start_select_star_cb)
                canvas.add_callback('cursor-up', self.end_select_star_cb)
            if selection_mode == "Star":
                canvas.add_callback('panset-down', self.start_select_star_cb)
                canvas.add_callback('panset-up', self.end_select_star_cb)
            else:
                canvas.add_callback('panset-down', self.start_select_mask_cb)
                canvas.add_callback('panset-up', self.end_select_mask_cb)
            canvas.add_callback('draw-up', self.next_star_cb)
            canvas.add_callback('draw-event', self.draw_cb)
    
    
    def step2_cb(self, _, __=None, ___=None, ____=None):
        """
        Responds to next button or right click by proceeding to the next step
        """
        self.stack.set_index(self.get_step())
        self.fv.showStatus("Crop each star image by clicking and dragging")
        self.set_callbacks()
        self.zoom_in_on_current_star()
        self.mark_current_star()
        
        
    def last_star_cb(self, _, __=None, ___=None, ____=None):
        """
        Responds to back button by going back to the last star
        """
        # if there is no previous star, do nothing
        if self.current_star > 0:
            self.current_star -= 1
            self.zoom_in_on_current_star()
        
    
    def next_star_cb(self, _, __=None, ___=None, ____=None):
        """
        Responds to next button or right click by proceeding to the next star
        """
        # if there is no next star, finish up
        self.current_star += 1
        if self.current_star >= self.star_num:
            self.fitsimage.center_image()
            self.fitsimage.zoom_fit()
            self.close()
            return
            
        # if there is one, focus in on it
        self.zoom_in_on_current_star()
        self.mark_current_star()
    
    
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
        
        
    def start_select_star_cb(self, _, __, x, y):
        """
        Responds to the mouse starting a left-drag by starting to select a star
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
        Responds to the mouse starting a middle-drag by starting to mask a star
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
        
        
    def end_select_star_cb(self, _, __, x, y):
        """
        Responds to the mouse finishing a left-drag by finalizing star selection
        @param x:
            An int corresponding to the x coordinate of where the click happened
        @param y:
            An int corresponding to the y coordinate of where the click happened
        """
        # if rectangle has area zero, ignore it
        if (x,y) == self.drag_start:
            return
            
        # finish the drawing, but make sure nothing is drawn; it won't be visible anyway
        self.canvas.draw_stop(None, None, *self.drag_start, viewer=None)
        self.canvas.enable_draw(False)
        # if anything is ahead of this in drag_history, clear it
        cs = self.current_star
        self.drag_index[cs] += 1
        if self.drag_index[cs] < len(self.drag_history[cs]):
            self.drag_history[cs] = self.drag_history[cs][:self.drag_index[cs]]
        
        # now save that star
        self.drag_history[cs].append((min(self.drag_start[0], x),
                                      min(self.drag_start[1], y),
                                      max(self.drag_start[0], x),
                                      max(self.drag_start[1], y),
                                      'star'))
        
        # shade in the outside areas and remark it
        self.draw_mask(*self.drag_history[self.current_star][-1])
        self.mark_current_star()
        
        
    def end_select_mask_cb(self, _, __, x, y):
        """
        Responds to the mouse finishing a middle-drag by finalizing star mask
        @param x:
            An int corresponding to the x coordinate of where the click happened
        @param y:
            An int corresponding to the y coordinate of where the click happened
        """
        # if rectangle has area zero, ignore it
        if (x,y) == self.drag_start:
            return
            
        # finish the drawing, but make sure nothing is drawn; we need to specify the tag
        self.canvas.draw_stop(None, None, *self.drag_start, viewer=None)
        self.canvas.enable_draw(False)
        # if anything is ahead of this in drag_history, clear it
        cs = self.current_star
        self.drag_index[cs] += 1
        if self.drag_index[cs] < len(self.drag_history[cs]):
            self.drag_history[cs] = self.drag_history[cs][:self.drag_index[cs]]
        
        # now save that mask
        self.drag_history[cs].append((min(self.drag_start[0], x),
                                      min(self.drag_start[1], y),
                                      max(self.drag_start[0], x),
                                      max(self.drag_start[1], y),
                                      'mask'))
                                      
        # shade that puppy in and remark it
        self.draw_mask(*self.drag_history[self.current_star][-1])
        self.mark_current_star()
            
            
    def undo1_cb(self, _):
        """
        Responds to the undo button in step 1
        by going back one click (if possible)
        """
        if self.click_index > 0:
            self.canvas.delete_object_by_tag(tag(1, self.click_index))
            self.click_index -= 1
            self.select_point(self.click_history[self.click_index])
    
    
    def redo1_cb(self, _):
        """
        Responds to the redo button in step 1
        by going forward one click (if possible)
        """
        if self.click_index < len(self.click_history)-1:
            self.click_index += 1
            self.select_point(self.click_history[self.click_index])
            
            
    def undo2_cb(self, _):
        """
        Responds to the undo button in step 2
        by going back one drag (if possible)
        """
        # sets drag_index backward for this star if possible
        cs = self.current_star
        if self.drag_index[cs] >= 0:
            self.canvas.delete_object_by_tag(tag(2, cs, self.drag_index[cs]))
            self.drag_index[cs] -= 1
            self.mark_current_star()
    
    
    def redo2_cb(self, _):
        """
        Responds to the redo button in step 2
        by going forward one drag (if possible)
        """
        # sets drag_index forward for this star if possible
        cs = self.current_star
        if self.drag_index[cs] < len(self.drag_history[cs])-1:
            self.drag_index[cs] += 1
            self.draw_mask(*self.drag_history[cs][self.drag_index[cs]])
            self.mark_current_star()
            
            
    def choose_select_cb(self, _, mode_idx):
        """
        Keeps track of our selection mode as determined by the combobox
        """
        # update the callbacks to account for this new mode
        self.set_callbacks(selection_mode=selection_modes[mode_idx])
        
        
    def draw_cb(self, _, tag):
        """
        Saves the tag whenever something is drawn
        """
        pass
        #self.tags.append(tag)
        
    
    def delete_last_obj(self):
        """
        Deletes the item with the most recent tag
        """
        pass
        #self.canvas.delete_object_by_tag(self.tags[-1])
        #self.tags.pop()
    
    
    def select_point(self, point):
        """
        Sets a point in step 1 as the current location of star #1,
        draws squares where it thinks all the stars are accordingly,
        and updates all thumbnails
        @param point:
            An int tuple containing the location of star #1
        """
        # define some variables before iterationg through the stars
        x, y = point
        src_image = self.fitsimage.get_image()
        color = colors[self.click_index%len(colors)]   # cycles through all the colors
        shapes = []
        for i, viewer in enumerate(self.thumbnails):
            dx, dy = self.star_list[i]
        
            # first, draw squares and numbers
            shapes.append(self.dc.SquareBox(x+dx, y+dy, sq_size, color=color))
            shapes.append(self.dc.Text(x+dx-sq_size+1, y+dy-sq_size+1,
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
                        
                        
    def draw_mask(self, x1, y1, x2, y2, kind):
        """
        Draws the giant rectangles around a star when you crop it
        @param x1, y1, x2, y2:
            floats representing the coordinates of the upper-left-hand corner
            (1) and the bottom-right-hand corner (2)
        @param kind:
            A string - either 'mask' for an ommission or 'star' for a crop
        """
        if kind == 'star':
            # calculate the coordinates of the outer box
            x0, y0 = self.click_history[self.click_index]
            dx, dy = self.star_list[self.current_star]
            x1, y1, x2, y2 = self.drag_history[self.current_star][-1][:-1]
            kwargs = {'color':'black', 'fill':True, 'fillcolor':'black'}
            
            # then draw the thing as a CompoundObject
            self.canvas.add(self.dc.CompoundObject(
                                self.dc.Rectangle(x0+dx-sq_size, y0+dy-sq_size,
                                                  x0+dx+sq_size, y1,
                                                  **kwargs),
                                self.dc.Rectangle(x0+dx-sq_size, y2,
                                                  x0+dx+sq_size, y0+dy+sq_size,
                                                  **kwargs),
                                self.dc.Rectangle(x0+dx-sq_size, y1,
                                                  x1,            y2,
                                                  **kwargs),
                                self.dc.Rectangle(x2,            y1,
                                                  x0+dx+sq_size, y2,
                                                  **kwargs),
                                self.dc.Rectangle(x1, y1, x2, y2,
                                                  color='white')),
                            tag=tag(2, self.current_star,
                                    self.drag_index[self.current_star]))
        else:
            self.canvas.add(self.dc.Rectangle(x1, y1, x2, y2, color='white',
                                              fill=True, fillcolor='black'),
                            tag=tag(2, self.current_star,
                                    self.drag_index[self.current_star]))
        
        
    def zoom_in_on_current_star(self):
        """
        Set the position and zoom level on fitsimage such that the user can
        only see the star at index self.current_star. Also locates and marks it
        """
        # get the final click location from step 1 and offset it based on index
        finalX, finalY = self.click_history[self.click_index]
        offsetX, offsetY = self.star_list[self.current_star]
        
        # then move and zoom
        self.fitsimage.set_pan(finalX + offsetX, finalY + offsetY)
        self.fitsimage.zoom_to(360.0/sq_size)
    
    
    def mark_current_star(self):
        """
        Puts a point on the current star
        """
        print "mark"
        # if there is already a point for this star, delete it
        t = tag(2, self.current_star, 'pt')
        self.canvas.delete_object_by_tag(t)
            
        # get the final click location from step 1 and offset it based on index
        finalX, finalY = self.click_history[self.click_index]
        offsetX, offsetY = self.star_list[self.current_star]
        
        # then locate with iqcalc and draw the point (if it exists)
        try:
            cs = self.current_star
            star = locate_star((finalX+offsetX, finalY+offsetY),
                            self.drag_history[cs][:self.drag_index[cs]+1],
                            self.fitsimage.get_image(), self.iqcalc)
            self.canvas.add(self.dc.Point(star[0], star[1], sq_size/4,
                                          color='white', linewidth=2), tag=t)
        except iqcalc.IQCalcError:
            star = (finalX+offsetX, finalY+offsetY)
            self.canvas.add(self.dc.Point(star[0], star[1], sq_size/4,
                                          color='red', linewidth=2,
                                          linestyle='dash'), tag=t)
        print "watney"
        
        
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
        
        
    def make_gui1(self, orientation='vertical'):
        """
        Constructs a GUI for the first step: locating the stars
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
        txt.set_text("Left click on the star labeled '#1'. The other stars "+
                     "should appear in the boxes below. Click again to select "+
                     "another position. Click 'Next' below or right-click "+
                     "when you are satisfied with your location.")
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
        num_img = self.star_num   # total number of alignment stars
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
        txt.set_text("Click and drag to include or exclude regions; "+
                     "left-click will crop to selection and middle-click will "+
                     "mask selection, or you can specify a selection option "+
                     "below. Click 'Next' below or right-click to proceed to "+
                     "the next star.")
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
        btn.add_callback('activated', self.last_star_cb)
        btn.set_tooltip("Go back to the previous star")
        box.add_widget(btn)
        
        # the next button moves on to the next star
        btn = Widgets.Button("Next")
        btn.add_callback('activated', self.next_star_cb)
        btn.set_tooltip("Accept and proceed to the next star")
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


    def build_gui(self, container):
        """
        Called when the plugin is invoked; sets up all the components of the GUI
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
        @returns:
            True. I'm not sure why.
        """
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True


    def start(self):
        """
        Called when the plugin is invoked, right after build_gui()
        """
        # stick our own canvas on top of the fitsimage canvas
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag='main-canvas')
        
        # clear the canvas
        self.canvas.delete_all_objects()
        
        # automatically select the first point and start
        self.resume()
        self.click1_cb(self.canvas, 1, *self.star0)


    def pause(self):
        """
        Called when the plugin is unfocused
        """
        self.canvas.ui_setActive(False)


    def resume(self):
        """
        Called when the plugin is refocused
        """
        # activate the GUI
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Locate the star labeled '1' by clicking.")


    def stop(self):
        """
        Called when the plugin is stopped
        """
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag('main-canvas')
        except:
            pass
        self.canvas.ui_setActive(False)
        self.fv.showStatus("")


    def redo(self):
        """
        Called whenever a new image is loaded
        """
        pass


    def __str__(self):
        return "MESOffset1"
        
        

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
        viewer.set_desired_size(400,400)
        viewer.enable_autozoom('on')
        viewer.enable_autocuts('on')
        output.append(viewer)
    return output


def readSBR():
    """
    Reads sf_a1689final.sbr and returns the position of the first active
    star as well as the relative positions of all the other stars in a list
    @returns:
        A tuple containing a list of float tuples (relative locations of stars)
        and a single float tuple (absolute location of first star)
    """
    # define variables
    star_list = []
    star0 = None
    
    # open and parse the file
    sbr = open("sf_a1689final.sbr", 'r')
    line = sbr.readline()
    while line != "":
        # for each line, get the important values and save them in star_list
        vals = [word.strip(" \n") for word in line.split(",")]
        if vals[0] == "C":
            newX, newY = imgXY_from_sbrXY((vals[1], vals[2]))
            if star0 == None:
                star_list.append((0, 0))
                star0 = (newX, newY)
            else:
                star_list.append((newX-star0[0],   # don't forget to shift it so star #0 is at the origin
                                  newY-star0[1]))
        line = sbr.readline()
        
    return star_list, star0


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
    SBRROT = 0  #XXX: What the heck is SBRROT?!
    fHoleX = 365.0 + (fX-300.0)*math.cos(SBRROT) - (fY-2660.0)*math.sin(SBRROT)
    fHoleY = 2580.0 + (fX-300.0)*math.sin(SBRROT) + (fY-2660.0)*math.cos(SBRROT)
    return (fHoleX, fHoleY)
    
    
def locate_star(approx, masks, image, calculator):
    """
    Finds the center of a star using the IQCalc peak location algorithm
    @param approx:
        A tuple of floats - the star should be within one sq_size of this.
    @param masks:
        A list of tuples of the form (x1, y1, x2, y2, kind) where kind is either
        'mask' or 'star' and everything else is floats. Each tuple in masks
        is one drag of the mouse that ommitted either its interior or its
        exterior
    @param image:
        The AstroImage containing the data necessary for this calculation
    @param calculator:
        The IQCalc object
    @returns:
        A tuple of two floats representing the actual location of the star
    @raises iqcalc.IQCalcError:
        If it is unable to find any desirable peaks
    """
    # start by cropping the image to get the data matrix
    data, x0,y0 = image.cutout_adjust(approx[0]-sq_size, approx[1]-sq_size,
                                      approx[0]+sq_size, approx[1]+sq_size)[0:3]
    threshold = 0
    data = data-threshold
    
    # omit data based on the masks
    for x1, y1, x2, y2, kind in masks:
        x1, y1, x2, y2 = (int(x1-approx[0]+sq_size), int(y1-approx[1]+sq_size),
                          int(x2-approx[0]+sq_size), int(y2-approx[1]+sq_size))
        mask = np.ones((2*sq_size, 2*sq_size))
        mask[x1:x2, y1:y2] = np.zeros((x2-x1, y2-y1))
        if kind == 'star':
            mask = 1-mask
        data = data*mask
        
    datast = ""
    for row in data:
        datast += '\n'
        for datum in row:
            datast += ' '
            if datum < 0:
                datast += '-'
            elif datum == 0:
                datast += '0'
            else:
                datast += '+'
    print datast
    
    x_sum = 0.
    y_sum = 0.
    tot = 0.
    for x in range(0, data.shape[0]):
        for y in range(0, data.shape[1]):
            x_sum += data[x, y]*x
            y_sum += data[x, y]*y
            tot += data[x, y]
    
    if tot == 0:
        raise iqcalc.IQCalcError("Data summed to zero")
    centroid = (x_sum/tot, y_sum/tot)
    
    # if there are any left, take the best one
    return (x0+centroid[0], y0+centroid[1])
    

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
    """
    if mod_2 == None:
        return '@{}:{}'.format(step, mod_1)
    else:
        return '@{}:{}:{}'.format(step, mod_1, mod_2)

#END

