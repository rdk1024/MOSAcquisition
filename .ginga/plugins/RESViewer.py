#
# RESViewer.py -- a ginga plugin to review the results of MESLocate
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import math
import sys

# ginga imports
from ginga import GingaPlugin
from ginga.gw import Widgets, Viewers, Plot



# constants
# the arguments passed in to the outer script
argv = sys.argv



class RESViewer(GingaPlugin.LocalPlugin):
    """
    A custom LocalPlugin for ginga that takes some data about some objects'
    positions, graphs them, and asks the user to modify the data if necessary.
    Intended for use as part of the MOS Acquisition software for aligning
    MOIRCS.
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
        super(RESViewer, self).__init__(fv, fitsimage)
        fv.set_titlebar("MOIRCS Acquisition")

        # initializes some class constants:
        self.title_font = self.fv.getFont('sansFont', 18)
        self.body_font = self.fv.getFont('sansFont', 10)
        
        # and some attributes
        self.data = readCOO()
        
        # now sets up the ginga.canvas.types.layer.DrawingCanvas self.canvas,
        # which is necessary to draw on the image:
        self.dc = fv.get_draw_classes()
        self.canvas = self.dc.DrawingCanvas()
        self.canvas.enable_draw(False)
        self.set_callbacks()
        self.canvas.set_surface(self.fitsimage)
        self.canvas.register_for_cursor_drawing(self.fitsimage)
        self.canvas.name = 'MOSA-canvas'
        
        
        
    def exit_cb(self, *args):
        self.close()
        self.fv.quit()
        
        
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
        btn = Widgets.Button("Exit")
        btn.add_callback('activated', self.exit_cb)
        out.add_widget(btn)

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
        
        # set the initial status message
        self.fv.showStatus("Analyze and trim the data.")
        
        # stick our own canvas on top of the fitsimage canvas
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag='main-canvas')
        
        # clear the canvas
        self.canvas.delete_all_objects()


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
        return "RESViewer"
    
    
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


def readRES():
    """
    Read the RES file and return the data within as a list of float tuples
    @returns:
        A list of tuples of floats representing (?, IDK, What, the important columns, R, ?)
    """
    # define variables
    val_list = []
    
    # try to open the file
    try:
        res = open(argv[1], 'r')
    except IOError:
        try:
            res = open("sbr_elaisn1rev_starholemask.res")
        except IOError:
            return [(0, 0, 0, 0, 0, 0, 0, 0)]
    
    # now parse it!
    line = res.readline()
    while line != "":
        # for each line, get the important values and save them in val_list
        vals = [float(word) for word in line.split()]
        val_list.append(vals)
        line = res.readline()
        
    return val_list

#END

