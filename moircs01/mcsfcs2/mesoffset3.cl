# -------------------------------------------
#
#   Measure offset between STAR and HOLE
#    All in one sequence for STAR, MASK images measurements
#
#        Ver 1.0 2006/05/10 Masayuki Akiyama
#        Ver 2   2009/01/05 K. Aoki
#         Revised by IT at 2013-04-09 for da2 work
#
#   USAGE:
#       istar_chip1 : STAR frame name
#       isky_chip1  : SKY frame name, if available. If no sky frame,NONE 
#       rootname1 : SBR filename without .sbr
#       cfile : MCSRED configuration file
#       iretry1 : If iretry1=yes, mosaicing of STAR frames will be skipped
#       iretry2 : If iretry2=yes, mosaicing of MASK frames will be skipped
#       iinterac1 : 
#       iinterac2 :
# -------------------------------------------

#procedure mesoffset3( istar_chip1, isky_chip1, rootname1, cfile, iretry1, iretry2,iinterac1, iinterac2 )
procedure newmesoffset3( istar_chip1, isky_chip1, rootname1, cfile)

int     istar_chip1      {prompt = ' Input chip1 STAR frame NUMBER (MCSA000?????.fits) :'}
int     isky_chip1       {prompt = ' Input chip1 SKY frame NUMBER (MCSA000?????.fits), if not available "0" :'}
string  rootname1        {prompt = ' SBR file name (without .sbr) used as rootname):'}
file    cfile            {"dir_mcsred$DATABASE/ana_apr16.cfg", prompt = ' Configuration file in MCSRED format :'}
string  imdir            {"data$", prompt="Raw Data Directory"}
bool    iretry1          {no, prompt = ' Re-use using mosaiced STAR images from previous measure ? :'}
bool    iretry2          {no, prompt = ' Re-use using mosaiced MASK images from previous measure ? :'}
bool    iinterac1        {yes, prompt = ' Interactive meshole ? :'}
bool    iinterac2        {yes, prompt = ' Interactive messtarhole ? :'}

struct *list1

begin
    int       num_star_chip1, num_star_chip2
    string    instar_chip1, instar_chip2
    int       num_sky_chip1, num_sky_chip2
    string    insky_chip1, insky_chip2
    int       num_mask_chip1, num_mask_chip2
    string    inmask_chip1, inmask_chip2

    string    frame_ss_chip1, frame_ss_chip2
    string    frame_star, frame_starg10, frame_mask
    string    log_mesoffset
    string    list_starhole, list_mask, list_starmask
    string    list_geotran, list_geores

    int       detid1, detid2
    string    configfile
    string    sbrfile
    string    data1, data2, data3
    string    data4, data5, data6
    string    rootname
    bool      retry1, retry2
    bool      interac1, interac2

    bool      mask_ready
    bool      star_OK
    bool      mask_OK
    bool      maskframe_same

# Star Frames 
    num_star_chip1 = istar_chip1
    if( num_star_chip1 < 100000 ){ 
       instar_chip1 = imdir//"MCSA000"//num_star_chip1//".fits[0]"
       num_star_chip2 = num_star_chip1 + 1
       instar_chip2 = imdir//"MCSA000"//num_star_chip2//".fits[0]"
       num_mask_chip1 = num_star_chip1 + 2
       inmask_chip1 = imdir//"MCSA000"//num_mask_chip1//".fits[0]"
       num_mask_chip2 = num_star_chip2 + 2
       inmask_chip2 = imdir//"MCSA000"//num_mask_chip2//".fits[0]"
    }
    else if( num_star_chip1 < 1000000 ){ 
       instar_chip1 = imdir//"MCSA00"//num_star_chip1//".fits[0]"
       num_star_chip2 = num_star_chip1 + 1
       instar_chip2 = imdir//"MCSA00"//num_star_chip2//".fits[0]"
       num_mask_chip1 = num_star_chip1 + 2
       inmask_chip1 = imdir//"MCSA00"//num_mask_chip1//".fits[0]"
       num_mask_chip2 = num_star_chip2 + 2
       inmask_chip2 = imdir//"MCSA00"//num_mask_chip2//".fits[0]"
    }
    print("Star frames = ", instar_chip1, " and ", instar_chip2)
# Sky Frames
    num_sky_chip1 = isky_chip1
    if( num_sky_chip1 != 0 ){ 
       if( num_sky_chip1 < 100000 ){
          insky_chip1 = imdir//"MCSA000"//num_sky_chip1//".fits[0]" 
          num_sky_chip2 = num_sky_chip1 + 1
          insky_chip2 = imdir//"MCSA000"//num_sky_chip2//".fits[0]"
       }
       else if( num_sky_chip1 < 1000000 ){
           insky_chip1 = imdir//"MCSA00"//num_sky_chip1//".fits[0]" 
           num_sky_chip2 = num_sky_chip1 + 1
           insky_chip2 = imdir//"MCSA00"//num_sky_chip2//".fits[0]"
       }
    }
    else{ 
       insky_chip1 = "NONE" 
       insky_chip2 = "NONE"
    }
    print("Sky frames = ", insky_chip1, " and ", insky_chip2)

    configfile = cfile
   
    rootname = rootname1
    retry1 = iretry1
    retry2 = iretry2
    interac1 = iinterac1
    interac2 = iinterac2

# New tasks
#    task $sed = $foreign
    task $awk = $foreign
#    task makemosaic = "../../MOS/makemosaic.cl"
#    task $messtar = "$../../MOS/mes_star"
    task $meshole = "$../../MOS2/mes_hole.py"
    task $messtarhole = "$../../MOS2/mes_starhole.py"
    task $resviewer = "$../../MOS2/res_viewer.py"
    task $geomap = "$../../MOS2/geo_map.py"

# Check header info.
    imgets( instar_chip1, "DET-ID")
    detid1 = int(imgets.value)
    imgets( instar_chip2, "DET-ID")
    detid2 = int(imgets.value)

# Check Detector ID of the Data
    if( detid1 != 1 ){
       print( "Error: "//instar_chip1//" is not data from chip1")
    }
    if( detid2 != 2 ){
       print( "Error: "//instar_chip2//" is not data from chip2")
    }

# Subtract sky frames
    frame_ss_chip1 = rootname//"_ss_chip1.fits"
    frame_ss_chip2 = rootname//"_ss_chip2.fits"

    if(retry1 != yes ){
       imdelete(frame_ss_chip1, >&"dev$null")
       imdelete(frame_ss_chip2, >&"dev$null")
       if( insky_chip1 != "NONE" && insky_chip2 != "NONE" ){
          imarith( instar_chip1, "-", insky_chip1, frame_ss_chip1 )
          imarith( instar_chip2, "-", insky_chip2, frame_ss_chip2 )
       }
       else{
          imcopy( instar_chip1, frame_ss_chip1 )
          imcopy( instar_chip2, frame_ss_chip2 )
       }
    }

# Mosaic target frames
    frame_star = rootname//"_star.fits"
    if(retry1 != yes ){
       imdelete( frame_star )
       makemosaic( frame_ss_chip1, frame_ss_chip2, frame_star, configfile )
    }

# Mosaic mask frames
    frame_mask = rootname//"_mask.fits"
    if(retry2 != yes ){
       imdelete( frame_mask )
# added
       imdelete(frame_ss_chip1, >&"dev$null")
       imdelete(frame_ss_chip2, >&"dev$null")
       chpixtype (instar_chip1, frame_ss_chip1, "real")
       chpixtype (instar_chip2, frame_ss_chip2, "real")
#       makemosaic( instar_chip1, instar_chip2, frame_mask, configfile )
       makemosaic( frame_ss_chip1, frame_ss_chip2, frame_mask, configfile )
    }

# Apply gaussian filter
    frame_starg10 = rootname//"_starg10.fits"
    if(retry1 != yes ){
       imdelete( frame_starg10 )
       gauss( frame_star, frame_starg10, 1.0 )
    }

# Measure hole positions on the mask frame
    sbrfile = rootname//".sbr"

    mask_OK = no
    while( mask_OK != yes ){
       list_mask = rootname//"_maskcheck.coo"
       delete( list_mask, >&"dev$null" )
       if( interac1 == yes ){
          meshole( frame_mask, sbrfile, list_mask, "yes" )
       }
       else{
          meshole( frame_mask, sbrfile, list_mask, "no" )
       }
       cat( list_mask )
       print( " Are you confident with the MASK measurements ? ")
       scan(mask_OK)
    }
   
# Measure star positions on the star frame

    star_OK = no
    while( star_OK != yes ){
       list_starhole = rootname//"_starcheck.coo"
       delete( list_starhole, >&"dev$null" )
       if( interac2 == yes ){
          messtarhole( frame_starg10, list_mask, list_starhole, "yes" )
       }
       else{
          messtarhole( frame_starg10, list_mask, list_starhole, "no" )
       }

       cat( list_starhole )
       print( " Are you confident with the STAR measurements ? ")
       scan(star_OK)
    }

# Combine the results
    list_starmask = rootname//"_starmaskcheck.coo"
    delete( list_starmask, >&"dev$null" )
    list1 = list_starhole
    while( fscan( list1, data1, data2, data3, data4 ) == 4 ){
        printf( "%s %s %s %s \n", data1, data2, data3, data4, >> list_starmask )
    }
   print( list_starhole )

# Calculate offset value
    log_mesoffset = rootname//"_log"

# Geotran and plot measure results
    log_mesoffset = rootname//"_log"
    print("=======================================================", >> log_mesoffset)
    print("mesoffset3b :", >> log_mesoffset)
    list_geotran = rootname//"_starmask.dbs"
    list_geores  = rootname//"_starmask.res"
    resviewer( frame_starg10, list_starmask, list_geotran, log_mesoffset, results=list_geores )

    print("This procedure ended ......")
    print("Log file written in ",log_mesoffset)
    print(" ")
    list1=""
       imdelete(frame_ss_chip1, >&"dev$null")
       imdelete(frame_ss_chip2, >&"dev$null")

end
