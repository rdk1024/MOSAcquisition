#
# ANA.py -- ANA plugin for Ginga FITS viewer
# 
# Takeshi Inagaki
# Eric Jeschke (eric@naoj.org)
#
import os, pwd
import re, time

from ginga import GingaPlugin
from ginga import AstroImage
from ginga.util import wcs

from ginga.misc import Future, Bunch
import remoteObjects as ro
import cfg.INS as INSconfig

# this file written by ANA menu software
#propid_file = "/tmp/propid"

try:
    homedir = os.environ['HOME']
except Exception:
    import getpass
    homedir = '/home/%s' %getpass.getuser()
    
propid_file = os.path.join(homedir, 'propid')

anacmd_tbl = {
    'program7': "/home/gen2/moircs01/mcsfcs/src/mcsfcs_g2.csh",
    }

class AnaError(Exception):
    pass

class ANA(GingaPlugin.GlobalPlugin):
    """
    NOTE: *** All these methods are running as the GUI thread, unless
    otherwise noted. Do not block!! ***  
    """

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(ANA, self).__init__(fv)

        # Find out what proposal ID we are logged in under
        username = pwd.getpwuid(os.getuid()).pw_name
        match = re.match(r'^[uo](\d{5})$', username)
        if match:
            self.propid = 'o' + match.group(1)
        else:
            self.propid = None
            if os.path.exists(propid_file):
                try:
                    with open(propid_file, 'r') as in_f:
                        self.propid = in_f.read().strip()
                except Exception:
                    # silently ignore lack of propid
                    pass

        # for looking up instrument names
        self.insconfig = INSconfig.INSdata()


    #############################################################
    #    Here come the ANA commands
    #############################################################

    def confirmation(self, tag, future,
                     instrument_name=None, title=None, dialog=None):

        # Make sure the specified channel is available
        chname = instrument_name
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)

        chinfo = self.fv.get_channelInfo(chname)

        # Deactivate plugin if one is already running
        pluginName = 'Ana_Confirmation'
        if chinfo.opmon.is_active(pluginName):
            chinfo.opmon.deactivate(pluginName)
            self.fv.update_pending()

        p = future.get_data()
        p.setvals(instrument_name=instrument_name, title=title,
                  dialog=dialog)

        # Invoke the operation manually
        chinfo.opmon.start_plugin_future(chname, pluginName, future)


    def userinput(self, tag, future,
                  instrument_name=None, title=None, itemlist=None,
                  iconfile=None, soundfile=None):
        # Make sure the specified channel is available
        chname = instrument_name
        if not self.fv.has_channel(chname):
            self.fv.add_channel(chname)

        chinfo = self.fv.get_channelInfo(chname)

        # Deactivate plugin if one is already running
        pluginName = 'Ana_UserInput'
        if chinfo.opmon.is_active(pluginName):
            chinfo.opmon.deactivate(pluginName)
            self.fv.update_pending()

        p = future.get_data()
        p.setvals(instrument_name=instrument_name, title=title,
                  itemlist=itemlist, iconfile=iconfile, soundfile=soundfile)

        # Invoke the operation manually
        chinfo.opmon.start_plugin_future(chname, pluginName, future)


    def _execute_program(self, tag, future, command=None, parameter=None):

        # look up command from a table
        cmd = anacmd_tbl[command.lower()]

        if parameter is not None:
            cmdstr = "%s %s" % (cmd, parameter)
        else:
            cmdstr = cmd

        p = future.get_data()
        
        self.logger.info("Executing command: %s" % (cmdstr))
        try:
            res = os.system(cmdstr)
            p.rescode = res
            if res != 0:
                raise AnaError("Command returned error code=%d" % (res))
            p.result = 'ok'

        except Exception, e:
            p.setvals(result='error', errmsg=str(e))
            
        future.resolve(0)

    def execute_program(self, tag, future, command=None, parameter=None):
        # Don't execute programs as the GUI!  Spawn off to a separate
        # task.
        self.fv.nongui_do(self._execute_program, tag, future,
                          command=command, parameter=parameter)


    def sleep(self, tag, future, sleep_time=None):
        def _sleep(future):
            p = future.get_data()
            p.result = 'ok'
            future.resolve(0)

        # TODO: Don't block the GUI thread!
        #gobject.timeout_add(msecs, _sleep, future)
        time.sleep(sleep_time)

        _sleep(future)


    def show_fits(self, fitspath):
        self.fv.nongui_do(self._show_fits, fitspath)
        return 0

    def _show_fits(self, fitspath):

        dirname, filename = os.path.split(fitspath)
        
        # Create an empty image
        image = AstroImage.AstroImage(logger=self.logger)
        try:
            #self.fv.showStatus("Loading %s" % (filename))
            self.logger.debug("Loading file '%s'" % (filename))
            image.load_file(fitspath)

        except Exception, e:
            self.fv.error("Error loading %s: %s" % (
                filename, str(e)))
            return
            
        header = image.get_header()

        # Try to figure out the frame id of the image 
        (path, filename) = os.path.split(fitspath)
        (frameid, ext) = os.path.splitext(filename)

        chname = None
        try:
            # 1st try the filename
            chname = self.insconfig.getNameByFrameId(frameid)
                
        except Exception:
            # No go.  How about an embedded keyword?
            try:
                frameid = header['FRAMEID'].strip()
                chname = self.insconfig.getNameByFrameId(frameid)

            except Exception:
                # Give up--don't display the data
                self.logger.error("Error getting FRAMEID from fits header: %s" % (
                    filename))
                return

        image.set(name=frameid, path=fitspath, chname=chname)
        path = image.get('path', 'NO PATH')
        #print "receive: path=%s" % (path)

        # Check that propid matches
        try:
            propid = header['PROP-ID'].strip()

        except Exception:
            # Give up--don't display the data
            self.logger.error("Error getting PROP-ID from fits header: %s" % (
                    filename))
            return

        if propid.lower() != self.propid:    
            self.logger.error("propid of file and login don't match: %s" % (
                    filename))
            return
        
        # OK--display image. 
        #self.fv.make_callback('file-notify', fitspath)
        self.fv.gui_do(self.fv.add_image, frameid, image, chname=chname)


    def __str__(self):
        return 'ana'
    

#END
