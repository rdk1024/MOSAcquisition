#
# mosplots.py -- extensions of util.plots.Plot to be used with MOS Acquisition
#
# Justin Kunimune
#



# ginga imports
from ginga.util import plots



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
    
    
    def residual(self, x_observe, x_calculate, active, var_name=""):
        """
        Plot the residual of this data against the real value.
        Residual is defined as the difference between the calculated value of
        xref and the observed value of xref.
        @param x_observe:
            A numpy array of the observed values of this variable
        @param x_calculate:
            A numpy array of the calculated values of this variable
        @param active:
            A numpy array representing which data are active, and which are not
        @param var_name:
            The name of this variable, if it has one
        """
        # then plot reference values by residual values
        self.plot(x_observe, x_calculate - x_observe,
                  xtitle="{0} Position (pixels)".format(var_name),
                  ytitle="{0} Residual (pixels)".format(var_name),
                  title="{0} Residual by {0}-axis".format(var_name),
                  linestyle='None', marker='+', color='blue')

#END

