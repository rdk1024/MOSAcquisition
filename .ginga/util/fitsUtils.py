#
# fitsUtils.py -- A utility file with methods that use IRAF to manipulate FITS files
# Works in conjunction with MESOffset ginga plugin for MOS Acquisition
#
# Justin Kunimune
#



# standard imports
import os

# third-party imports
from pyraf.iraf import imgets, imarith, gauss, geotran, hedit, imcombine, rotate



def nothing(*args, **kwargs):
    """A placeholder function for log"""
    pass


def process_star_frames(star_chip1, sky_chip1, rootname, c_file, img_dir,
                        retry1, log=nothing, next_step=None
                        ): #TODO: I don't need all of these
    """
    Process the raw sky images into a single mosaiced, blurred, compound image
    @param rootname:
        The string used as a filename for all the files IRAF creates
    @param img_dir:
        The string prefix to all raw image filenames
    @param star_chip1_num:
        The number in the star image filename
    @param sky_chip1_num:
        The number in the sky image filename
    @param log:
        A function which should take one argument, and will be called to report
        information
    """
    # declare all of the raw input filenames TODO: log
    log("Loading images...")
    star_chip1_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, star_chip1)
    star_chip2_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, star_chip1+1)
    sky_chip1_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, sky_chip1)
    sky_chip2_filename = "{}MCSA{:08d}.fits[0]".format(img_dir, sky_chip1+1)
    
    # check header info
    imgets(star_chip1_filename, 'DET-ID')
    if imgets.value != '1':
        raise ValueError("%s is data from chip%s, but should be from chip1" %
                         (star_chip1_filename, imgets.value))
    imgets(star_chip2_filename, 'DET-ID')
    if imgets.value != '2':
        raise ValueError("%s is data from chip%s, but should be from chip2" %
                         (star_chip2_filename, imgets.value))
    
    # subtract the sky frames from the star frames
    log("Subtracting images...")
    if sky_chip1 != 0:
        dif_chip1_filename = rootname+"_ss_chip1.fits"
        dif_chip2_filename = rootname+"_ss_chip2.fits"
        if not retry1:
            delete(dif_chip1_filename, dif_chip2_filename)
            imarith(star_chip1_filename,'-',sky_chip1_filename, dif_chip1_filename)
            imarith(star_chip2_filename,'-',sky_chip2_filename, dif_chip2_filename)
    else:
        dif_chip1_filename = star_chip1_filename
        dif_chip2_filename = star_chip2_filename
    
    # mosaic the chips together
    log("Mosaicing images...")
    comb_star_filename = rootname+"_star.fits"
    if not retry1:
        delete(comb_star_filename)
        makemosaic(dif_chip1_filename, dif_chip2_filename, comb_star_filename,
                   c_file, log=log)
    
    # apply gaussian blur
    final_star_filename = rootname+"_starg10.fits"
    if not retry1:
        delete(final_star_filename)
        gauss(comb_star_filename, final_star_filename, 1.0)
    
    # finish up with the provided callback
    if next_step != None:
        next_step()


def process_mask_frames(log=nothing):
    pass
    
def process_starhole_frames(log=nothing):
    pass


def makemosaic(input_fits1, input_fits2, output_fits, c_file, log=nothing):     #TODO: check for variables that are only used once
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
    imgets(input_fits1, 'ALTITUDE')
    if float(imgets.value) < 45.:
        log(("WARN: %s has a low elevation of %s; the mosaicing database may "+
             "not be applicable here.") % (input_fits1, imgets.value))
    imgets(input_fits2, 'ALTITUDE')
    if float(imgets.value) < 45.:
        log(("WARN: %s has a low elevation of %s; the mosaicing database may "+
             "not be applicable here.") % (input_fits2, imgets.value))
    
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
    log("Correcting distortion...")
    delete(temp_file[0][0], temp_file[0][1])
    geotran(input_fits1, temp_file[0][0], config[2], config[3])
    geotran(input_fits2, temp_file[0][1], config[4], config[5])
    
    # mosaic
    log("Repositioning chips...")
    delete(temp_file[1][0], temp_file[1][1])
    geotran(temp_file[0][0], temp_file[1][0], config[8], config[9]) # TODO: get them out of stdout
    geotran(temp_file[0][1], temp_file[1][1], config[10], config[11])
    hedit(temp_file[1][0], 'BPM', config[12], add='yes', update='yes', ver='no')
    hedit(temp_file[1][1], 'BPM', config[13], add='yes', update='yes', ver='no')
    delete(temp_file[0][0], temp_file[0][1])
    
    # combine the images
    log("Combining the chips...")
    delete(unrotated)
    imcombine(temp_file[1][0]+','+temp_file[1][1], unrotated,
              reject='avsig', masktype='goodvalue')
    delete(temp_file[1][0], temp_file[1][1])
    
    # rotate the result
    rotate(unrotated, output_fits, 90, ncol=2048, nline=3569)
    delete(unrotated)


def delete(*files):
    """
    Delete files(s)
    @param files:
        The locations of the files to be deleted
    """
    for filename in files:
        try:
            os.remove(filename)
        except OSError as e:
            pass

#END

