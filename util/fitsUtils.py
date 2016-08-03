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
dir_mcsred = "../../MCSRED2/"



def nothing(*args, **kwargs):
    """A placeholder function for log"""
    pass


def auto_process_fits(mode, n1, n2, c, i, f, log=nothing, next_step=None):
    """
    Use mode to choose a fitsUtils method and call it with the appropriate
    arguments
    @param mode:
        A string which will determine the method we call - either 'star',
        'mask', or 'starhole'
    """
    try:
        if mode == 'mask':
            process_mask_fits(n1, c, i, f, log, next_step=next_step)
        else:
            process_star_fits(n1, n2, c, i, f, log, next_step=next_step)
    except Exception as e:
        log("{}: {}".format(type(e).__name__, e), level='e')


def process_star_fits(star_num, back_num, c_file, img_dir, output_filename,
                      log=nothing, next_step=None
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
        The location of the cfg file that contains parameters for makemosaic
    @param img_dir:
        The string prefix to all raw image filenames
    @param output_filename:
        The filename of the final FITS image
    @param log:
        A function which should take one argument, and will be called to report
        information
    @param error:
        A function that takes a single string argument in the event of an error
    @param next_step:
        The function to be called at the end of this process
    @raises IOError:
        If it cannot find the FITS files in the specified directory
    @raises ValueError:
        If the FITS files have the wrong chip values
    """
    log("Processing star frames...")
    
    # open the star FITS, if you can
    star_chip = []
    for chip in (0, 1):
        star_chip.append(open_fits("{}MCSA{:08d}.fits".format(
                                            img_dir, star_num+chip))[0])
    
    # check header info
    for i in (0, 1):
        if star_chip[i].header['DET-ID'] != i+1:
            raise ValueError(("{}MCSA{:08d}.fits should be data from chip {}, "+
                              "but is from chip {}. Try a different frame "+
                              "number.").format(img_dir, star_num, i+1,
                                                star_chip[i].header['DET-ID'])
                             )
        if star_chip[i].header['ALTITUDE'] < 45.0:
            log((u"{}MCSA{:08d}.fits has low elevation of {:.1f}\u00B0; "+
                  "the mosaicing database may not be applicable here.").format(
                                            img_dir, star_num+i,
                                            star_chip[i].header['ALTITUDE']),
                level='warning')
    
    # subtract the background frames from the star frames
    log("Subtracting images...")
    if back_num != 0:
        back_chip = []
        for chip in (0,1):
            back_chip.append(open_fits("{}MCSA{:08d}.fits".format(
                                                img_dir, back_num+chip))[0])
        
        dif_data = [star_chip[i].data - back_chip[i].data for i in (0,1)]
    
    else:
        dif_data = [star_chip[i].data for i in (0,1)]
    
    # mosaic the chips together
    mosaic_hdu = makemosaic(dif_data, star_chip[0].header, c_file, log=log)
    
    # apply gaussian blur
    log("Blurring...")
    gaussian_filter(mosaic_hdu.data, 1.0, output=mosaic_hdu.data)
    
    # write to file
    mosaic_hdu.writeto(output_filename, clobber=True)
    
    # finish up with the provided callback
    if next_step != None:
        next_step()


def process_mask_fits(mask_num, c_file, img_dir, output_filename,
                      log=nothing, next_step=None):
    """
    Process the raw mask frames by changing their data type and mosaicing them
    together
    @param mask_num:
        The number in the filename of the mask chip1 FITS image
    @param c_file:
        The location of the cfg file that controls makemosaic
    @param img_dir:
        The prefix for all raw image filenames
    @param output_filename:
        The filename of the output FITS image
    @param log:
        The function that will be called whenever something interesting happens
    @param error:
        A function that takes a single string argument in the event of an error
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
                                            img_dir, mask_num+chip))[0])
    
    # mosaic the reformatted results to a file
    mosaic_hdu = makemosaic([mask_chip[0].data, mask_chip[1].data],
                            mask_chip[0].header, c_file, log=log)
    mosaic_hdu.writeto(output_filename, clobber=True)
    
    # and you're done! go ahead to the next step
    if next_step != None:
        next_step()


def open_fits(filename):
    """
    Exactly the same thing as astropy.fits.open, but it throws more descriptive
    error messages!
    """
    try:
        return fits.open(filename)
    except IOError as e:
        raise IOError(str(e)+"\nPlease check your frame numbers and image "+
                             "directory, or change Ginga's working directory.")


def makemosaic(input_data, input_header, c_file, log=nothing):
    """
    Correct the images for distortion, and then combine the two FITS images by
    rotating and stacking them vertically. Also do something to the header
    @param input_data:
        A sequence of two numpy 2D arrays to mosaic together
    @param input_header:
        The HDU header on which the output image's header will be based
    @param c_file:
        The location of the configuration .cfg file that manages distortion-
        correction
    @param log:
        A function that takes a single string argument and records it somehow
    @param error:
        A function that takes a single string argument in the event of an error
    @returns:
        An astropy HDU object consisting of the new data and the updated header
    """
    # read MSCRED c_file
    cfg = open(c_file, 'r')
    config = []
    line = cfg.readline()
    while line != '':
        if line[0] != '#':
            config.append(line.split()[-1].replace('dir_mcsred$',dir_mcsred))
        line = cfg.readline()
    cfg.close()
    
    # correct for distortion and apply mask
    # XXX: stuff I haven't figured out how to do wiothout IRAF yet :XXX #
    log("Correcting for distortion...")
    correct_data = [transform(input_data[0], config[2], config[3]),
                    transform(input_data[1], config[4], config[5])]
    log("Correcting some more for distortion...")
    shifted_data = [transform(correct_data[0], config[8], config[9]),
                    transform(correct_data[1], config[10], config[11])]
    log("Masking bad pixels...")
    masked_data = [apply_mask(shifted_data[0], config[12]),
                   apply_mask(shifted_data[1], config[13])]
    # XXX: stuff I haven't figured out how to do wiothout IRAF yet :XXX #
    
    # crop images
    cropped_data = [masked_data[0][:, 0:1818], masked_data[1][:, -1818:-1]] # XXX is it okay for me to hardcode the 1818?
    
    # combine and rotate the images
    log("Combining the chips...")
    mosaic_data = np.rot90(np.hstack(cropped_data), k=3)
    
    return fits.PrimaryHDU(data=mosaic_data, header=input_header)


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

