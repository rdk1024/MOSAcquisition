#
# CurveFit.py -- Curve fitting plugin for fits viewer
# 
# Takeshi Inagaki (tinagaki@naoj.org)
# Eric Jeschke (eric@naoj.org)
#
import os.path

import numpy

import Gen2.fitsview.util.curve_fit as curvefit

from ginga.misc import CanvasTypes, Widgets
from ginga.gw.Plot import FigureCanvas
from ginga.util import plots
from ginga import GingaPlugin

class CurveFit(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(CurveFit, self).__init__(fv, fitsimage)

    def build_gui(self, container, future=None):
        # Paned container is just to provide a way to size the graph
        # to a reasonable size
        self.logger.debug('building curve fitting...')

        self.plot1 = plots.Plot(logger=self.logger,
                                width=200, height=600)

        class1 = curvefit.make_CurveFittingCanvas(FigureCanvas)
        class2 = curvefit.make_CurveFitting(class1)
        self.cf = class2(self.plot1.fig, logger=self.logger)
        cf = Widgets.wrap(self.cf)
        cf.resize(300, 700)
  
        vtop = Widgets.VBox()
        vtop.set_border_width(2)

        box = Widgets.Splitter(orientation='vertical')
        box.add_widget(cf)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        # create an empty box to adjust height of cure fitting. 
        vbox1 = Widgets.VBox()
        vbox1.set_border_width(100)

        # empty label
        self.label = Widgets.Label("")
        vbox1.add_widget(self.label)

        fr = Widgets.Frame("")
        fr.set_widget(vbox1)

        box.add_widget(fr)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=1)
        btns.add_widget(Widgets.Label(''), stretch=1)

        vtop.add_widget(box, stretch=1)
        vtop.add_widget(btns, stretch=0)
        container.add_widget(vtop, stretch=1)


    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True
 
    def curve_fitting(self, p, x_points, y_points, parabola):

        x = numpy.asarray(x_points)
        y = numpy.asarray(y_points)

        try:
            self.cf.clear_canvas()
            self.cf.set_axes()
            mx, my = self.cf.plot(x, y, parabola)
            self.cf.redraw()

            p.setvals(result='ok', mx=float(mx), my=float(my),
                      a=float(self.cf.qf.a), b=float(self.cf.qf.b),
                      c=float(self.cf.qf.c))

        except Exception as e:
            errmsg = "error in curve fitting: %s" % (str(e))
            self.logger.error(errmsg)
            p.setvals(result='error', errmsg=str(e))

        return 0

    def start(self):
        self.resume()

    def pause(self):
        pass
        
    def resume(self):
        pass
        
    def stop(self):
        self.fv.showStatus("")
        
    def redo(self):
        pass
    
    def __str__(self):
        return 'curvefit'
    
# END
