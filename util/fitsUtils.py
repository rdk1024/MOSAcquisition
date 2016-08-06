#
# fitsUtils.py -- A utility file with methods to manipulate FITS files
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import os

# third-party imports
from astropy.io import fits
import numpy as np
from scipy.ndimage.filters import gaussian_filter


# constants
DIR_MCSRED = '../../MCSRED2/'
NO_SUCH_FILE_ERR = ("No such file or directory: {}\nPlease check your frame "+
                        "numbers and image directory, or run Ginga from a "+
                        "different directory.")
WRONG_CHIP_ERR =   ("{} should be data from chip {}, but is from chip {}. Try "+
                        "a different frame number.")
LOW_ELEV_WARN =   (u"{}MCSA{:08d}.fits has low elevation of {:.1f}\u00B0; the "+
                        "mosaicing database may not be applicable here.")
USER_INTERRUPT_ERR = ("This process was terminated. Please press 'Return to "+
                        "Menu' to start it over.")



def nothing(*args, **kwargs):
    """A placeholder function for log"""
    pass


def auto_process_fits(mode, n1, n2, c, i, f, t, log=nothing, next_step=None):
    """
    Use mode to choose a fitsUtils method and call it with the appropriate
    arguments
    @param mode:
        A string which will determine the method we call - either 'star',
        'mask', or 'starhole'
    """
    try:
        if mode == 'mask':
            process_mask_fits(n1, c, i, f, t, log, next_step=next_step)
        else:
            process_star_fits(n1, n2, c, i, f, t, log, next_step=next_step)
        if t.is_set():
            raise RuntimeError(USER_INTERRUPT_ERR)
    except Exception as e:
        log("{}: {}".format(type(e).__name__, e), level='e')


def process_star_fits(star_num, back_num, c_file, img_dir, output_filename,
                      terminate, log=nothing, next_step=None
                      ):
    """
    Process the raw star and background images by subtracting the background
    from the star images, adding a gaussian filter to the result, and mosaicing
    it all together
    @param star_num:
        The integer in the star image chip1 filename
    @param back_num:
        The integer in the background image chip1 filename
    @param c_file:
        The location of the cfg file that contains parameters for make_mosaic
    @param img_dir:
        The string prefix to all raw image filenames
    @param output_filename:
        The filename of the final FITS image
    @param terminate:
        The threading.Event object that flags True if the user tries to
        terminate this thread
    @param log:
        A function which should take one argument, and will be called to report
        information
    @param next_step:
        The function to be called at the end of this process
    @raises IOError:
        If it cannot find the FITS files in the specified directory
    @raises ValueError:
        If the FITS files have the wrong chip values
    """
    log("Processing star frames...")
    
    # open the star FITS and check header info
    star_chip = []
    for i in (0, 1):
        star_chip.append(open_fits("{}MCSA{:08d}.fits".format(
                                            img_dir, star_num+i), i+1))
        if star_chip[i].header['ALTITUDE'] < 45.0:
            log(LOW_ELEV_WARN.format(img_dir, star_num+i,
                                     star_chip[i].header['ALTITUDE']),
                level='warning')
    
    # subtract the background frames from the star frames
    log("Subtracting images...")
    if back_num != 0:
        back_chip = []
        for i in (0, 1):
            back_chip.append(open_fits("{}MCSA{:08d}.fits".format(
                                                img_dir, back_num+i), i+1))
        
        dif_data = [star_chip[i].data - back_chip[i].data for i in (0,1)]
    
    else:
        dif_data = [star_chip[i].data for i in (0,1)]
    
    # mosaic the chips together
    if terminate.is_set():  return
    mosaic_data = make_mosaic(dif_data, c_file, terminate, log=log)
    if terminate.is_set():  return
    
    # apply gaussian blur
    log("Blurring...")
    mosaic_data = gaussian_filter(mosaic_data, 1.0)
    
    # write to file and go to next_step
    fits.writeto(output_filename, mosaic_data, header=star_chip[0].header,
                 clobber=True)
    if next_step != None:
        next_step()


def process_mask_fits(mask_num, c_file, img_dir, output_filename,
                      terminate, log=nothing, next_step=None):
    """
    Process the raw mask frames by changing their data type and mosaicing them
    together
    @param mask_num:
        The number in the filename of the mask chip1 FITS image
    @param c_file:
        The location of the cfg file that controls make_mosaic
    @param img_dir:
        The prefix for all raw image filenames
    @param output_filename:
        The filename of the output FITS image
    @param terminate:
        The threading.Event that will flag True if the user tries to kill this
        process
    @param log:
        The function that will be called whenever something interesting happens
    @param next_step:
        The function to be called at the end of this process
    @raises IOError:
        If it cannot find the FITS images
    """
    log("Processing mask frames...")
    
    # load the files
    mask_chip = []
    for chip in (0, 1):
        mask_chip.append(open_fits("{}MCSA{:08d}.fits".format(
                                            img_dir, mask_num+chip), chip+1))
    
    # mosaic the reformatted results to a file
    if terminate.is_set():  return
    mosaic_data = make_mosaic([hdu.data for hdu in mask_chip], c_file,
                              terminate, log=log)
    if terminate.is_set():  return
    
    # finish up by writing to file and moving on
    fits.writeto(output_filename, mosaic_data, header=mask_chip[0].header,
                 clobber=True)
    if next_step != None:
        next_step()


def make_mosaic(input_data, c_file, terminate, log=nothing):
    """
    Correct the images for distortion, and then combine the two FITS images by
    rotating and stacking them vertically. Also do something to the header
    @param input_data:
        A sequence of two numpy 2D arrays to mosaic together
    @param c_file:
        The location of the configuration .cfg file that manages distortion-
        correction
    @param terminate:
        The threading.Event object that will tell us when/if to terminate
    @param log:
        A function that takes a single string argument and records it somehow
    @returns:
        A mosaiced numpy array comprising data from the two input_data arrays
    """
    # read MSCRED c_file
    cfg = open(c_file, 'r')
    config = []
    line = cfg.readline()
    while line != '':
        if line[0] != '#':
            config.append(line.split()[-1].replace('dir_mcsred$',DIR_MCSRED))
        line = cfg.readline()
    cfg.close()
    
    mosaic_data = [None,None]
    if terminate.is_set():  return
    
    # XXX: stuff I haven't figured out how to do wiothout IRAF yet :XXX #
    # correct for distortion and apply mask
    log("Correcting for distortion...")
    mosaic_data[0] = transform(input_data[0], config[2], config[3])
    if terminate.is_set():  return
    mosaic_data[1] = transform(input_data[1], config[4], config[5])
    if terminate.is_set():  return
    
    log("Correcting for more distortion...")
    mosaic_data[0] = transform(mosaic_data[0], config[8], config[9])
    if terminate.is_set():  return
    mosaic_data[1] = transform(mosaic_data[1], config[10], config[11])
    if terminate.is_set():  return
    
    log("Masking bad pixels...")
    mosaic_data[0] = apply_mask(mosaic_data[0], config[12])
    if terminate.is_set():  return
    mosaic_data[1] = apply_mask(mosaic_data[1], config[13])
    if terminate.is_set():  return
    # XXX: stuff I haven't figured out how to do wiothout IRAF yet :XXX #
    
    # combine and rotate the images
    log("Combining the chips...")
    mosaic_arr = np.rot90(np.sum(mosaic_data, axis=0), k=3)
    if terminate.is_set():  return
    
    return mosaic_arr


def open_fits(filename, chipnum):
    """
    It's like astropy.fits.open, but with better error handling
    @param filename:
        The name of the FITS file to be opened ('***.fits')
    @param chipnum:
        The desired value of the DET-ID header card
    @returns:
        An astropy HDU object -- the first in the FITS file
    @raises IOError:
        if the file cannot be found
    @raises ValueError:
        if the DET-ID is not chipnum
    """
    try:
        hdu = fits.open(filename)[0]
    except IOError as e:
        if len(filename) >= 1 and filename[0] in ('/'):
            raise IOError(NO_SUCH_FILE_ERR.format(filename))
        else:
            raise IOError(NO_SUCH_FILE_ERR.format(os.getcwd()+"/"+filename))
    if hdu.header['DET-ID'] != chipnum:
        raise ValueError(WRONG_CHIP_ERR.format(filename, chipnum,
                                               hdu.header['DET-ID']))
    return hdu


# XXX: Methods that still use IRAF :XXX #

def transform(input_arr, dbs_filename, gmp_filename):
    """
    Correct the input array for distortion using the given dbs and gmp
    @param input_arr:
        The input numpy array
    @param dbs_filename:
        The filename of the IRAF 'database file'. Not to be confused with an
        SQLBase .dbs file, or a .db database file.
    @param gmp_filename:
        The filename inside the filename that tells IRAF which part of the dbs
        file to look at. Because using integers was too easy, so why not just
        use filenames with an extention that doesn't exist to index through a
        file. Rather, the .gmp file extension does exist, and serves a log of
        purposes, but none of them have anything to do with IRAF or image
        transformations. WHYYYYYY?
    @returns:
        The corrected numpy array
    """
    from pyraf.iraf import geotran
    
    if os.path.exists('tempout.fits'):
        os.remove('tempout.fits')
    fits.PrimaryHDU(data=input_arr).writeto("tempin.fits", clobber=True)
    print dbs_filename
    geotran('tempin.fits', 'tempout.fits', dbs_filename, gmp_filename,
            verbose='no')
    output = fits.open('tempout.fits')[0].data
    os.remove('tempin.fits')
    os.remove('tempout.fits')
    return output


def apply_mask(input_arr, pl_filename, mask_val=0):
    """
    Replace all masked pixels with zero in the input array
    @param input_arr:
        The input numpy array
    @param pl_filename:
        Is it a Perl script? No. Well, it's some kind of text file, right? No.
        This is a 'pixel list', and by that I mean binary image, and not a list
        at all. It represents a mask. It has to pretend to be a Perl script
        instead of an image so that no program besides IRAF can read it.
    @param mask_val:
        The value to put into all of the masked pixels
    """
    from pyraf.iraf import imcombine
    
    if os.path.exists('tempout.fits'):
        os.remove('tempout.fits')
    hdu = fits.PrimaryHDU(data=input_arr)
    hdu.header['BPM'] = pl_filename
    hdu.writeto('tempin.fits', clobber=True)
    imcombine('tempin.fits', 'tempout.fits',
              masktype='goodvalue', maskvalue=mask_val)
    output = fits.open('tempout.fits')[0].data
    os.remove('tempin.fits')
    os.remove('tempout.fits')
    return output

#END

