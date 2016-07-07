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

# third-party imports
import numpy as np



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
        # superclass constructor defines self.fv, self.fitsimage, and self.logger
        super(MESOffset1, self).__init__(fv, fitsimage)
        fv.set_titlebar("MES Offset 1")

        # initialize some constants
        self.title_font = self.fv.getFont('sansFont', 18)
        self.body_font = self.fv.getFont('sansFont', 10)
        self.sq_size = 30
        self.colors = ('green','red','blue','yellow','magenta','cyan','orange')

        # and some attributes
        self.click_history = [] # places we've clicked
        self.click_index = -1   # index of the last click
        self.current_star = 0  # index of the current star
        # read the given SBR file to get the star positions
        self.star_list, self.star0 = readSBR()
        # create the list of thumbnails that will go in the GUI
        self.thumbnails = create_viewer_list(len(self.star_list), self.logger)
        
        # now set up the ginga.canvas.types.layer.DrawingCanvas self.canvas,
        # which is necessary to draw on the image
        self.dc = fv.getDrawClasses()
        self.canvas = self.dc.DrawingCanvas()
        self.canvas.enable_draw(False)
        self.canvas.set_callback('cursor-down', self.click_cb)  # left-click callback
        self.canvas.set_callback('draw-down', self.step2_cb) # right-click callback
        self.canvas.set_surface(self.fitsimage)
        self.canvas.register_for_cursor_drawing(self.fitsimage)
        self.canvas.name = 'MOSA-canvas'



    def step2_cb(self, _, __=None, ___=None, ____=None):
        """
        Responds to the next button by proceeding to the next step
        """
        self.stack.set_index(self.stack.get_index()+1)
        self.fv.showStatus("Crop each star image by clicking and dragging")
        self.canvas.clear_callback('draw-down')
        self.canvas.set_callback('draw-down', self.next_star_cb)
        self.zoom_in_on_current_star()
        
    
    def next_star_cb(self, _, __=None, ___=None, ____=None):
        """
        Responds to the next button by proceeding to the next star
        """
        # if there is no next star, finish up
        self.current_star += 1
        if self.current_star >= len(self.star_list):
            self.fitsimage.center_image()
            self.fitsimage.zoom_fit()
            self.close()
            return
            
        # if there is one, focus in on it
        self.zoom_in_on_current_star()
    
    
    def click_cb(self, canvas, event, x, y):
        """
        Responds to a click on the screen
        @param canvas:
            The DrawingCanvas object that called this method
        @param event:
            The PointEvent object that contains all useful information about the click
        @param x:
            The x coordinate of the click
        @param y:
            The y coordiante of the click
        """
        self.click_index += 1
        if self.click_index < len(self.click_history):
            self.click_history[self.click_index] = (x,y)
        else:
            self.click_history.append((x,y))
        self.select_point(self.click_history[self.click_index])
            
            
    def undo_cb(self, _):
        """
        Responds to the undo button by going back one click (if possible)
        """
        if self.click_index > 0:
            self.click_index -= 1
            self.select_point(self.click_history[self.click_index])
    
    
    def redo_cb(self, _):
        """
        Responds to the redo button by going forward one click (if possible)
        """
        if self.click_index < len(self.click_history)-1:
            self.click_index += 1
            self.select_point(self.click_history[self.click_index])
    
    
    def select_point(self, point):
        """
        Sets a point as the current location of star #1,
        draws squares where it thinks all the stars are accordingly,
        and updates all thumbnails
        @param point:
            An int tuple containing the location of star #1
        """
        # define some variables before iterationg through the stars
        x, y = point
        src_image = self.fitsimage.get_image()
        self.canvas.enable_draw(True)
        color = self.colors[self.click_index%len(self.colors)]   # cycles through all the colors
        for i, viewer in enumerate(self.thumbnails):
            dx, dy = self.star_list[i]
        
            # first, draw squares and numbers
            self.canvas.add(self.dc.CompoundObject(
                                self.dc.SquareBox(x+dx, y+dy,
                                                  self.sq_size,
                                                  color=color),
                                self.dc.Text(x+dx+self.sq_size+1, y+dy,
                                             str(i+1),
                                             color=color)))

            # then, update the little pictures
            x1, y1, x2, y2 = (x-self.sq_size+dx, y-self.sq_size+dy,
                              x+self.sq_size+dx, y+self.sq_size+dy)
            cropped_data = src_image.cutout_adjust(x1,y1,x2,y2)[0]
            viewer.set_data(cropped_data)
            self.fitsimage.copy_attributes(viewer,
                                           ['transforms','cutlevels','rgbmap'])
            
        self.canvas.enable_draw(False)
        
        
    def zoom_in_on_current_star(self):
        """
        Set the position and zoom level on fitsimage such that the user can
        only see the star at index self.current_star
        """
        # get the final click location and offset it based on idx
        finalX, finalY = self.click_history[self.click_index]
        offsetX, offsetY = self.star_list[self.current_star]
        
        # then move and zoom
        self.fitsimage.set_pan(finalX + offsetX, finalY + offsetY)
        self.fitsimage.zoom_to(4)
        
        
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
        btn.add_callback('activated', self.undo_cb)
        btn.set_tooltip("Undo a single click (if a click took place)")
        box.add_widget(btn)

        # the redo button goes forward
        btn = Widgets.Button("Redo")
        btn.add_callback('activated', self.redo_cb)
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
        num_img = len(self.star_list)   # total number of alignment stars
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
        btn.add_callback('activated', self.undo_cb)
        btn.set_tooltip("Undo a single click (if a click took place)")
        box.add_widget(btn)

        # the redo button goes forward
        btn = Widgets.Button("Redo")
        btn.add_callback('activated', self.redo_cb)
        btn.set_tooltip("Undo an undo action (if an undo action took place)")
        box.add_widget(btn)

        # the clear button nullifies all crops
        btn = Widgets.Button("Clear")
        btn.add_callback('activated', lambda w: self.canvas.delete_all_objects())
        btn.set_tooltip("Erase all marks on the canvas")
        box.add_widget(btn)
        
        # the next button moves on to the next star
        btn = Widgets.Button("Next")
        btn.add_callback('activated', self.next_star_cb)
        btn.set_tooltip("Accept and proceed to step 2")
        box.add_widget(btn)
        
        # make a box for a combobox+label combo
        box = Widgets.VBox()
        box.set_spacing(3)
        gui.add_widget(box)
        lbl = Widgets.Label("Selection Mode:")
        box.add_widget(lbl)
        
        # last is the combobox of selection options
        com = Widgets.ComboBox()
        com.append_text("Automatic")
        com.append_text("Star Region")
        com.append_text("Mask Region")
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
        self.click_cb(None, None, *self.star0)


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

#END

