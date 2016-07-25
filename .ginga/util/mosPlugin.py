#
# mosplugin.py -- defines a base for all plugins that work with MOS Acquisition
# Should not be instantiated
#
# Justin Kunimune
#



# ginga imports
from ginga import GingaPlugin
from ginga.gw import GwHelp, Widgets



class MESPlugin(GingaPlugin.LocalPlugin):
    """
    Any custom LocalPlugin for ginga that is intended for use as part of the
    MOS Acquisition software for aligning MOIRCS.
    """
    
    title_font  = GwHelp.get_font('Monospace', 18)
    header_font = GwHelp.get_font('Monospace', 14)
    body_font   = GwHelp.get_font('Monospace', 10)
    
    
    
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
        
        
        
    def build_gui(self, container):
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
        box.add_widget(stk)
        self.stack = stk
        
        # space the GUI appropriately
        box.add_widget(Widgets.Label(""), stretch=True)

        # end is an HBox that comes at the very end, after the rest of the GUIs
        end = Widgets.HBox()
        end.set_spacing(2)
        out.add_widget(end)
            
        # throw in a close button at the very end, just in case
        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        end.add_widget(btn)
        end.add_widget(Widgets.Label(''), stretch=True)
        
        
    def build_specific_gui(self, stack, orientation='vertical'):
        """
        Combine the GUIs necessary for this particular plugin
        Must be implemented for each MESPlugin
        @param stack:
            The stack in which each part of the GUI will be stored
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        """
        raise NotImplementedError("make_specific_gui() must be implemented "+
                                  "for every subclass of mosplugin.MESPlugin")
        
    
    def start(self):
        """
        Called when the plugin is first invoked, right after build_gui()
        One of the required LocalPlugin methods
        """
        # stick our own canvas on top of the fitsimage canvas
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag='main-canvas')
        
        # clear the canvas
        self.canvas.delete_all_objects()
    
    
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
        # activate the GUI
        self.canvas.ui_setActive(True)


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
        return type(self).__name__

#END

