#
# mosplots.py -- extensions of util.plots.Plot to be used with MOS Acquisition
#
# Justin Kunimune
#



# ginga imports
from ginga.util import plots

# third-party imports
import numpy as np



class MOSPlot(plots.Plot):
    """
    A plot that deals with scatterplots based on some objects' estimated and
    measured positions. Available axes include x-position, y-position,
    x-residual, and y-residual.
    """
    
    def x_versus_y(self, data):
        """
        Plot the star positions on the x-y plane.
        """
        x = data[:, 0]
        y = data[:, 1]
        self.plot(x, y,
                  xtitle="X Position (pixels)",
                  ytitle="Y Position (pixels)",
                  title="Star Positions",
                  linestyle='None', marker='+')
    
    
    def x_residual(self, data):
        """
        Plot the x residual of this data against the x axis.
        x residual is defined as the third column substracted from the first_column
        """
        x = data[:, 0]
        x_res = data[:, 0] - data[:, 2]
        self.plot(x, x_res,
                  xtitle="X Position (pixels)",
                  ytitle="X Residual (pixels)",
                  title="X Residual by X-axis",
                  linestyle='None', marker='+')
    
    
    def y_residual(self, data):
        """
        Plot the y residual of this data against the y axis.
        y residual is defined as the fourth column subtracted from the second column
        """
        y = data[:, 1]
        y_res = data[:, 1] - data[:, 3]
        self.plot(y, y_res,
                  xtitle="Y Position (pixels)",
                  ytitle="Y Residual (pixels)",
                  title="Y Residual by Y-axis",
                  linestyle='None', marker='+')

#END

