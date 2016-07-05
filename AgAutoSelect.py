#
# AgAutoSelect.py -- A VGW plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
from ginga.misc import Bunch
import Catalogs
import astro.radec as radec
from Gen2.fitsview.util import g2catalog


class AgAutoSelect(Catalogs.Catalogs):

    def __init__(self, fv, fitsimage):
        super(AgAutoSelect, self).__init__(fv, fitsimage)

        # thickness of the marked rings for FOV
        self.ring_thickness = 2
        self.colors = Bunch.Bunch(inst='magenta', outer='red', inner='red',
                                  vignette='green', probe='cyan')
        self.probe_vignette_radius = None

    def build_gui(self, container, future=None):
        super(AgAutoSelect, self).build_gui(container, future=future)
        
        # add blacklist feature
        self.table.add_operation("add to blacklist", self.add_blacklist)
        self.table.add_operation("rm from blacklist", self.rem_blacklist)
        self.table.btn['oprn'].append_text("add to blacklist")
        self.table.btn['oprn'].append_text("rm from blacklist")
        self.table.btn['oprn'].set_index(0)

    def start(self, future):
        self.callerInfo = future
        super(AgAutoSelect, self).start()

    def get_canvas(self):
        return self.canvas

    def plot(self, future, plotObj):
        self.callerInfo = future
        # Gather parameters
        p = future.get_data()

        self.clearAll()
        self.reset()

        # Draw the graphics for this particular foci or instrument
        plotObj.draw(self)
        
        # If there is a starlist waiting to be plotted, do it
        if p.starlist:
            if (self.limit_stars_to_area and 
                hasattr(plotObj, 'filter_results')):
                starlist = plotObj.filter_results(p.starlist)
            else:
                starlist = p.starlist
            p.starlist = starlist
        else:
            p.starlist = []
            
        self.probe_vignette_radius = p.get('probe_vignette_radius', None)

        # Update GUI
        self.update_catalog(p.starlist, p.info)

        # Select top star
        if len(p.starlist) > 0:
            self.table.show_selection(p.starlist[0])
        
        #self.fv.update_pending(timeout=0.25)

    def highlight_object(self, obj, tag, color, redraw=True):
        x = obj.objects[0].x
        y = obj.objects[0].y
        delta = 10
        radius = obj.objects[0].radius + delta

        hilite = self.dc.CompoundObject()
        # TODO: we have to add this to the canvas first--fix this
        self.hilite.add_object(hilite)
        
        hilite.add_object(self.dc.Circle(x, y, radius,
                                         linewidth=4, color=color))
        # TODO: consider calling back into the plotObj for a custom
        # highlight
        if self.probe_vignette_radius is not None:
            hilite.add_object(self.dc.Circle(x, y, self.probe_vignette_radius,
                                             linewidth=2, color='green',
                                             linestyle='dash'))
        if redraw:
            self.canvas.update_canvas()
        

    def release_caller(self):
        self.callerInfo.resolve(0)
        
    def close(self):
        self.ok()
        
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True
        
    def ok(self):
        self.logger.info("OK clicked.")
        p = self.callerInfo.get_data()

        p.result = 'ok'
        selected = self.table.get_selected()
        if len(selected) == 0:
            self.fv.show_error("No object selected.  Please select an object!")
            return False
        p.selected = selected
        self.logger.debug("returning %s" % str(p.selected))
        self.release_caller()
        return True

    def cancel(self):
        self.logger.info("CANCEL clicked.")
        p = self.callerInfo.get_data()
        p.result = 'cancel'
        self.release_caller()
        return True


    def add_blacklist(self, selected):
        self.logger.info("selected=%s" % (str(selected)))
        star = selected[0]
        g2catalog.blacklist.add_blacklist(star)
        
    def rem_blacklist(self, selected):
        self.logger.info("selected=%s" % (str(selected)))
        star = selected[0]
        g2catalog.blacklist.remove_blacklist(star)
        
    def __str__(self):
        return 'agautoselect'
    
#END
