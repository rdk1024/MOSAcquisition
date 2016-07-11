#
# mosplots.py -- extensions of util.plots.Plot to be used with MOS Acquisition
#
# Justin Kunimune
#



# ginga imports
from ginga.util import plots

# third-party imports
import numpy as np



class StarXYPlot(plots.Plot):
    """
    Plots a short series of stars on the X-Y plane as a scatterplot. Has the
    ability to mark various stars as active or inactive, which will influence
    the eventual fit calculations. Intended for use with the MESOffset plugins.
    """
    
    def __init__(self, star_list=None, offset=None, **kwargs):
        """
        Class constructor
        @param star_list:
            A list of float tuples representing the positions of the stars
        @param offset:
            A float tuple to offset star_list by, if star_list exists
        """
        super(StarXYPlot, self).__init__(**kwargs)
        
        if star_list != None:
            self.set_data(star_list, offset=offset)
        
        
    def set_data(self, star_list, offset=None):
        """
        Setter method for self.x_arr and self.y_arr
        @param star_list:
            A list of float tuples representing the positions of the stars
        @param offset:
            An optional float tuple to offset star_list by, if star_list exists
        @raises TypeError:
            If one or more stars could not be located
        """
        # create self.data by converting star_list to a numpy array
        if offset is not None:
            dx, dy = offset
        else:
            dx, dy = (0,0)
        self.data = np.array([[x+dx,y+dy] for x, y in star_list])
        
        #self.deleted represents which stars are deleted (defaults to none of them)
        self.deleted = []
        
        
    def delete(self, x, y):
        """
        Deletes the star at the given position by setting it to inactive
        @param x
            The float value for the x position
        @param y
            The float value for the y position
        """
        # iterate through data until you find this point,
        for i in self.data.size[0]:
            if self.data[i,0] == x and self.data[i,1] == y:
                if not i in self.deleted:
                    self.deleted.append(i)  # then put its index in self.deleted
                return
                
        # if no points matched, throw an error
        raise ValueError("The point ({}, {}) is not in self.data".format(x,y))
    
    
    def plot_x_y(self):
        """
        Reads the star positions from self.x_arr and self.y_arr, and plots them
        """
        #self.clear()
        self.plot(self.data[:,0], self.data[:,1], xtitle='X pos (pixels)',
                  ytitle='Y pos (pixels)', title='X verus Y plot',
                  linestyle='None', marker='+', color='black')
    
    
    
class YResidualPlot(plots.Plot):
    """
    Plots the Y residual against Y. What is Y residual? Good question. I have no
    idea. Intended for use with the MESOffset plugins.
    """
    
    def set_data(self, *args, **kwargs):
        pass
    
    def plot_residual(self, data=None):
        """
        Reads the Y residuals from self.??? and plots them
        """
        x = np.arange(0,10,0.01)
        y = np.sin(x)
        
        #self.clear()
        self.plot(x, y, xtitle='Y pos (pixels)',
                  ytitle='Y residual (???)', title='Y Residual plot',
                  linestyle='None', marker='+', color='black')

#END

