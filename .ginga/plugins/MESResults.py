#
# MESResults.py -- a ginga plugin to display results from mesoffset2 and 3
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import sys

# ginga imports
from ginga import GingaPlugin
from ginga.gw import Widgets, Viewers, Plot



# constants
# the arguments passed in to the outer script
argv = sys.argv
fits_image = argv[1]
input_res = argv[2]



class MESResults(GingaPlugin.LocalPlugin):
    """
    A custom LocalPlugin for ginga that helps to visualize results from geomap
    by drawing arrows from the stars' initial positions to their final
    positions. Intended for use as part of the MOS Acquisition software for
    aligning MOIRCS.
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
        super(MESResults, self).__init__(fv, fitsimage)
        fv.set_titlebar("MOIRCS Acquisition")
        
        # initializes some class constants:
        self.title_font = self.fv.getFont('sansFont', 18)
        self.header_font = self.fv.getFont('sansFont', 14)
        self.body_font = self.fv.getFont('sansFont', 10)
        
        # and some attributes
        
        # now sets up the ginga.canvas.types.layer.DrawingCanvas self.canvas,
        # which is necessary to draw on the image:
        self.dc = fv.get_draw_classes()
        self.canvas = self.dc.DrawingCanvas()
        self.canvas.enable_draw(False)
        self.canvas.set_surface(self.fitsimage)
        self.canvas.register_for_cursor_drawing(self.fitsimage)
        self.canvas.name = 'MOSA-canvas'
    
    
    def exit_cb(self, *args, **kwargs):
        """
        Responds to the 'Exit' button by closing Ginga\
        """
        self.close()
        self.fv.quit()
    
    
    def make_gui_5(self, orientation='vertical'):
        """
        Construct a GUI for the fifth step: viewing the results
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        @returns:
            A Widgets.Box object containing all necessary buttons, labels, etc.
        """
        # start by creating the container
        gui = Widgets.Box(orientation=orientation)
        gui.set_spacing(4)
        
        # create a label to title this step
        lbl = Widgets.Label("View Results")
        lbl.set_font(self.title_font)
        gui.add_widget(lbl)

        # fill a text box with brief instructions and put in in an expander
        exp = Widgets.Expander(title="Instructions")
        gui.add_widget(exp)
        txt = Widgets.TextArea(wrap=True, editable=False)
        txt.set_font(self.body_font)
        txt.set_text("Look at the results. The vectors represent the "+
                     "displacement of the stars from their corresponding "+
                     "holes. Star/hole pairs with displacements of less than "+
                     "0.5 pixels are shown in blue. Press 'Exit' below when "+
                     "you are done.")
        exp.set_widget(txt)
        
        # put in the Exit button, which is reall just a close button
        btn = Widgets.Button("Exit")
        btn.add_callback('activated', lambda w: self.close())
        gui.add_widget(btn)
        
        # space gui appropriately and return it
        gui.add_widget(Widgets.Label(""), stretch=True)
        return gui
        

    def build_gui(self, container):
        """
        Called when the plugin is invoked; sets up all the components of the GUI
        One of the required LocalPlugin methods
        @param container:
            The widget.VBox this GUI will be added into
        """
        # create the outer Box that will hold the GUI and the close button
        out = Widgets.VBox()
        out.set_border_width(4)
        container.add_widget(out, stretch=True)
        
        # create the inner box that will contain the stack of GUIs
        box, box_wrapper, orientation = Widgets.get_oriented_box(container)
        box.set_border_width(4)
        box.set_spacing(3)
        out.add_widget(box_wrapper, stretch=True)
        
        # the rest is specific to step 5
        box.add_widget(self.make_gui_5(orientation))

        # end is an HBox that comes at the very end, after the rest of the GUIs
        end = Widgets.HBox()
        end.set_spacing(2)
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
        # TODO: set the cuts to -20, 200 or something
        # set the initial status message
        self.fv.showStatus("Inspect the results.")
        
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
        return "MESResults"
    


    @staticmethod
    def readInputFile():
        """
        Read the COO file and return the data within as a numpy array
        @returns:
            A list of tuples of floats representing (x_in, y_in, x_out, y_out)
        """
        # define variables
        val_list = []
        
        # try to open the file
        try:
            coo = open(input_coo, 'r')
        except IOError:
            try:
                coo = open("sbr_elaisn1rev_starmask.coo")
            except IOError:
                return np.array([[0., 0., 0., 0.]])
        
        # now parse it!
        line = coo.readline()
        while line != "":
            # for each line, get the important values and save them in val_list
            vals = [float(word) for word in line.split()]
            val_list.append(vals)
            line = coo.readline()
            
        return np.array(val_list)
    
#END

