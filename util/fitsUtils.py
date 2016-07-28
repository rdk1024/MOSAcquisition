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



def nothing(*args, **kwargs):
    """A placeholder function for log"""
    pass


def process_star_fits(star_num, sky_num, c_file, img_dir, output_filename,
                      log=nothing, next_step=None
                      ):
    """
    Process the raw star and sky images by subtracting the sky from the star
    images, adding a gaussian filter to the result, and mosaicing it all
    together
    @param star_num:
        The number in the star image chip1 filename
    @param sky_num:
        The number in the sky image chip1 filename
    @param c_file:
        The location of the cfg file that contains parameters for makemosaic
    @param img_dir:
        The string prefix to all raw image filenames
    @param output_filename:
        The filename of the final FITS image
    @param log:
        A function which should take one argument, and will be called to report
        information
    @param next_step:
        The function to be called at the end of this process
    @raises IOError:
        If it cannot find the specified images
    @raises ValueError:
        If the images have the wrong detector id
    """
    log("Processing star frames...")
    
    # open all the FITS, if you can TODO: what happens when the files aren't there?
    star_chip = []
    sky_chip = []
    for chip in (0, 1):
        star_chip.append(fits.open("{}MCSA{:08d}.fits".format(
                                            img_dir, star_num+chip))[0])
        sky_chip.append(fits.open("{}MCSA{:08d}.fits".format(
                                            img_dir, sky_num+chip))[0])
    
    # check header info
    for i in (0, 1):
        if star_chip[i].header['DET-ID'] != i+1:
            raise ValueError(("{}MCSA{:08d}.fits is data from chip{}, but "+
                              "should be from chip{}").format(
                                            img_dir, star_num,
                                            star_chip[i].header['DET-ID'], i+1))
        if star_chip[i].header['ALTITUDE'] < 45.0:
            log(("WARN: {}MCSA{:08d}.fits has a low elevation of {}; the "+
                 "mosaicing database may not be applicable here.").format(
                                            img_dir, star_num,
                                            star_chip[i].header['ALTITUDE']))
    
    # subtract the sky frames from the star frames
    log("Subtracting images...")
    if sky_num != 0:
        dif_data = [star_chip[0].data - sky_chip[0].data,
                    star_chip[1].data - sky_chip[1].data]
    else:
        dif_data = [star_chip[0].data,
                    star_chip[1].data]
    
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
    @param next_step:
        The function to be called at the end of this process
    @raises IOError:
        If it cannot find the FITS images
    """
    log("Processing mask frames...")
    
    # load the files
    mask_chip = []
    for chip in (0, 1):
        mask_chip.append(fits.open("{}MCSA{:08d}.fits".format(
                                            img_dir, mask_num+chip))[0])
    
    # mosaic the reformatted results to a file
    mosaic_hdu = makemosaic([mask_chip[0].data, mask_chip[1].data],
                            mask_chip[0].header, c_file, log=log)
    mosaic_hdu.writeto(output_filename, clobber=True)
    
    # and you're done! go ahead to the next step
    if next_step != None:
        next_step()


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
    @returns:
        An astropy HDU object consisting of the new data and the updated header
    """
    # read MSCRED c_file
    cfg = open(c_file, 'r')
    config = []
    line = cfg.readline()
    while line != '':
        if line[0] != '#':
            config.append(line.split()[-1])
        line = cfg.readline()
    cfg.close()
    
    # correct for distortion
    log("Correcting for distortion...")
    # XXX: stuff I haven't figured out how to do wiothout IRAF yet :XXX #
    correct_data = [transform(input_data[0], config[2], config[3]),
                    transform(input_data[1], config[4], config[5])]
    # XXX: stuff I haven't figured out how to do wiothout IRAF yet :XXX #
    
    # crop images
    cropped_data = [correct_data[0][:, 0:1818], correct_data[1][:, -1818:-1]]
    
    # combine and rotate the images
    log("Combining the chips...")
    mosaic_data = np.rot90(np.hstack(cropped_data), k=3)
    
    input_header['BPM'] = config[12]    # XXX: I don't know what this does
    input_header['BPM'] = config[13]    #TODO: hedit? BPM?
    return fits.PrimaryHDU(data=mosaic_data, header=input_header)


def transform(input_arr, dbs_file, gmp_file):
    """
    Correct the input array for distortion using the given dbs and gmp
    @param input_arr:
        The input numpy array
    @param dbs_file:
        IDK. A string, I think
    @param gmp_file:
        I'm even less sure what this one is
    @returns:
        The corrected numpy array
    """
    from pyraf.iraf import geotran
    
    fits.PrimaryHDU(data=input_arr).writeto("tempin.fits", clobber=True)
    geotran("tempin.fits", "tempout.fits", dbs_file, gmp_file)
    output = fits.open("tempout.fits")[0].data
    os.remove("tempin.fits")
    os.remove("tempout.fits")
    return output

#END

