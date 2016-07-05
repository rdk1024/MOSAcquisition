#
# QDAS.py -- QDAS plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
# Takeshi Inagaki (tinagaki@naoj.org)
#
import math

import os
import numpy

from ginga import GingaPlugin, AstroImage
from ginga.misc import Future, Bunch
from ginga.util import wcs

import remoteObjects as ro
import astro.radec as radec
import cfg.g2soss as g2soss

# Local application imports
from util import g2calc

class QDASError(Exception):
    pass

msg_auto_success = """Automatic frame region selection succeeded."""
msg_semiauto_failure = """Automatic frame region selection failed!

Please select a region manually."""
msg_auto_manual = """Manual mode selected:

Please select a region manually."""

# Where sounds are stored
soundhome = os.path.join(g2soss.soundhome, 'ogg', 'en')

# Sounds
snd_region_failure = os.path.join(soundhome, "auto_regionselect_failed4.ogg")
snd_region_select_manual = os.path.join(soundhome,
                                      "select_region_manually3.ogg")



class QDAS(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(QDAS, self).__init__(fv)

        self.count = 0
        #fv.set_callback('add-image', self.add_image)

        self.colorcalc = 'cyan'
        self.dc = fv.get_draw_classes()

        # For image FWHM type calculations
        self.iqcalc = g2calc.IQCalc(self.logger)

    #############################################################
    #    Here come the QDAS commands
    #############################################################

    def qdas_display(self, tag, future,
                     instrument_name=None, input_frame=None):
        
        # Copy the image specified by (input_frame) into the QDAS channel
        chname = '%s_Online' % (instrument_name)
        image = self.load_frame(instrument_name, input_frame, chname)
        assert isinstance(image, AstroImage.AstroImage), \
               QDASError("Null image for %s" % chname)

        # remove all other QDAS layers
        chinfo = self.fv.get_channelInfo(chname)
        self.withdraw_qdas_layers(chinfo.fitsimage)
        
        #self.fv.ds.raise_tab(chname)

        p = future.get_data()
        p.result = 'ok'
        
        future.resolve(0)


    def frame_region(self, tag, future,
                     motor=None, instrument_name=None, mode=None,
                     input_frame=None, select_mode=None,
                     x_region=None, y_region=None):
    
        # Copy the image specified by (input_frame) into the QDAS channel
        chname = '%s_Online' % (instrument_name)
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)

        chinfo = self.fv.get_channelInfo(chname)

        # Deactivate plugin if one is already running
        pluginName = 'Region_Selection'
        if chinfo.opmon.is_active(pluginName):
            chinfo.opmon.deactivate(pluginName)
            self.fv.update_pending()

        image = self.load_frame(instrument_name, input_frame, chname)
        assert isinstance(image, AstroImage.AstroImage), \
               QDASError("Null image for %s" % chname)
        self.fv.ds.raise_tab(chname)

        # TODO: calculate automatic exptime?
        p = future.get_data()
        p.setvals(exptime=0.0, auto=False, recenter=True,
                  obj_x=0.0, obj_y=0.0, fwhm=0.0,
                  skylevel=0.0, brightness=0.0,
                  dx=x_region // 2, dy=y_region // 2,
                  alg='v1')

        # TODO: get old values
        #x, y, exptime, fwhm, brightness, skylevel, objx, objy
        ## p = self.get_default_parameters('region_selection',
        ##                             ('x', 'y', 'exptime', 'fwhm', 'brightness',
        ##                             'skylevel', 'objx', 'objy'))

        p.x, p.y = image.width // 2, image.height // 2
        p.x1, p.y1 = max(0, p.x - p.dx), max(0, p.y - p.dy)
        p.x2 = min(image.width-1,  p.x + p.dx)
        p.y2 = min(image.height-1, p.y + p.dy)

        rsinfo = chinfo.opmon.getPluginInfo(pluginName)
        rsobj = rsinfo.obj

        thr = rsobj.threshold
        if (thr == ''):
            thr = None
        p.setvals(radius=rsobj.radius, threshold=thr)

        select_mode = select_mode.lower()
        if select_mode in ('auto', 'semiauto'):
            try:
                p.x1, p.y1 = 0, 0
                p.x2, p.y2 = image.width-1, image.height-1
                
                self._auto_region_selection(image, p)

                rsobj.show_region(p)
                p.exptime = rsobj.exptime

                future.resolve(0)
                return

            except Exception as e:
                errmsg = "Automatic region selection failed: %s" % str(e)
                self.logger.error(errmsg)
                self.fv.play_soundfile(snd_region_failure, priority=19)

        #elif select_mode in ('manual', ):
            
        # Invoke the operation manually
        chinfo.opmon.start_plugin_future(chname, pluginName,
                                         future)
            
        self.fv.update_pending(timeout=0.10)
        self.fv.play_soundfile(snd_region_select_manual, priority=20)
            

    def _auto_region_selection(self, image, p):

        if p.alg == 'v2':
            qualsize = self.iqcalc.qualsize
        else:
            # NOTE: qualsize_old is Kosugi-san's old algorithm
            qualsize = self.iqcalc.qualsize_old
            
        qs = qualsize(image, p.x1, p.y1, p.x2, p.y2,
                      radius=p.radius, threshold=p.threshold)
        p.x, p.y = qs.x, qs.y

        # set region from center of detected object
        if p.recenter:
            p.x1, p.y1 = max(0, p.x - p.dx), max(0, p.y - p.dy)
            p.x2 = min(image.width-1,  p.x + p.dx)
            p.y2 = min(image.height-1, p.y + p.dy)

        p.fwhm = qs.fwhm
        p.brightness = qs.brightness
        p.skylevel = qs.skylevel
        p.obj_x = qs.objx
        p.obj_y = qs.objy
        p.result = 'ok'

        self.logger.info("Region selection succeeded %s" % (
            str(p)))


    def telescope_move(self, tag, future,
                       motor=None, instrument_name=None,
                       input_frame=None, slit_x=None, slit_y=None,
                       object_x=None, object_y=None, framelist=[]):

        # Copy the image specified by (input_frame) into the QDAS channel
        chname = '%s_Online' % (instrument_name)
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)

        chinfo = self.fv.get_channelInfo(chname)

        # Deactivate plugin if one is already running
        pluginName = 'Sv_Drive'
        if chinfo.opmon.is_active(pluginName):
            chinfo.opmon.deactivate(pluginName)
            self.fv.update_pending()

        input_frame = framelist[0]
        image = self.load_frame(instrument_name, input_frame, chname)
        assert isinstance(image, AstroImage.AstroImage), \
               QDASError("Null image for %s" % chname)
        self.fv.ds.raise_tab(chname)

        # Set defaults and adjust for difference between data coords and
        # fits coords
        if slit_x is not None:
            slit_x -= 1
        if slit_y is not None:
            slit_y -= 1
        if object_x is not None:
            object_x -= 1
        if object_y is not None:
            object_y -= 1

        p = future.get_data()
        p.setvals(dst_x=slit_x, dst_y=slit_y,
                  obj_x=object_x, obj_y=object_y,
                  x1=0, y1=0, x2=image.width-1, y2=image.height-1,
                  framelist=framelist, dst_channel=chname,
                  src_channel=instrument_name,
                  load_frame=self.load_frame)

        future2 = Future.Future(data=p)
        future2.add_callback('resolved', self._telescope_move_cb, future,
                             p, image)
        
        # Invoke the operation manually
        chinfo.opmon.start_plugin_future(chname, pluginName, future2)

    def reacquire_target(self, tag, future,
                         motor=None, instrument_name=None,
                         input_frame=None, dst_x=None, dst_y=None,
                         obj_x=None, obj_y=None,
                         x1=None, y1=None, x2=None, y2=None,
                         select_mode='OVERRIDE', recenter='NO',
                         width=None, height=None, badwcs='OK'):

        # Create the QDAS channel if it is not already created
        chname = '%s_Online' % (instrument_name)
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)

        chinfo = self.fv.get_channelInfo(chname)

        # Load the image we are operating on into the channel
        image = self.load_frame(instrument_name, input_frame, chname)
        assert isinstance(image, AstroImage.AstroImage), \
               QDASError("Null image for %s" % chname)
        self.fv.ds.raise_tab(chname)

        p = future.get_data()
        future2 = Future.Future(data=p)
        future2.add_callback('resolved', self._telescope_move_cb, future,
                             p, image)
        
        # Set defaults and adjust for difference between data coords and
        # fits coords
        if x1 is None:
            x1 = 0
        else:
            x1 -= 1
        if y1 is None:
            y1 = 0
        else:
            y1 -= 1
        if x2 is None:
            x2 = image.width-1
        else:
            x2 -= 1
        if y2 is None:
            y2 = image.height-1
        else:
            y2 -= 1
        if width is None:
            width = x2 - x1
        if height is None:
            height = y2 - y1
        if dst_x is not None:
            dst_x -= 1
        if dst_y is not None:
            dst_y -= 1
        if obj_x is not None:
            obj_x -= 1
        if obj_y is not None:
            obj_y -= 1

        select_mode = select_mode.lower()
        recenter = recenter.lower() == 'yes'
        p.setvals(dst_x=dst_x, dst_y=dst_y,
                  obj_x=obj_x, obj_y=obj_y,
                  auto=False, mode=select_mode,
                  recenter=recenter, autoerr=False,
                  fwhm=0.0, skylevel=0.0, brightness=0.0,
                  dx=width // 2, dy=height // 2,
                  width=width, height=height,
                  x1=x1, y1=y1, x2=x2, y2=y2,
                  badwcs=badwcs, alg='v1')

        pluginName = 'Sv_Drive'
        pluginInfo = chinfo.opmon.getPluginInfo(pluginName)
        pluginObj = pluginInfo.obj

        thr = pluginObj.threshold
        if (thr == ''):
            thr = None
        p.setvals(radius=pluginObj.radius, threshold=thr)
            
        if select_mode in ('auto', 'semiauto', 'override'):
            try:
                self._auto_region_selection(image, p)
                pluginObj.acquire_region(p)

                if select_mode != 'override':
                    future2.resolve(0)
                    return
                p.msg = "Please confirm target acquisition."

            except Exception as e:
                ## self.fv.gui_do(pluginObj.check_region, x1, y1, x2, y2,
                ##                width=width, height=height)
                errmsg = "Automatic target reacquisition failed: %s" % str(e)
                self.logger.error(errmsg)
                self.fv.play_soundfile(snd_region_failure, priority=19)

                if select_mode == 'auto':
                    # TODO: need to show failure visibly on QDAS canvas
                    p.setvals(result='error', errmsg=errmsg)
                    future2.resolve(0)
                    return
                
                p.autoerr = True
                p.msg = "Automatic target reacquisition failed. Please acquire the target manually."
        else:
            p.msg = "Manual target reacquisition."

        # Start plugin if it is not already running
        if not chinfo.opmon.is_active(pluginName):
            chinfo.opmon.start_plugin_future(chname, pluginName, future2,
                                             alreadyOpenOk=True)
            self.fv.update_pending()

        #self.fv.update_pending(timeout=0.10)
        self.fv.play_soundfile(snd_region_select_manual, priority=20)


    def _telescope_move_cb(self, future2, future, p, image):
        self.logger.debug("telescope move cb: res=%s" % (str(p)))
        image = p.get('image', image)
        p.image = None
        try:
            if p.result == 'ok':
                try:
                    dst_ra_deg, dst_dec_deg = image.pixtoradec(p.dst_x, p.dst_y)
                    obj_ra_deg, obj_dec_deg = image.pixtoradec(p.obj_x, p.obj_y)

                    p.dst_ra = radec.raDegToString(dst_ra_deg)
                    p.dst_dec = radec.decDegToString(dst_dec_deg)
                    p.obj_ra = radec.raDegToString(obj_ra_deg)
                    p.obj_dec = radec.decDegToString(obj_dec_deg)

                    sep_ra, sep_dec = wcs.get_RaDecOffsets(obj_ra_deg, obj_dec_deg,
                                                           dst_ra_deg, dst_dec_deg)
                    self.logger.debug("separation is dra=%f ddec=%f" % (sep_ra,
                                                                        sep_dec))
                    p.rel_ra = sep_ra
                    p.rel_dec = sep_dec
                    #p.rel_ra = radec.offsetRaDegToString(sep_ra)
                    #p.rel_dec = radec.decDegToString(sep_dec)
                except Exception as e:
                    if p.badwcs != 'OK':
                        raise(e)
                    p.dst_ra = 'BAD_WCS'
                    p.dst_dec = 'BAD_WCS'
                    p.obj_ra = 'BAD_WCS'
                    p.obj_dec = 'BAD_WCS'
                    p.rel_ra = 'BAD_WCS'
                    p.rel_dec = 'BAD_WCS'

                p.dst_x += 1
                p.dst_y += 1
                p.equinox = 2000.0
                p.dst_equinox = 2000.0
                p.obj_equinox = 2000.0
                p.obj_x += 1
                p.obj_y += 1
                p.x1 += 1
                p.y1 += 1
                p.x2 += 1
                p.y2 += 1

                p.delta_x = p.obj_x - p.dst_x
                p.delta_y = p.obj_y - p.dst_y

        except Exception as e:
            p.setvals(result='error', errmsg=str(e))

        # Function objects cannot be marshalled
        p.load_frame = None

        self.logger.debug("telescope move cb terminating: res=%s" % (str(p)))
        future.resolve(0)
        
    
    def focus_fitting(self, tag, future,
                      instrument_name, file_list, x1, y1, x2, y2):

        chname = '%s_Online' % (instrument_name)
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)
        chinfo = self.fv.get_channelInfo(chname)

        rsinfo = chinfo.opmon.getPluginInfo('FocusFit')
        rsobj = rsinfo.obj

        p = future.get_data()
        
        # Invoke the gui
        if not chinfo.opmon.is_active('FocusFit'):
            chinfo.opmon.start_plugin(chname, 'FocusFit', alreadyOpenOk=True)

        try:
            # TODO: would prefer not to have the GUI thread doing
            # all that file I/O
            z = rsobj.focus_fitting(file_list, x1, y1, x2, y2)
            p.setvals(result='ok', z=z)

        except Exception as e:
            errmsg = "Focus fitting failed: %s" % str(e)
            self.logger.error(errmsg)
            p.setvals(result='error', errmsg=str(e))

        future.resolve(0)

    def MOIRCS_fitting(self, tag, future,
                       instrument_name, param, file_list, best_fit_type):

        chname = '%s_Online' % (instrument_name)
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)
        chinfo = self.fv.get_channelInfo(chname)

        rsinfo = chinfo.opmon.getPluginInfo('MOIRCSFit')
        rsobj = rsinfo.obj

        p = future.get_data()
        
        # Invoke the gui
        if not chinfo.opmon.is_active('MOIRCSFit'):
            chinfo.opmon.start_plugin(chname, 'MOIRCSFit', alreadyOpenOk=True)

        if param == 'MAIN':
            try:
                z = rsobj.focus_fitting(param, file_list)
                p.setvals(result='ok', z=z)

            except Exception as e:
                errmsg = "Focus fitting failed: %s" % str(e)
                self.logger.error(errmsg)
                p.setvals(result='error', errmsg=str(e))
        elif param == 'BEST':
            try:
                z = rsobj.focus_best(best_fit_type)
                p.setvals(result='ok', z=z)

            except Exception as e:
                errmsg = "Best fitting failed: %s" % str(e)
                self.logger.error(errmsg)
                p.setvals(result='error', errmsg=str(e))
        elif param == 'INIT':
            try:
                z = rsobj.close()
                p.setvals(result='ok', z=z)

            except Exception as e:
                errmsg = "Init failed: %s" % str(e)
                self.logger.error(errmsg)
                p.setvals(result='error', errmsg=str(e))

        future.resolve(0)

    def seeing(self, tag, future,
               instrument_name, avg, std, dp):

        chname = '%s_Online' % (instrument_name)
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)
        chinfo = self.fv.get_channelInfo(chname)

        rsinfo = chinfo.opmon.getPluginInfo('FocusFit')
        rsobj = rsinfo.obj

        p = future.get_data()
        
        # Invoke the gui
        if not chinfo.opmon.is_active('FocusFit'):
            chinfo.opmon.start_plugin(chname, 'FocusFit', alreadyOpenOk=True)

        try:
            rsobj.seeing_size(avg, std, dp)
            p.setvals(result='ok')

        except Exception as e:
            errmsg = "Seeing size failed: %s" % str(e)
            self.logger.error(errmsg)
            p.setvals(result='error', errmsg=str(e))

        future.resolve(0)

    def curve_fitting(self, tag, future,
               instrument_name, x_points, y_points, parabola):

        chname = '%s_Online' % (instrument_name)
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)
        chinfo = self.fv.get_channelInfo(chname)

        rsinfo = chinfo.opmon.getPluginInfo('CurveFit')
        rsobj = rsinfo.obj

        p = future.get_data()
        
        # Invoke the gui
        if not chinfo.opmon.is_active('CurveFit'):
            chinfo.opmon.start_plugin(chname, 'CurveFit', alreadyOpenOk=True)

        try:
            self.fv.gui_call(rsobj.curve_fitting, p, x_points, y_points,
                             parabola)

        except Exception as e:
            errmsg = "Curve Fitting failed: %s" % str(e)
            self.logger.error(errmsg)
            p.setvals(result='error', errmsg=str(e))

        future.resolve(0)

    def mark_position(self, tag, future,
                      instrument_name=None, x=None, y=None, mode=None,
                      mark=None, size=None, color=None):
        # X and Y are in FITS data coordinates
        x, y = x-1, y-1

        chname = '%s_Online' % (instrument_name)
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)

        chinfo = self.fv.get_channelInfo(chname)

        p = future.get_data()

        canvas = chinfo.fitsimage
        try:
            self._mark(chname, canvas, x, y, mode, mark, size, color)
            p.setvals(result='ok')

        except Exception as e:
            p.setvals(result='error', errmsg=str(e))
            
        future.resolve(0)
        
                
    def load_image(self, tag, future, instrument_name, path):

        if not path:
            return
        
        # Copy the image specified by (input_frame) into the QDAS channel
        chname = '%s_Online' % (instrument_name)
        image = self.load_file(path, chname)
        assert isinstance(image, AstroImage.AstroImage), \
               QDASError("Null image for '%s'" % (chname))

        # remove all other QDAS layers
        chinfo = self.fv.get_channelInfo(chname)
        self.withdraw_qdas_layers(chinfo.fitsimage)
        
        self.fv.ds.raise_tab(chname)
        return 0

    def viewer(self, tag, future, motor, instrument_name):

        instrument_name = instrument_name.upper()

        chname1 = instrument_name
        ch1_exists = self.fv.has_channel(chname1)

        chname2 = '%s_Online' % (instrument_name)
        ch2_exists = self.fv.has_channel(chname2)
        
        p = future.get_data()

        if motor == 'ON':
            # Create these channels if they does not exist
            if not ch1_exists:
                self.fv.add_channel(chname1)
            if not ch2_exists:
                self.fv.add_channel(chname2)

        elif motor == 'OFF':
            # Delete these channels if they exists
            if ch1_exists:
                self.fv.delete_channel(chname1)
            if ch2_exists:
                self.fv.delete_channel(chname2)

        
        p.setvals(result='ok')
        future.resolve(0)
        return 0

    #############################################################
    #    Helper methods
    #############################################################

    def _get_framepath(self, frameid, instrument_name):

        #if frameid != 'DEFAULT':
        DATAHOME = os.environ['DATAHOME']
        path = os.path.join(DATAHOME, instrument_name,
                            '%s.fits' % frameid)
        self.logger.info('frame path=%s' % path)
        return path


    def withdraw_qdas_layers(self, fitsimage):
        tags = fitsimage.getTagsByTagpfx('qdas-')
        for tag in tags:
            try:
                fitsimage.deleteObjectByTag(tag)
            except:
                pass
        
    def load_file(self, filepath, dst_chname):
        try:
            self.logger.debug("Attempting to load '%s' into %s" % (
                filepath, dst_chname))
            image = self.fv.load_file(filepath, chname=dst_chname, wait=True)

            return image

        except Exception as e:
            errmsg = "Failed to load '%s' into %s: %s" % (
                filepath, dst_chname, str(e))
            self.logger.error(errmsg)
            raise QDASError(errmsg)

        
    def load_frame(self, src_chname, imagename, dst_chname):
        """Load image named (imagename) from channel named (chname1) into
        channel named (chname2).
        """
        try:
            chinfo1 = self.fv.get_channelInfo(src_chname)
            if chinfo1.datasrc.has_key(imagename):
                # Image is still in the heap
                image = chinfo1.datasrc[imagename]
                self.fv.change_channel(dst_chname, image=image)
                return image
        except KeyError:
            # Channel does not exist yet
            pass

        try:
            path = self._get_framepath(imagename, src_chname)
            self.logger.debug("Image '%s' is no longer in memory; attempting to load from '%s'" % (
                imagename, path))
            image = self.fv.load_file(path, chname=dst_chname, wait=True)
            assert isinstance(image, AstroImage.AstroImage), \
                   QDASError("Null image for '%s'" % (src_chname))
            return image

        except Exception as e:
            errmsg = "Failed to load '%s' image into %s: %s" % (
                imagename, dst_chname, str(e))
            self.logger.error(errmsg)
            raise QDASError(errmsg)

        
    ## def add_image(self, viewer, chname, image):
    ##     chinfo = self.fv.get_channelInfo(chname)
        
    ##     data = image.get_data()
    ##     # Get metadata for mouse-over tooltip
    ##     header = image.get_header()

    def _mark(self, chname, canvas, x, y, mode, mark, size, color):
        # mode is CLEAR | DRAW
        mode = mode.upper()
        if mode == 'CLEAR':
            objs = canvas.get_objects_by_tag_pfx("qdas_mark")
            canvas.delete_objects(objs)
            
        elif mode == 'DRAW':
            color = color.lower()
            mark  = mark.lower()
            self.count += 1
            tag = ("qdas_mark%d" % self.count)

            # mark is POINT | CROSS | CIRCLE | SQUARE
            if mark == 'cross':
                tag = canvas.add(self.dc.Point(x, y, size,
                                                    color=color),
                                 tag=tag)
            elif mark == 'point':
                tag = canvas.add(self.dc.Circle(x, y, size,
                                                    color=color,
                                                    fill=True),
                                 tag=tag)
            elif mark == 'circle':
                tag = canvas.add(self.dc.Circle(x, y, size,
                                                    color=color),
                                 tag=tag)
            elif mark == 'square':
                half = size #// 2
                x1, y1, x2, y2 = x-half, y-half, x+half, y+half
                tag = canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                                       color=color),
                                 tag=tag)

            # Only raise for a draw
            self.fv.ds.raise_tab(chname)

    def __str__(self):
        return 'qdas'
    

#END
