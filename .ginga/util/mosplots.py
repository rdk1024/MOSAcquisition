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
    
    def residual(self, z_observe, z_calculate, active, var_name=""):
        """
        Plot the residual of this data against the real value.
        Residual is defined as the difference between the calculated value of
        zref and the observed value of zref.
        @param z_observe:
            A numpy array of the observed values of this variable
        @param z_calculate:
            A numpy array of the calculated values of this variable
        @param active:
            A numpy array representing which data are active, and which are not
        @param var_name:
            The name of this variable, if it has one
        """
        #separate the active and inactive data
        inactive = np.logical_not(active)
        active_x = z_observe[np.nonzero(active)]
        active_y = (z_calculate - z_observe)[np.nonzero(active)]
        inactive_x = z_observe[np.nonzero(inactive)]
        inactive_y = (z_calculate - z_observe)[np.nonzero(inactive)]
        
        # then plot reference values by residual values
        self.add_axis()
        self.clear()
        self.plot(active_x, active_y,
                  linestyle='None', marker='+', color='blue')
        self.plot(inactive_x, inactive_y,
                  linestyle='None', marker='x', color='grey',
                  xtitle="{0} Position (pixels)".format(var_name),
                  ytitle="{0} Residual (pixels)".format(var_name),
                  title="{0} Residual by {0}-axis".format(var_name))

#END

