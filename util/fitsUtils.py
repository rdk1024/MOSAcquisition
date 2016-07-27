#
# fitsUtils.py -- A utility file with methods that use IRAF to manipulate FITS files
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import os

# third-party imports
from pyraf import iraf   # TODO: astropy?



def nothing(*args, **kwargs):
    """A placeholder function for log"""
    pass


def process_star_frames(star_chip1, sky_chip1, rootname, c_file, img_dir,
                        log=nothing, next_step=None
                        ): #TODO: I don't need all of these
    """
    Process the raw star and sky images by subtracting the sky from the star
    images, adding a gaussian filter to the result, and mosaicing it all
    together
    @param star_chip1_num:
        The number in the star image filename
    @param sky_chip1_num:
        The number in the sky image filename
    @param rootname:
        The string used as a filename for all the files IRAF creates
    @param c_file:
        The location of the cfg file that contains parameters for makemosaic
    @param img_dir:
        The string prefix to all raw image filenames
    @param log:
        A function which should take one argument, and will be called to report
        information
    """
    log("Processing star frames...")
    
    # declare all of the raw input filenames
    star_chip1_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, star_chip1)
    star_chip2_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, star_chip1+1)
    sky_chip1_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, sky_chip1)
    sky_chip2_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, sky_chip1+1)
    
    # check header info
    try:
        iraf.imgets(star_chip1_filename, 'DET-ID')
        if iraf.imgets.value != '1':
            raise ValueError("%s is data from chip%s, but should be from chip1"%
                             (star_chip1_filename, iraf.imgets.value))
        iraf.imgets(star_chip2_filename, 'DET-ID')
        if iraf.imgets.value != '2':
            raise ValueError("%s is data from chip%s, but should be from chip2"%
                             (star_chip2_filename, iraf.imgets.value))
    except iraf.IrafError as e:
        log("ERROR: {}".format(str(e).strip()))
        log("The chip number or image directory are incorrect,\n"+
            "or you may be running python from the wrong working directory.")
        return
    
    # subtract the sky frames from the star frames
    log("Subtracting images...")
    if sky_chip1 != 0:
        dif_chip1_filename = rootname+"_dif_chip1.fits"
        dif_chip2_filename = rootname+"_dif_chip2.fits"
        delete(dif_chip1_filename, dif_chip2_filename)
        iraf.imarith(star_chip1_filename,'-',sky_chip1_filename,
                     dif_chip1_filename)
        iraf.imarith(star_chip2_filename,'-',sky_chip2_filename,
                     dif_chip2_filename)
    else:
        dif_chip1_filename = star_chip1_filename
        dif_chip2_filename = star_chip2_filename
    
    # mosaic the chips together
    sharp_star_filename = rootname+"_star_sharp.fits"
    delete(sharp_star_filename)
    makemosaic(dif_chip1_filename, dif_chip2_filename, sharp_star_filename,
               c_file, log=log)
    delete(dif_chip1_filename, dif_chip2_filename)
    
    # apply gaussian blur
    log("Blurring...")
    final_star_filename = rootname+"_star.fits"
    delete(final_star_filename)
    iraf.gauss(sharp_star_filename, final_star_filename, 1.0)
    delete(sharp_star_filename)
    
    # finish up with the provided callback
    if next_step != None:
        next_step()


def process_mask_frames(mask_chip1, rootname, c_file, img_dir,
                        log=nothing, next_step=None):
    """
    Process the raw mask frames by changing their data type and mosaicing them
    together
    @param mask_chip1:
        The number in the filename of the mask chip1 FITS image
    @param rootname:
        The string used as a filename for all the files IRAF creates
    @param c_file:
        The location of the cfg file that controls makemosaic
    @param img_dir:
        The prefix for all raw image filenames
    @param log:
        The function that will be called whenever something interesting happens
    @param next_step:
        The function to be called at the end of this process
    """
    log("Processing mask frames...")
    
    # deduce the raw image filenames
    mask_chip1_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, mask_chip1)
    mask_chip2_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, mask_chip1+1)
    
    # reformat the raw images
    log("Changing data type...")
    real_chip1_filename = rootname+"_real_chip1.fits"
    real_chip2_filename = rootname+"_real_chip2.fits"
    delete(real_chip1_filename, real_chip2_filename)
    iraf.chpixtype(mask_chip1_filename, real_chip1_filename, 'real')
    iraf.chpixtype(mask_chip2_filename, real_chip2_filename, 'real')
    delete(mask_chip1_filename, mask_chip2_filename)
    
    # mosaic the reformatted results together
    final_mask_filename = rootname+"_mask.fits"
    delete(final_mask_filename)
    makemosaic(real_chip1_filename, real_chip2_filename, final_mask_filename,
               c_file, log=log)
    delete(real_chip1_filename, real_chip2_filename)
    
    # and you're done! go ahead to the next step
    if next_step != None:
        next_step()


def process_starhole_frames(log=nothing):
    pass


def makemosaic(input_fits1, input_fits2, output_fits, c_file, log=nothing):
    """
    Combine the two images by stacking them vertically, and correct for
    distortion
    @param input_fits1:
        The filename of the first image
    @param input_fits2:
        The filename of the second image
    @param output_fits:
        The output filename
    @param c_file:
        The location of the configuration .cfg file
    """
    # check header info
    iraf.imgets(input_fits1, 'ALTITUDE')
    if float(iraf.imgets.value) < 45.:
        log(("WARN: %s has a low elevation of %s; the mosaicing database may "+
             "not be applicable here.") % (input_fits1, iraf.imgets.value))
    iraf.imgets(input_fits2, 'ALTITUDE')
    if float(iraf.imgets.value) < 45.:
        log(("WARN: %s has a low elevation of %s; the mosaicing database may "+
             "not be applicable here.") % (input_fits2, iraf.imgets.value))
    
    # read MSCRED c_file
    cfg = open(c_file, 'r')
    config = []
    line = cfg.readline()
    while line != '':
        if line[0] != '#':
            config.append(line.split()[-1])
        line = cfg.readline()
    cfg.close()
    
    # come up with some temporary filenames
    temp_file = [["makemosaic_temp%d_ch%d.fits"%(j,i) for i in (0,1)]
                 for j in (0,1)]
    unrotated = "makemosaic_temp3.fits"
    
    # correct for distortion
    log("Correcting for distortion...")
    delete(temp_file[0][0], temp_file[0][1])
    iraf.geotran(input_fits1, temp_file[0][0], config[2], config[3])
    iraf.geotran(input_fits2, temp_file[0][1], config[4], config[5])
    
    # mosaic
    log("Repositioning chips...")
    delete(temp_file[1][0], temp_file[1][1])
    iraf.geotran(temp_file[0][0], temp_file[1][0], config[8], config[9])
    iraf.geotran(temp_file[0][1], temp_file[1][1], config[10], config[11])
    iraf.hedit(temp_file[1][0], 'BPM', config[12], add='yes', update='yes', ver='no')   # TODO: what are the defaults?
    iraf.hedit(temp_file[1][1], 'BPM', config[13], add='yes', update='yes', ver='no')
    delete(temp_file[0][0], temp_file[0][1])
    
    # combine the images
    log("Combining the chips...")
    delete(unrotated)
    iraf.imcombine(temp_file[1][0]+','+temp_file[1][1], unrotated,
              reject='avsig', masktype='goodvalue')
    delete(temp_file[1][0], temp_file[1][1])
    
    # rotate the result
    iraf.rotate(unrotated, output_fits, 90, ncol=2048, nline=3569)
    delete(unrotated)


def delete(*files):
    """
    Delete files(s) without throwing any errors
    @param files:
        The locations of the files to be deleted
    """
    for filename in files:
        try:
            os.remove(filename)
        except OSError as e:
            pass

#END

