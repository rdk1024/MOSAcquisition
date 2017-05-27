#
# mosPlugin.py -- a base for all ginga plugins that work with MOS Acquisition
# Should not be instantiated
#
# Justin Kunimune
#



# ginga imports
from __future__ import absolute_import
from ginga import GingaPlugin
from ginga.gw import GwHelp, Widgets



class MESPlugin(GingaPlugin.LocalPlugin):
    """
    Any custom LocalPlugin for ginga that is intended for use as part of the
    MOS Acquisition software for aligning MOIRCS.
    """
    
    HEADER_FONT = GwHelp.get_font('sansFont', 18)
    NORMAL_FONT = GwHelp.get_font('sansFont', 12)
    BODY_FONT   = GwHelp.get_font('sansFont', 10)
    MONO_FONT   = GwHelp.get_font('Monospace', 12)
    
    
    
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
        super(MESPlugin, self).__init__(fv, fitsimage)
        fv.set_titlebar("MOIRCS Acquisition")
        
        # now sets up the ginga.canvas.types.layer.DrawingCanvas self.canvas,
        # which is necessary to draw on the image:
        self.dc = fv.get_draw_classes()
        self.canvas = self.dc.DrawingCanvas()
        self.canvas.enable_draw(False)
        self.canvas.set_surface(self.fitsimage)
        self.canvas.register_for_cursor_drawing(self.fitsimage)
        self.canvas.name = type(self).__name__+'-canvas'
        
        
        
    def clear_canvas(self, keep_objects=False,
                           keep_callbacks=False,
                           keep_zoom=False):
        """
        Reset the ImageViewCanvas by deleting objects and callbacks
        @param keep_objects:
            If True, canvas objects will not be deleted
        @param keep_callbacks:
            If True, canvas callbacks will not be cleared
        @param keep_zoom:
            If True, fitsimage zoom level and position will not be reset
        """
        if not keep_objects:
            self.canvas.delete_all_objects()
        if not keep_callbacks:
            for button in ('cursor', 'panset', 'draw'):
                for event in ('-up', '-down'):
                    self.canvas.clear_callback(button+event)
        if not keep_zoom:
            self.fitsimage.zoom_fit()
            self.fitsimage.center_image()
    
    
    def build_gui(self, container, future=None):
        """
        Called when the plugin is invoked; sets up all the components of the GUI
        One of the required LocalPlugin methods
        @param container:
            The widget.Box this GUI must be added into
        """
        # create the outer Box that will hold the GUI and the close button
        out = Widgets.VBox()
        out.set_border_width(4)
        container.add_widget(out, stretch=True)
        
        # create the inner box that will contain the stack of GUIs
        box, box_wrapper, orientation = Widgets.get_oriented_box(container,
                                                                 fill=True)
        box.set_border_width(4)
        box.set_spacing(3)
        out.add_widget(box_wrapper, stretch=True)
        
        # the rest is a stack of GUIs for each step, as decided by the subclass
        stk = Widgets.StackWidget()
        self.stack_guis(stk, orientation)
        box.add_widget(stk, stretch=True)
        self.stack = stk
        
        # end is an HBox that comes at the very end, after the rest of the GUIs
        end = Widgets.HBox()
        end.set_spacing(2)
        out.add_widget(end)
        
        # throw in a close button at the very end, just in case
        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        end.add_widget(btn)
        end.add_widget(Widgets.Label(''), stretch=True)
    
    
    def start(self, future=None):
        """
        Called when the plugin is first invoked, right after build_gui()
        One of the required LocalPlugin methods
        """
        # stick our own canvas on top of the fitsimage canvas
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag='MOSA-canvas')
        
        # clear the canvas
        self.canvas.delete_all_objects()
    
        # Save a reference to the "future" object so we MESInterface
        # can use it later on.
        self.callerInfo = future

    def close(self):
        """
        Called when the plugin is closed
        One of the required LocalPlugin methods
        @returns:
            True. I'm not sure why.
        """
        self.fv.stop_local_plugin(self.chname, str(self))
        return True
    
    
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
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Calculate the offset values to align MOIRCS")
    
    
    def stop(self):
        """
        Called when the plugin is stopped
        One of the required LocalPlugin methods
        """
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag('MOSA-canvas')
        except:
            pass
        self.canvas.ui_setActive(False)
        self.clear_canvas()
        
        # call the termination event, if you have one
        if hasattr(self, 'terminate'):
            self.terminate.set()
    
    
    def redo(self):
        """
        Called whenever a new image is loaded
        One of the required LocalPlugin methods
        """
        pass
    
    
    def __str__(self):
        return type(self).__name__

#END

