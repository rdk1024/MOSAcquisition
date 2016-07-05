#
# Ana_UserInput.py -- ANA user input plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
from ginga import GingaPlugin
from ginga.misc import Widgets

class Ana_UserInput(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Ana_UserInput, self).__init__(fv, fitsimage)

    def build_gui(self, container, future=None):
        vbox1 = Widgets.VBox()
        vbox = Widgets.VBox()
        
        fr = Widgets.Frame()
        fr.set_widget(vbox)
        
        self.lbl = Widgets.Label()
        vbox.add_widget(self.lbl, stretch=0)

        vbox2 = Widgets.VBox()
        self.entries = vbox2
        vbox.add_widget(vbox2, stretch=1)

        vbox1.add_widget(fr, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)

        btn = Widgets.Button("Ok")
        btn.add_callback('activated', lambda w: self.ok())
        btns.add_widget(btn)
        btn = Widgets.Button("Cancel")
        btn.add_callback('activated', lambda w: self.cancel())
        btns.add_widget(btn)
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

        # Remove previous entries
        self.entries.remove_all()

        p.resDict = {}

        tbl = Widgets.GridBox(rows=len(p.itemlist), columns=2)
        tbl.set_row_spacing(2)
        tbl.set_column_spacing(2)

        row = 0
        for name, val in p.itemlist:
            lbl = Widgets.Label(name)
            #lbl.set_alignment(1.0, 0.5)
            ent = Widgets.TextEntry()
            #ent.set_length(100)
            val_s = str(val)
            ent.set_text(val_s)
            p.resDict[name] = ent

            tbl.add_widget(lbl, 0, row, stretch=0)
            tbl.add_widget(ent, 1, row, stretch=1)
            row += 1

        self.entries.add_widget(tbl, stretch=0)

    def resume(self):
        pass
    
    def release_caller(self):
        try:
            self.close()
        except:
            pass
        self.callerInfo.resolve(0)
        
    def ok(self):
        p = self.callerInfo.get_data()

        p.result = 'ok'
        # Read out the entry widgets
        d = {}
        for key, ent in p.resDict.items():
            s = ent.get_text()
            d[key] = s

        p.resDict = d
        self.logger.info("OK clicked, items=%s" % (d))
        self.release_caller()

    def cancel(self):
        p = self.callerInfo.get_data()
        p.result = 'cancel'
        p.resDict = {}
        self.logger.info("CANCEL clicked.")
        self.release_caller()

    def stop(self):
        pass
    
    def redo(self):
        pass
    
    def __str__(self):
        return 'ana_userinput'
    
#END
