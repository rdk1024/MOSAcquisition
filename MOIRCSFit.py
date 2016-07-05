#
# MOIRCSFit.py -- MOIRCS focus fitting plugin for fits viewer
# 
# Hannah Twigg-Smith
# Writen using FocusFit.py as a guideline
#

import os
import shutil
import logging
import pickle

import gtk
import pango

import numpy as np
## For Ubuntu 12.04
## from scipy.stats import binned_statistic
import binned_statistic
import scipy.optimize as optimize

import gtk, gobject
import matplotlib
matplotlib.use('GTKAgg')
import matplotlib.pyplot as plt
from  matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as figurecanvas

import sewpy
import pyfits

from ginga.gtkw import ImageViewCanvasTypesGtk as CanvasTypes
from ginga.gtkw import Plot
from ginga import GingaPlugin

import cfg.g2soss as g2soss
from Gen2.fitsview.util import polynomial

class MOIRCSFitError(Exception):
    pass

# These functions are used when we compute the statistics of the
# binned data. Note that we have a minimum sample size defined. This
# means that statistics will be computed only on bins that have
# sufficient samples in them.
MIN_SAMPLE_SIZE = 6
def compute_mean(x):
    if len(x) >= MIN_SAMPLE_SIZE:
        return np.mean(x)
    else:
        return None

def compute_median(x):
    if len(x) >= MIN_SAMPLE_SIZE:
        return np.median(x)
    else:
        return None

class MOIRCSFit(GingaPlugin.LocalPlugin):
    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(MOIRCSFit, self).__init__(fv, fitsimage)
        self.fwhm_factor = 0.117 # FWHM gets multiplied by this factor

        # Min/Max pixel values for the graphs.
        self.xmin_pixel = 0
        self.xmax_pixel = 2048

        # Parameters for binning the FWHM data to compute mean and
        # median values.
        self.bin_start = 200
        self.bin_stop = 2000
        self.bin_incr = 400
        self.bins = np.arange(self.bin_start, self.bin_stop, self.bin_incr)
        self.x_pix_bins = np.array([])
        for i, x in enumerate(self.bins):
            try:
                self.x_pix_bins = np.append(self.x_pix_bins, (self.bins[i] + self.bins[i+1]) / 2)
            except:
                pass

        # Name of the file used to save data for each focus position
        self.mcs_focus_data_filepath = '/tmp/mcs_focus_data.pck'

        # Work directory for Source Extractor
        self.workdir = '/tmp/sewpy'

        # Source Extractor configuration files
        self.sex_filepath = os.path.join(g2soss.dirload, 'sex')
        fitsview_confpath = os.path.join(g2soss.confhome, 'fitsview')
        self.param_filepath = os.path.join(fitsview_confpath, 'mcsfcs.param')
        self.config_filepath = os.path.join(fitsview_confpath, 'mcsfcs.sex')
        self.filter_filepath = os.path.join(fitsview_confpath, 'tophat_1.5_3x3.conv')

        # Parameters for filtering Source Extractor results
        self.se_flag_threshold = 2 # Reject sources with SE flag value >= than 2
        self.source_ellipticity_threshold = 0.3  # Reject sources with SE flag value >= than 0.3
        self.source_fwhm_threshold = 0.0 # Reject sources with FWHM <= 0.0

        # Set up a logger for the sewpy (Source Extractor wrapper)
        # module.
        sewpy_logger = logging.getLogger('sewpy')
        for h in self.logger.handlers:
            sewpy_logger.addHandler(h)

        # Remove the "saved data" file when the module is loaded.
        try:
            os.remove(self.mcs_focus_data_filepath)
        except OSError:
            pass

    def build_gui(self, container):
        # Paned container is just to provide a way to size the graph
        # to a reasonable size
        box = gtk.VPaned()
        cw = container.get_widget()
        cw.pack_start(box, expand=True, fill=True)

        self.notebook = gtk.Notebook()
        self.notebook.set_tab_pos(gtk.POS_TOP)
        self.show_tabs = True
        self.show_border = True
        self.notebook.set_scrollable(True)
        box.pack1(self.notebook, resize=True, shrink=True)
        
        self.fontdesc = pango.FontDescription("Helvetica Bold 18")

        # create a box to pack widgets into. 
        vbox1 = gtk.VBox()

        # label for seeing size 
        self.label_ss = gtk.Label(" Best: ")
        self.label_ss.set_alignment(0, 0)
        vbox1.pack_start(self.label_ss, padding=5, fill=True, expand=False)

        fr = gtk.Frame(" Best Z Value ")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        fr.set_label_align(0.1, 0.5)
        fr.add(vbox1)
        fr.show_all()
        
        box.pack2(fr, resize=True, shrink=True)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)
        btns.set_child_size(15, -1)

        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        cw.pack_start(btns, padding=4, fill=True, expand=False)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        try:
            os.remove(self.mcs_focus_data_filepath)
        except OSError:
            pass
        return True
        
    def clear(self):
        self.logger.debug('clearing canvas...')
        self.ax[0].cla()
        self.ax[1].cla()

    def _draw(self):
        self.ax[0].grid(True)
        self.ax[1].grid(True)
        self.fig.canvas.draw()

    def _drawGraph(self, mcs_focus_data):
        self.fig, self.ax = plt.subplots(2, 1)
        self.canvas = figurecanvas(self.fig)
        self.canvas.set_size_request(-1, 500)

        focz = mcs_focus_data['FOC-VAL']
        det_data = mcs_focus_data['det_data']

        # For each detector in the det_data structure, plot the Raw
        # Data, the Selected data, the binned median values and the
        # linear fit of the median values.
        for i, d in enumerate(det_data):
            raw_data = d['Raw Data']
            x_raw = raw_data['X_IMAGE']
            fwhm_raw = raw_data['FWHM_IMAGE']

            self.ax[i].plot(x_raw, fwhm_raw, 'ro', label='Raw data')
            sel = d['Selected']
            x_sel = sel['X_IMAGE']
            fwhm_sel = sel['FWHM_IMAGE']
            self.ax[i].plot(x_sel, fwhm_sel, 'go', label='Selected')

            x_pix_bins = d['x_pix_bins']
            medians = d['medians']
            fit = np.polyfit(x_pix_bins, medians, 1)
            fit_fn = np.poly1d(fit)

            self.ax[i].plot(x_pix_bins, medians, 'k*', label='Median', markersize=15)

            x_fit = np.linspace(self.xmin_pixel,self.xmax_pixel,5)
            self.ax[i].plot(x_fit, fit_fn(x_fit), 'k', label='Best fit')

            frameid = d['FRAMEID']
            title = '%s: FOC-Z=%s, Slope=%.3g' % (frameid, focz, fit[0])
            self.ax[i].set_title(title)
            ## 27 December 2015 - Increase y-axis range
            self.ax[i].axis([0, 2048, 0.2, 4.2])
            self.ax[i].set_xlabel('x [pixel]')
            self.ax[i].set_ylabel('FWHM [arcsec]')
            ## For Ubuntu 12.04
            ## self.ax[i].legend(fontsize='small')
            self.ax[i].legend(prop={'size': 8})
            self.ax[i].set_xticks(np.arange(0, 2049, 512))
            self.logger.info(title)

        label = gtk.Label('Z=%s' % focz)
        self.notebook.append_page(self.canvas,label)
        self._draw()
        self.canvas.show_all()
        self.notebook.next_page()
        return False

    def curve_fit(self, det_id, x, y, sdev, best_fit_type):
        best = np.nan
        x_fit = np.array([])
        y_fit = np.array([])

        # Fit the supplied FWHM vs. focus position to a quadratic
        # function, using either a non-linear fitting or a linear
        # fitting method, based on the supplied best_fit_type value.
        if best_fit_type == 'NONLINEAR':
            try:
                popt, pcov = optimize.curve_fit(lambda x,a,b,c: a*(x-b)*(x-b)+c,
                                                x, y, sigma=sdev)
                best = popt[1]
                z = np.array([popt[0], -2.*popt[0]*popt[1], popt[0]*popt[1]*popt[1]+popt[2]])
                fit_fn = np.poly1d(z)
                x_fit = np.linspace(x[0],x[-1],200)
                y_fit = fit_fn(x_fit)
            except RuntimeError as e:
                self.logger.error('Unable to curve fit det_id %s: %s' % (det_id, str(e)))
        else: # best_fit_type == 'LINEAR':
            qf = polynomial.QuadraticFunction(self.logger)
            qf.coefficient(x, y)
            best, yv = qf.min_vertex()
            x_fit = np.linspace(x[0],x[-1],200)
            fit_fn = qf.quadratic()
            y_fit = fit_fn(x_fit)

        return best, x_fit, y_fit

    def errorplot(self, det_id, x, y, sdev, best, x_fit, y_fit):

        # Plot the supplied FWHM vs focus position and the curve fit
        # results.
        self.ax[det_id-1].errorbar(x, y, sdev, linestyle='None', marker='^')

        self.ax[det_id-1].plot(x_fit, y_fit)

        title = 'MCS Focus Fitting [CH%s]' % det_id
        if np.isfinite(best):
            title = '%s: Best-Z=%.3g' % (title, best)
        else:
            title = '%s: Curve fit fail' % title
        self.ax[det_id-1].set_title(title)
        self.logger.info(title)
        self.ax[det_id-1].set_xlabel('FOC-Z')
        self.ax[det_id-1].set_ylabel('FWHM [arcsec]')
        return best

    def _drawBest(self, best_data, best, x_fit, y_fit, avg_best):
        
        self.fig, self.ax = plt.subplots(2, 1)
        self.canvas = figurecanvas(self.fig)
        self.canvas.set_size_request(-1, 500)

        self.clear()

        # For each detector in best_data, plot the binned median FWHM vs focus position.
        for d in best_data:
            det_id = d['DET-ID']
            x = d['focz']
            y = d['med_fwhm']
            sdev = d['sdev']
            self.errorplot(det_id, x, y, sdev, best[det_id-1], x_fit[det_id-1], y_fit[det_id-1])

        if np.isfinite(avg_best):
            msg = " Best:  %.3g" % (avg_best)
        else:
            msg = "Curve fit fail"
        self.label_ss.set_text(msg)
        self._draw()
        self.canvas.show_all()
        label = gtk.Label("Best")
        self.notebook.append_page(self.canvas,label)
        self.notebook.next_page()

        return False

    def valuefilter(self, astrotable):
        flags_col = astrotable['FLAGS']
        astrotable.remove_rows(np.where(flags_col >= self.se_flag_threshold)) # Throw out unneeded values
        e_col = astrotable['ELLIPTICITY']
        astrotable.remove_rows(np.where(e_col >= self.source_ellipticity_threshold)) # Throw out unneeded values

    def select_fwhm(self, astrotable):
        fwhm_col = astrotable['FWHM_IMAGE']
        astrotable.remove_rows(np.where(fwhm_col <= self.source_fwhm_threshold)) # Throw out unneeded values

    def focus_fitting(self, param, file_list):

        # We use a Python pickle file to save data from the different
        # focus positions. Load in the data from the pickle file, if
        # the file exists. Otherwise, just create a new data
        # structure.
        if os.path.isfile(self.mcs_focus_data_filepath):
            try:
                with open(self.mcs_focus_data_filepath, 'rb') as f:
                    mcs_focus_data = pickle.load(f)
            except Exception as e:
                self.logger.error('pickle load error from file %s: %s' % (self.mcs_focus_data_filepath, str(e)))
                raise e
        else:
            mcs_focus_data = []

        # Read from the supplied filepaths, get a few FITS header
        # values, and add them to the mcs_focus_data structure.
        for i, filepath in enumerate(file_list):
                self.logger.info('Reading from MOIRCS filepath %s' % filepath)
                try:
                    with pyfits.open(filepath) as hdulist:
                        frameid = hdulist[0].header['FRAMEID']
                        det_id  = hdulist[0].header['DET-ID']
                        focz    = hdulist[0].header['FOC-VAL']
                        ## 27 December 2015 - FOC-VAL is string in FITS header. Convert to float.
                        focz = float(focz)
                except Exception as e:
                    self.logger.error('Failed to get FRAMEID, DET-ID, or FOC-VAL from FITS headers for filepath %s: %s' % (filepath, str(e)))
                    continue
                if i == 0:
                    mcs_focus_data.append({})
                    mcs_focus_data[-1]['FOC-VAL'] = focz
                    mcs_focus_data[-1]['det_data'] = []
                mcs_focus_data[-1]['det_data'].append({'DET-ID': det_id, 'FRAMEID': frameid})

        # Set up an object to access Source Extractor. We set the
        # parameters, filter name, and configuration file.
        shutil.rmtree(self.workdir, True)
        sew = sewpy.SEW(
            workdir=self.workdir,
            sexpath=self.sex_filepath,
            config={'PARAMETERS_NAME': self.param_filepath, 'FILTER_NAME': self.filter_filepath, 'VERBOSE_TYPE':'NORMAL'},
            configfilepath=self.config_filepath,
            )

        # Run Source Extractor on the supplied MOIRCS filepaths and
        # process the resulting data.
        for i, filepath in enumerate(file_list):

            # Run Source Extractor
            try:
                se_result = sew(filepath)
                se_table = se_result['table']
            except Exception as e:
                self.logger.error('Source Extractor failed on file %s: %s' % (filepath, str(e)))
                continue

            # Sort the Source Extractor results using the x pixel
            # position as the sort key.
            se_table.sort('X_IMAGE')

            # Remove sources based on FHWM value
            self.select_fwhm(se_table)

            # Multiply FWHM column by the specified factor
            fwhm_col = se_table['FWHM_IMAGE']
            fwhm_col *= self.fwhm_factor

            # Add a copy of the Source Extractor "Raw Data" results to
            # the mcs_focus_data structure
            mcs_focus_data[-1]['det_data'][i]['Raw Data'] = se_table.copy()

            # Filter out sources that do not meet our criteria for
            # "flag" value and ellipticity.
            self.valuefilter(se_table)

            # Add a copy of the Source Extractor "Selected Data"
            # results to the mcs_focus_data structure
            mcs_focus_data[-1]['det_data'][i]['Selected'] = se_table.copy()

            # Compute some statistics on the "Selected Data"
            x_col = se_table['X_IMAGE']
            fwhm_col = se_table['FWHM_IMAGE']
            data_range = ((self.bins[0], self.bins[-1]),)

            # Bin the data and compute the mean values of the FWHM in
            # each bin.
            ## For Ubuntu 12.04
            ## means, binedge, binnum = binned_statistic(x_col, fwhm_col, statistic=compute_mean, bins=self.bins, range=data_range)
            means, binedge, binnum = binned_statistic.binned_statistic(x_col, fwhm_col, statistic=compute_mean, bins=self.bins, range=data_range)

            # Bin the data and compute the median values of the FWHM
            # in each bin.
            ## For Ubuntu 12.04
            ## medians, binedge, binnum = binned_statistic(x_col, fwhm_col, statistic=compute_median, bins=self.bins, range=data_range)
            medians, binedge, binnum = binned_statistic.binned_statistic(x_col, fwhm_col, statistic=compute_median, bins=self.bins, range=data_range)

            # Some bins might not have enough samples. In that case,
            # the mean and median will be returned as NaN. Select only
            # the good values for plotting.
            means_good_values = means[~np.isnan(means)]
            medians_good_values = medians[~np.isnan(medians)]
            x_pix_bins = self.x_pix_bins[~np.isnan(medians)]

            # Save the statistical data to the mcs_focus_data
            # structure.
            mcs_focus_data[-1]['det_data'][i]['x_pix_bins'] = x_pix_bins
            mcs_focus_data[-1]['det_data'][i]['means'] = means_good_values
            mcs_focus_data[-1]['det_data'][i]['medians'] = medians_good_values
            self.logger.debug('filepath %s means_good_values %s' % (filepath, means_good_values))
            self.logger.debug('filepath %s medians_good_values %s' % (filepath, medians_good_values))
            self.logger.debug('filepath %s x_pix_bins %s' % (filepath, x_pix_bins))

            # We also want to compute the average and the standard
            # deviation of the median values.
            avg_of_medians = np.mean(medians_good_values)
            sdev = np.std(medians_good_values, ddof=1) / 2.0

            # Save the average and standard deviation in the
            # mcs_focus_data structure.
            mcs_focus_data[-1]['det_data'][i]['avg_of_medians'] = avg_of_medians
            mcs_focus_data[-1]['det_data'][i]['sdev'] = sdev
            self.logger.debug('filepath %s avg_of_medians %s sdev %s' % (filepath, avg_of_medians, sdev))

        # Use the Python pickle module to write out the mcs_focus_data
        # structure.
        try:
            with open(self.mcs_focus_data_filepath, 'wb') as f:
                pickle.dump(mcs_focus_data, f)
        except Exception as e:
            self.logger.error('pickle dump error: %s' % str(e))
            raise e

        # draw graph at next available opportunity
        gobject.idle_add(self._drawGraph, mcs_focus_data[-1])

        return 0

    def focus_best(self, best_fit_type):
        # Read the Python pickle file with the saved data. If we can't
        # read the file, there isn't much we can do, so report the
        # problem and raise an exception.
        try:
            with open(self.mcs_focus_data_filepath, 'rb') as f:
                mcs_focus_data = pickle.load(f)
        except Exception as e:
            self.logger.error('Failed to read file %s: %s' % (self.mcs_focus_data_filepath, str(e)))
            raise e

        # Get the data we need for the "best" plot from the
        # mcs_focus_data structure: focus position, average of the
        # medians, and the standard deviations.
        best_data = []
        for i, d1 in enumerate(mcs_focus_data):
            focz = d1['FOC-VAL']
            for j, d2 in enumerate(d1['det_data']):
                det_id = d2['DET-ID']
                if i == 0:
                    best_data.append({'DET-ID': det_id, 'focz': [], 'med_fwhm': [], 'sdev': []})
                best_data[j]['focz'].append(focz)
                avg_of_medians = d2['avg_of_medians']
                best_data[j]['med_fwhm'].append(avg_of_medians)
                sdev = d2['sdev']
                best_data[j]['sdev'].append(sdev)

        # Curve-fit the median FWHM vs focus position and compute the
        # "best" focus position for each detector.
        best = np.array([])
        x_fit = []
        y_fit = []
        avg_best = 0.0
        count = 0
        for d in best_data:
            det_id = d['DET-ID']
            x = d['focz']
            y = d['med_fwhm']
            sdev = d['sdev']
            b, x, y = self.curve_fit(det_id, x, y, sdev, best_fit_type)
            best = np.append(best, b)
            x_fit.append(x)
            y_fit.append(y)

        # Compute the average of the "best" values.
        best_good_values = best[~np.isnan(best)]
        if len(best_good_values) > 0:
            avg_best = np.mean(best_good_values)
        else:
            avg_best = np.nan

        self.logger.debug('best %s avg_best %s' % (best, avg_best))

        # draw graph at next available opportunity
        gobject.idle_add(self._drawBest, best_data, best, x_fit, y_fit, avg_best)

        # Check to see if we were able to compute a "best" value. If
        # not, raise an exception.
        if np.isfinite(avg_best):
            avg_best_ret = float(avg_best)
        else:
            raise MOIRCSFitError('Unable to %s curve fit data from either detector' % best_fit_type)

        self.logger.info('returning avg_best_ret %s' % avg_best_ret)
        return avg_best_ret

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
        return 'moircsfit'
    
# END
