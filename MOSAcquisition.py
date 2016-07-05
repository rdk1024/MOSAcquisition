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

# third-party imports
import astroplan

class MOSAcquisition(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        """
        class constructor
        @param fv:
            a reference to the GingaShell object (reference viewer)
        @param fitsimage:
            a reference to the specific ImageViewCanvas object associated with the channel
            on which the plugin is being invoked
        """
        # superclass constructor defines self.fv, self.fitsimage, and self.logger
        super(MOSAcquisition, self).__init__(fv, fitsimage)

        # initialize some constants
        self.title_font = self.fv.getFont("sansFont", 18)
        self.body_font = self.fv.getFont("sansFont", 10)
        self.sq_size = 20

        # and some attributes
        self.click_history = []
        self.click_index = -1
        
        # create the list of thumbnails that will go in the GUI
        self.thumbnails = []
        for i in range(8):
            viewer = Viewers.CanvasView(logger=self.logger)
            viewer.set_desired_size(300,300)
            viewer.enable_autozoom('off')
            viewer.enable_autocuts('off')
            viewer.zoom_to(3)
            viewer.get_settings().getSetting('zoomlevel').add_callback('set',self.zoomset,viewer)
            viewer.set_cmap(self.fv.cm)
            viewer.set_imap(self.fv.im)
            viewer.set_callback('none_move',self.detailxy)
            viewer.set_bg(0.4, 0.4, 0.4)
            viewer.set_name("Bob")
            bd = viewer.get_bindings()
            bd.enable_pan(True)
            bd.enable_zoom(True)
            bd.enable_cuts(True)
            viewer.configure(300,300)
            self.thumbnails.append(viewer)
        
        # now set up the ginga.canvas.types.layer.DrawingCanvas self.canvas,
        # which is necessary to draw on the image
        self.dc = fv.getDrawClasses()
        self.canvas = self.dc.DrawingCanvas()
        self.canvas.enable_draw(False)
        self.canvas.set_drawtype('squarebox', color='white') #TODO: find out about different colors
        self.canvas.set_callback('cursor-down', self.select_point)  # left-click callback
        self.canvas.set_callback('draw-down', lambda w,x,y,z: self.close()) # right-click callback
        self.canvas.set_surface(self.fitsimage)
        self.canvas.register_for_cursor_drawing(self.fitsimage)
        self.canvas.name = 'MOSA-canvas'
        
        
    def zoomset(self, setting, zoomlevel, fitsimage):   #XXX: do I need this?
        scalefactor = fitsimage.get_scale()
        self.logger.debug("scalefactor = %.2f" % (scalefactor))
        text = self.fv.scale2text(scalefactor)
        self.wdetail.zoom.set_text(text)
        
        
    def detailxy(self, canvas, button, data_x, data_y): #XXX: this too
        """Motion event in the pick fits window.  Show the pointing
        information under the cursor.
        """
        if button == 0:
            # TODO: we could track the focus changes to make this check
            # more efficient
            fitsimage = self.fv.getfocus_fitsimage()
            # Don't update global information if our fitsimage isn't focused
            if fitsimage != self.fitsimage:
                return True

            # Add offsets from cutout
            data_x = data_x + self.pick_x1
            data_y = data_y + self.pick_y1

            return self.fv.showxy(self.fitsimage, data_x, data_y)


    def select_point(self, canvas, event, x, y):
        """
        Resopnds to a click on the screen
        @param canvas:
            The DrawingCanvas object that called this method
        @param event:
            The PointEvent object that contains all useful information about the click
        @param x:
            The x coordinate of the click
        @param y:
            The y coordiante of the click
        """
        # first, draw a square
        self.canvas.enable_draw(True)
        canvas.draw_start(None, None, x, y, self.fitsimage)
        canvas.draw_stop(None, None, x+self.sq_size, y, self.fitsimage)
        self.canvas.enable_draw(False)
        
        # then save this point
        self.click_history.append((x,y))
        self.click_index += 1
        
        # finally, update the smaller pictures
        src_image = self.fitsimage.get_image()
        for viewer in self.thumbnails:
            x1, y1, x2, y2 = (x-self.sq_size, y-self.sq_size,
                              x+self.sq_size, y+self.sq_size)
            cropped_data = src_image.cutout_adjust(x1,y1,x2,y2)[0]
            viewer.set_data(cropped_data)
            self.fitsimage.copy_attributes(viewer, ['transforms','cutlevels','rgbmap'])


    def build_gui(self, container):
        """
        Called when the plugin is invoked; setus up all the components of the GUI
        @param container:
            the widget.VBox this GUI will be added into
        """
        # create the outer VBox that will hold everything else
        out = Widgets.VBox()
        out.set_border_width(4)
        container.add_widget(out)
        
        # now create the VBox to hold the majority of the commands,
        # the ScrollWidget that contains that box,
        # and a string to specify whether this is horizontal or vertical
        gui, gui_wrapper, orientation = Widgets.get_oriented_box(container)
        gui.set_border_width(4)
        gui.set_spacing(3)
        out.add_widget(gui_wrapper)
        
        # create a label to title this step
        lbl = Widgets.Label("Step 1:")
        lbl.set_font(self.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Left click on the star labeled '#1'. The other stars should appear in the boxes below. Click again to select another position. Click 'Next' when you are satisfied with your location.")
        gui.add_widget(txt)

        # create a box to group the controls together
        box = Widgets.HBox()
        box.set_spacing(3)
        gui.add_widget(box)

        # the undo button goes back a step
        btn = Widgets.Button("Undo")
        #TODO
        box.add_widget(btn)

        # the redo button goes forward
        btn = Widgets.Button("Redo")
        #TODO
        box.add_widget(btn)

        # the clear button erases the canvas
        btn = Widgets.Button("Clear")
        btn.add_callback('activated', lambda w: self.canvas.delete_all_objects())
        box.add_widget(btn)
        
        # the next button moves on to step 2
        btn = Widgets.Button("Next")
        btn.add_callback('activated', lambda w: self.close())
        box.add_widget(btn)
        
        # lastly, we need the zoomed-in images
        frm = Widgets.Frame()
        gui.add_widget(frm)
        box = Widgets.VBox()
        box.set_spacing(3)
        frm.set_widget(box)
        
        # these are the images we put in the frame
        row_len = 3
        for i in range(0, 8, row_len):
            row = Widgets.HBox()
            box.add_widget(row)
            # arrange them in 8/row_len rows of row_len
            for j in range(i, i+row_len):
                pic = Viewers.GingaViewerWidget(viewer=self.thumbnails[j])
                pic.resize(300,300)
                row.add_widget(pic)

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
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag='leedle leedle leedle lee')

        self.canvas.delete_all_objects()
        self.resume()


    def pause(self):
        """
        Called when the plugin is unfocused
        """
        self.canvas.ui_setActive(False)


    def resume(self):
        """
        Called when the plugin is refocused
        """
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a ruler with the right mouse button")


    def stop(self):
        """
        Called when the plugin is stopped
        """
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag('leedle leedle leedle lee')
        except:
            pass
        self.canvas.ui_setActive(False)
        self.fv.showStatus("")


    def redo(self):
        """
        Called whenever a new image is loaded
        @returns:
            Either True or None...? I don't even...
        """
        for viewer in self.thumbnails:
            self.fitsimage.copy_attributes(viewer,
                                           ['transforms', 'cutlevels',
                                           'rgbmap'])


    def __str__(self):
        return "MOSAcquisition"

#END

