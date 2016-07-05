#
# Ana_Confirmation.py -- ANA Confirmation plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
from ginga import GingaPlugin
from ginga.misc import Widgets

class Ana_Confirmation(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Ana_Confirmation, self).__init__(fv, fitsimage)

    def build_gui(self, container, future=None):
        vbox1 = Widgets.VBox()
        vbox = Widgets.VBox()
        
        fr = Widgets.Frame()
        fr.set_widget(vbox)
        
        self.lbl = Widgets.Label()
        vbox.add_widget(self.lbl, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)
        self.btns = btns
        vbox.add_widget(btns, stretch=0)

        vbox1.add_widget(fr, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)

        btn = Widgets.Button("Cancel")
        btn.add_callback('activated', lambda w: self.cancel())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox1.add_widget(btns, stretch=0)

        # stretch/spacer
        vbox1.add_widget(Widgets.Label(""), stretch=1)

        container.add_widget(vbox1, stretch=0)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True
        
    def start(self, future=None):
        self.callerInfo = future
        # Gather parameters
        p = future.get_data()

        self.lbl.set_text(p.title)

        # Remove previous buttons
        self.btns.remove_all()

        def cb(index):
            return lambda w: self.ok(index)

        items = p.dialog.split()
        index = 1
        for name in items:
            btn = Widgets.Button(name)
            btn.add_callback('activated', cb(index))
            self.btns.add_widget(btn, stretch=0)
            index += 1
        #self.btns.add_widget(Widgets.Label(''), stretch=1)

    def resume(self):
        pass
    
    def release_caller(self):
        try:
            self.close()
        except:
            pass
        self.callerInfo.resolve(0)
        
    def ok(self, index):
        self.logger.info("OK clicked, index=%d" % (index))
        p = self.callerInfo.get_data()

        p.result = 'ok'
        p.index  = index
        self.release_caller()

    def cancel(self):
        self.logger.info("CANCEL clicked.")
        p = self.callerInfo.get_data()
        p.result = 'cancel'
        self.release_caller()

    def stop(self):
        pass
    
    def redo(self):
        pass
    
    def __str__(self):
        return 'ana_confirmation'
    
#END
