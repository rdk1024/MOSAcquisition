#
# MESResults.py -- a ginga plugin to display results from mesoffset2 and 3
# Works in conjunction with mesoffset scripts for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import math
import sys

# local imports
from util.mosplugin import MESPlugin

# ginga imports
from ginga.gw import Widgets, Viewers, Plot

# third-party imports
import numpy as np



# constants
# the arguments passed in to the outer script
argv = sys.argv
fits_image = argv[1]
input_res = argv[2]
# vector length
scale = 400



class MESResults(MESPlugin):
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
        # LocalPlugin constructor defines self.fv, self.fitsimage, self.logger;
        # MESPlugin constructor defines self.dc, self.canvas, and some fonts
        super(MESResults, self).__init__(fv, fitsimage)
        
        # the only attribute is the data
        self.data = self.read_input_file()
    
    
    
    def build_specific_gui(self, stack, orientation='vertical'):
        """
        Combine the GUIs necessary for this particular plugin
        Must be implemented for each MESPlugin
        @param stack:
            The stack in which each part of the GUI will be stored
        @param orientation:
            Either 'vertical' or 'horizontal', the orientation of this new GUI
        """
        stack.add_widget(self.make_gui_5(orientation))
        
    
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
                     "residuals of the geomap model. Residuals less than 0.5 "+
                     "are shown in green, and residuals greater than 1.0 are "+
                     "in red. Press 'Exit' below when you are done.")
        exp.set_widget(txt)
        
        # put in the Exit button, which is reall just a close button
        btn = Widgets.Button("Exit")
        btn.add_callback('activated', self.exit_cb)
        btn.set_tooltip("Close Ginga")
        gui.add_widget(btn)
        
        # space gui appropriately and return it
        gui.add_widget(Widgets.Label(""), stretch=True)
        return gui
        
        
    def start(self):
        """
        Called when the plugin is invoked, right after build_gui()
        One of the required LocalPlugin methods
        """
        super(MESResults, self).start()
        
        # adjust the cut levels to make the arrows easier to see
        self.fitsimage.get_settings().set(autocut_method='zscale')
        
        # set the initial status message
        self.fv.showStatus("Inspect the results.")
        
        # draw the vectors
        self.draw_results()
        
    
    def draw_results(self):
        """
        Draws the results from self.data onto the canvas in the form of vectors
        """
        for row in self.data:
            startX = row[0]
            startY = row[1]
            endX = row[0] + scale*row[2]
            endY = row[1] + scale*row[3]
            magnitude = math.hypot(row[2], row[3])
            if magnitude <= 0.5:
                color = 'green'
            elif magnitude <= 1.0:
                color = 'yellow'
            else:
                color = 'red'
            self.canvas.add(self.dc.Line(startX, startY, endX, endY,
                                         color=color, arrow='end', showcap=1,
                                         alpha = 0.7))
            self.canvas.add(self.dc.Text((startX+endX)/2, (startY+endY)/2,
                                         "{:,.1f}p".format(magnitude),
                                         color=color))
        
        
    def exit_cb(self, *args, **kwargs):
        """
        Responds to the 'Exit' button by closing Ginga
        """
        self.close()
        self.fv.quit()
    
    
    
    @staticmethod
    def read_input_file():
        """
        Read the RES file and return the data within as a numpy array
        @returns:
            A numpy array with four columns: x0, y0, dx, dy representing the
            hole positions, and the residuals from the geomap model
        """
        # try to open the file
        try:
            res = open(input_res, 'r')
        except IOError:
            try:
                res = open("sbr_elaisn1rev_starholemask.res")
            except IOError:
                return np.array([[0., 0., 0., 0.]])
        
        val_array = []
        
        # now parse it!
        line = res.readline()
        while line != "":
            # for each line, get the important values and save them in val_array
            if line[0] != '#' and line[0] != '\n':
                values = [float(word) for word in line.split()]
                val_array.append([values[0], values[1], values[6], values[7]])
            line = res.readline()
            
        return np.array(val_array)
    
#END

