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
    if sky_chip1 != 0:
        dif_chip1_filename = rootname+"_ss_chip1.fits"
        dif_chip2_filename = rootname+"_ss_chip2.fits"
        if not retry1:
            delete(dif_chip1_filename, dif_chip2_filename)    # TODO: Can we please use some for loops here? It feels like every line happens twice
            imarith(star_chip1_filename,'-',sky_chip1_filename, dif_chip1_filename)
            imarith(star_chip2_filename,'-',sky_chip2_filename, dif_chip2_filename)
    else:
        dif_chip1_filename = star_chip1_filename
        dif_chip2_filename = star_chip2_filename
    
    # mosaic the chips together
    comb_star_filename = rootname+"_star.fits"
    if not retry1:
        delete(comb_star_filename)
        makemosaic(dif_chip1_filename, dif_chip2_filename, comb_star_filename, c_file)
    
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
    imgets(input_fits1, 'DET-ID')
    if imgets.value != '1':
        raise ValueError("%s is data from chip%s, but should be from chip1" %
                         (input_fits1, imgets.value))
    imgets(input_fits1, 'ALTITUDE')
    if float(imgets.value) < 45.:
        log(("WARN: %s has a low elevation of %s; the mosaicing database may "+
             "not be applicable here.") % (input_fits1, imgets.value))
    imgets(input_fits2, 'DET-ID')
    if imgets.value != '2':
        raise ValueError("%s is data from chip%s, but should be from chip2" %
                         (input_fits2, imgets.value))
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
    temp_name = [["makemosaic_temp%d_ch%d"%(i,j) for i in (1,2)] for j in (1,2)]
    
    # correct for distortion
    delete("makemos_temp1_ch1.fits", "makemos_temp1_ch2.fits")
    geotran(input_fits1, "makemos_temp1_ch1.fits", config[2], config[3])
    geotran(input_fits2, "makemos_temp1_ch2.fits", config[4], config[5])
    
    # mosaic
    delete("makemos_temp2_ch1.fits", "makemos_temp2_ch2.fits")
    geotran("makemos_temp1_ch1.fits", "makemos_temp2_ch1.fits", config[8], config[9])
    geotran("makemos_temp1_ch2.fits", "makemos_temp2_ch2.fits", config[10], config[11])
    hedit("makemos_temp2_ch1.fits", "BPM", config[12], add='yes', update='yes', ver='no')
    hedit("makemos_temp2_ch2.fits", "BPM", config[13], add='yes', update='yes', ver='no')
    
    delete("makemos_temp1_ch1.fits", "makemos_temp1_ch2.fits")  # TODO: should makemos_... be variables?
    
    # combine and rotate
    delete("makemos_temp3.fits")
    imcombine("makemos_temp2_ch1.fits,makemos_temp2_ch2.fits", "makemos_temp3.fits", reject='avsig', masktype='goodvalue')
    
    delete("makemos_temp2_ch1.fits", "makemos_temp2_ch2.fits")
    
    rotate("makemos_temp3.fits", output_fits, 90, ncol=2048, nline=3569)    #XXX Do I need this?
    
    delete("makemos_temp3.fits")


def delete(*files):
    """
    Delete files(s)
    @param files:
        The locations of the files to be deleted
    """
    for filename in files:
        try:
            os.remove(filename)
        except OSError:
            pass

#END

