#
# AgAreaSelection.py -- Ag area selection plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#

from ginga.misc import Widgets, Plot, Bunch
from ginga import GingaPlugin

# Local application imports
from util import g2calc

class AgAreaSelection(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(AgAreaSelection, self).__init__(fv, fitsimage)

        self.layertag = 'qdas-agareaselection'

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        self.canvas = canvas

        canvas.set_callback('cursor-down', self.drag)
        canvas.set_callback('cursor-move', self.drag)
        canvas.set_callback('cursor-up', self.update)
        canvas.set_callback('draw-event', self.setpickregion)
        canvas.set_drawtype('rectangle', color='cyan', linestyle='dash',
                            drawdims=True)
        canvas.set_surface(self.fitsimage)

        self.exptime = 6000

        self.pick_qs = None
        self.picktag = None
        self.pickcolor = 'green'
        self.eregcolor = 'pink'

        self.dx = 30
        self.dy = 30
        # this is the maximum size a side can be
        self.max_len = 512
        self.agarea = 'AG1'

        self.iqcalc = g2calc.IQCalc(self.logger)
        self.radius = 10
        self.threshold = None
        self.use_new_algorithm = False

    def build_gui(self, container, future=None):

        vtop = Widgets.VBox()
        vtop.set_border_width(2)

        vbox, sw, orientation = Widgets.get_oriented_box(container)

        self.msgFont = self.fv.getFont("sansFont", 14)

        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Expander(" Instructions ")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        nb = Widgets.TabWidget(tabpos='bottom')
        self.w.nb2 = nb
        vbox.add_widget(nb, stretch=0)

        captions = (('Object X:', 'label', 'Object_X', 'llabel',
                     'Object Y:', 'label', 'Object_Y', 'llabel'),
                    ('RA:', 'label', 'RA', 'llabel',
                     'DEC:', 'label', 'DEC', 'llabel'),
                    ('Equinox:', 'label', 'Equinox', 'llabel'),
                    ('Sky Level:', 'label', 'Sky Level', 'entry',
                     'Brightness:', 'label', 'Brightness', 'entry'),
                    ('FWHM:', 'label', 'FWHM', 'llabel',
                     'Star Size:', 'label', 'Star Size', 'llabel'),
                    ('Sample Area:', 'label', 'Sample Area', 'llabel'),
                    ('Exptime:', 'label', 'Exptime', 'entry'),
                    )

        w, b = Widgets.build_info(captions)
        self.w.update(b)
        b.exptime.set_text(str(self.exptime))
        self.wdetail = b

        # add padding for spacing
        box = Widgets.Box()
        box.set_border_width(30)
        box.add_widget(w)
        nb.add_widget(box, title="Select")

        captions = (('New algorithm', 'checkbutton'),
                    ('Radius:', 'label', 'Radius', 'spinfloat',
                     'xlbl_radius', 'label'),
                    ('Threshold:', 'label', 'Threshold', 'entry',
                     'xlbl_threshold', 'label'),
                    )

        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.radius.set_tooltip("Radius for peak detection")
        b.threshold.set_tooltip("Threshold for peak detection (blank=default)")

        b.new_algorithm.set_state(self.use_new_algorithm)
        def new_alg_cb(w, tf):
            self.use_new_algorithm = tf
        b.new_algorithm.add_callback('activated', new_alg_cb)

        # radius control
        b.radius.set_decimals(2)
        b.radius.set_limits(5.0, 200.0, incr_value=1.0)
        def chg_radius(w, val):
            self.radius = float(val)
            self.w.xlbl_radius.set_text(str(self.radius))
            return True
        b.xlbl_radius.set_text(str(self.radius))
        b.radius.add_callback('value-changed', chg_radius)

        # threshold control
        def chg_threshold(w):
            threshold = None
            ths = w.get_text().strip()
            if len(ths) > 0:
                threshold = float(ths)

            self.threshold = threshold
            self.w.xlbl_threshold.set_text(str(self.threshold))
            return True
        b.xlbl_threshold.set_text(str(self.threshold))
        b.threshold.add_callback('activated', chg_threshold)

        hbox = Widgets.HBox()
        hbox.add_widget(w, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        nb.add_widget(hbox, title="Settings")

        vbox.add_widget(Widgets.Label(''), stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(5)

        btn = Widgets.Button("Ok")
        btn.add_callback('activated', lambda w: self.ok())
        btns.add_widget(btn, stretch=1)

        btn = Widgets.Button("Cancel")
        btn.add_callback('activated', lambda w: self.cancel())
        btns.add_widget(btn, stretch=1)
        btns.add_widget(Widgets.Label(''), stretch=1)

        vtop.add_widget(sw, stretch=1)
        vtop.add_widget(btns, stretch=0)
        container.add_widget(vtop, stretch=1)


    def set_message(self, msg):
        self.tw.set_text(msg)
        self.tw.set_font(self.msgFont)

    def withdraw_qdas_layers(self):
        tags = self.fitsimage.get_tags_by_tag_pfx('qdas-')
        for tag in tags:
            try:
                self.fitsimage.delete_object_by_tag(tag)
            except:
                pass

    def instructions(self):
        self.set_message("""Please select an area manually.

Draw (or redraw) an area with the right mouse button.  Move the area with the left mouse button.  Press Ok or Cancel to finish.""")

    def start(self, future=None):
        self.callerInfo = future
        # Gather parameters
        p = future.get_data()

        # remove all qdas canvases
        self.withdraw_qdas_layers()

        # insert our canvas to fitsimage if it is not already
        try:
            obj = self.fitsimage.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

        self.canvas.delete_all_objects(redraw=False)
        self.instructions()

        # Save calling parameters
        #self.w.exptime.set_text(str(p.exptime))

        self.resume()

        self.agarea = p.ag_area.upper()

        # Draw exposure region, if any
        if p.has_key('er_x1'):
            self.logger.info("Exposure region at %dx%d, %dx%d" % (
                p.er_x1, p.er_y1, p.er_x2, p.er_y2))
            self.canvas.add(self.dc.CompoundObject(
                self.dc.Rectangle(p.er_x1, p.er_y1, p.er_x2, p.er_y2,
                                  color=self.eregcolor),
                self.dc.Text(p.er_x1, p.er_y2+4, "Exposure Range",
                             color=self.eregcolor)),
                            redraw=False)

        tag = self.canvas.add(self.dc.Rectangle(p.x1, p.y1, p.x2, p.y2,
                                                color='cyan',
                                                linestyle='dash'))
        self.setpickregion(self.canvas, tag)


    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a rectangle with the right mouse button")

    def stop(self):
        # disable canvas
        self.canvas.ui_setActive(False)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True

    def release_caller(self):
        try:
            self.close()
        except:
            pass
        self.callerInfo.resolve(0)

    def ok(self):
        self.logger.info("OK clicked.")
        p = self.callerInfo.get_data()

        try:
            obj = self.canvas.get_object_by_tag(self.picktag)
        except KeyError:
            # No rectangle drawn
            # TODO: throw up a popup
            pass

        if obj.kind != 'compound':
            return True
        bbox  = obj.objects[0]
        point = obj.objects[1]
        p.x1, p.y1, p.x2, p.y2 = bbox.get_llur()

        # Save exposure time for next invocation
        try:
            self.exptime = float(self.w.exptime.get_text())
        except ValueError:
            self.exptime = 3000.0
        p.exptime = self.exptime

        p.result = 'ok'
        self.release_caller()

    def cancel(self):
        self.logger.info("CANCEL clicked.")
        p = self.callerInfo.get_data()
        p.result = 'cancel'

        try:
            obj = self.canvas.get_object_by_tag(self.picktag)
            if obj.kind == 'compound':
                bbox  = obj.objects[0]
                point = obj.objects[1]
                label = obj.objects[2]
                bbox.color = 'red'
                label.color = 'red'
                self.canvas.redraw()
        except KeyError:
            pass
        self.release_caller()

    def show_area(self, p):
        # remove all qdas canvases
        self.withdraw_qdas_layers()

        # insert our canvas to fitsimage if it is not already
        try:
            obj = self.fitsimage.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

        self.agarea = p.ag_area.upper()

        self.canvas.delete_all_objects(redraw=False)

        # Draw exposure region, if any
        if p.has_key('er_x1'):
            self.logger.info("Exposure region at %dx%d, %dx%d" % (
                p.er_x1, p.er_y1, p.er_x2, p.er_y2))
            self.canvas.add(self.dc.CompoundObject(
                self.dc.Rectangle(p.er_x1, p.er_y1, p.er_x2, p.er_y2,
                                  color=self.eregcolor),
                self.dc.Text(p.er_x1, p.er_y2+4, "Exposure Range",
                             color=self.eregcolor)),
                            redraw=False)

        # Draw area selection
        tag = self.canvas.add(self.dc.CompoundObject(
            self.dc.Rectangle(p.x1, p.y1, p.x2, p.y2,
                              color=self.pickcolor),
            self.dc.Point(p.x, p.y, 10, color='green'),
            self.dc.Text(p.x1, p.y2+4, self.agarea,
                         color=self.pickcolor)),
                              redraw=True)
        self.picktag = tag

        # disable canvas
        self.stop()
        return 0


    def redo(self):
        obj = self.canvas.get_object_by_tag(self.picktag)
        if obj.kind != 'compound':
            return True
        bbox  = obj.objects[0]
        point = obj.objects[1]
        data_x, data_y = point.x, point.y
        x1, y1, x2, y2 = bbox.get_llur()

        p = self.callerInfo.get_data()
        try:
            image = self.fitsimage.get_image()

            # sanity check on region
            width = x2 - x1
            height = y2 - y1
            dx = width // 2
            dy = height // 2
            if (width > self.max_len) or (height > self.max_len):
                errmsg = "Image area (%dx%d) too large!" % (
                    width, height)
                self.fv.showStatus(errmsg)
                raise Exception(errmsg)

            # Note: FITS coordinates are 1-based, whereas numpy FITS arrays
            # are 0-based
            fits_x, fits_y = data_x + 1, data_y + 1

            self.wdetail.sample_area.set_text('%dx%d' % (width, height))

            if self.use_new_algorithm:
                qualsize = self.iqcalc.qualsize
            else:
                qualsize = self.iqcalc.qualsize_old
            qs = qualsize(image, x1, y1, x2, y2, radius=self.radius,
                          threshold=self.threshold)
            p.x, p.y = qs.x, qs.y

            # Calculate X/Y of center of star
            obj_x = qs.objx
            obj_y = qs.objy
            fwhm = qs.fwhm
            # set region from center of detected object
            p.x1, p.y1 = max(0, p.x - dx), max(0, p.y - dy)
            width = image.width
            height = image.height
            p.x2 = min(width - 1,  p.x + dx)
            p.y2 = min(height - 1, p.y + dy)

            p.fwhm = qs.fwhm
            p.brightness = qs.brightness
            p.skylevel = qs.skylevel
            p.objx = qs.objx
            p.objy = qs.objy

            self.wdetail.fwhm.set_text('%.3f' % fwhm)
            self.wdetail.object_x.set_text('%.3f' % (obj_x+1))
            self.wdetail.object_y.set_text('%.3f' % (obj_y+1))
            self.wdetail.sky_level.set_text('%.3f' % qs.skylevel)
            self.wdetail.brightness.set_text('%.3f' % qs.brightness)

            # Mark object center on image
            point.x, point.y = obj_x, obj_y
            point.color = 'cyan'

            # Calc RA, DEC, EQUINOX of X/Y center pixel
            ra_txt, dec_txt = image.pixtoradec(obj_x, obj_y, format='str')
            self.wdetail.ra.set_text(ra_txt)
            self.wdetail.dec.set_text(dec_txt)
            equinox = image.get_keyword('EQUINOX', 'UNKNOWN')
            self.wdetail.equinox.set_text(str(equinox))

            self.pick_qs = qs

            # TODO: Get separate FWHM for X and Y
            cdelt1, cdelt2 = image.get_keywords_list('CDELT1', 'CDELT2')
            starsize = self.iqcalc.starsize(fwhm, cdelt1, fwhm, cdelt2)
            self.wdetail.star_size.set_text('%.3f' % starsize)

        except Exception as e:
            point.color = 'red'
            self.logger.error("Error calculating quality metrics: %s" % (
                str(e)))
            for key in ('sky_level', 'brightness', 'star_size'):
                self.wdetail[key].set_text('')
            self.wdetail.fwhm.set_text('Failed')
            self.pick_qs = None

            # set region
            p.x1, p.y1 = max(0, x1), max(0, y1)
            width = image.width
            height = image.height
            p.x2 = min(width - 1,  x2)
            p.y2 = min(height - 1, y2)

        self.canvas.redraw(whence=3)

        self.fv.showStatus("Click left mouse button to reposition pick")
        return True

    def update(self, canvas, event, data_x, data_y):
        try:
            obj = self.canvas.get_object_by_tag(self.picktag)
            if obj.kind == 'rectangle':
                bbox = obj
            else:
                bbox  = obj.objects[0]
                point = obj.objects[1]
            x1, y1, x2, y2 = bbox.get_llur()
            self.dx = (x2 - x1) // 2
            self.dy = (y2 - y1) // 2
        except Exception as e:
            pass

        dx = self.dx
        dy = self.dy

        # Mark center of object and region on main image
        try:
            self.canvas.delete_object_by_tag(self.picktag, redraw=False)
        except:
            pass

        x1, y1 = data_x - dx, data_y - dy
        x2, y2 = data_x + dx, data_y + dy

        tag = self.canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                                color='cyan',
                                                linestyle='dash'),
                              redraw=False)

        self.setpickregion(self.canvas, tag)
        return True

    def drag(self, canvas, event, data_x, data_y):

        obj = self.canvas.get_object_by_tag(self.picktag)
        if obj.kind == 'compound':
            bbox = obj.objects[0]
        elif obj.kind == 'rectangle':
            bbox = obj
        else:
            return True

        # calculate center of bbox
        x1, y1, x2, y2 = bbox.get_llur()
        wd = x2 - x1
        dw = wd // 2
        ht = y2 - y1
        dh = ht // 2
        x, y = x1 + dw, y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        # calculate new coords
        x1, y1, x2, y2 = x1+dx, y1+dy, x2+dx, y2+dy

        if (not obj) or (obj.kind == 'compound'):
            # Replace compound image with rectangle
            try:
                self.canvas.delete_object_by_tag(self.picktag, redraw=False)
            except:
                pass

            self.picktag = self.canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                                             color='cyan',
                                                             linestyle='dash'))
        else:
            # Update current rectangle with new coords and redraw
            bbox.x1, bbox.y1, bbox.x2, bbox.y2 = x1, y1, x2, y2
            self.canvas.redraw(whence=3)

        return True

    def setpickregion(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        if obj.kind != 'rectangle':
            return True
        canvas.delete_object_by_tag(tag, redraw=False)

        if self.picktag:
            try:
                canvas.delete_object_by_tag(self.picktag, redraw=False)
            except:
                pass

        # determine center of rectangle
        x1, y1, x2, y2 = obj.get_llur()
        x = x1 + (x2 - x1) // 2
        y = y1 + (y2 - y1) // 2

        tag = canvas.add(self.dc.CompoundObject(
            self.dc.Rectangle(x1, y1, x2, y2,
                              color=self.pickcolor),
            self.dc.Point(x, y, 10, color='red'),
            self.dc.Text(x1, y2+4, self.agarea,
                         color=self.pickcolor)),
                         redraw=False)
        self.picktag = tag

        #self.fv.raise_tab("detail")
        self.redo()
        return True

    def __str__(self):
        return 'agareaselection'

#END
