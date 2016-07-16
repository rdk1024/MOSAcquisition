# -------------------------------------------
#
#   Measure offset between STAR and HOLE
#    All in one sequence for STAR, MASK images measurements
#
#        Ver 1.0 2006/05/10 Masayuki Akiyama
#         Revised by IT at 2013-04-09 for da2 work
#         2016-04-13: Updated for numoircs
#
#   USAGE:
#       istar_chip1 : STAR frame name
#       isky_chip1  : SKY frame name, if available. If no sky frame,NONE 
#       rootname1 : SBR filename without .sbr
#       cfile : MCSRED configuration file
#       iretry1 : If iretry1=yes, mosaicing of STAR frames will be skipped
#       iretry2 : If iretry2=yes, mosaicing of MASK frames will be skipped
#       iinter1 : If Iinter1=yes, star position measurement in interactive mode.
#       iinter2 : If Iinter2=yes, hole position measurement in interactive mode.
# -------------------------------------------

#procedure mesoffset1( istar_chip1, isky_chip1, rootname1, cfile, iretry1, iretry2,iinter1, iinter2 )
procedure mesoffset1( istar_chip1, isky_chip1, rootname1, cfile)

int     istar_chip1      {prompt = ' Input chip1 STAR frame NUMBER (MCSA000?????.fits) :'}
int     isky_chip1       {prompt = ' Input chip1 SKY frame NUMBER (MCSA000?????.fits), if not available "0" :'}
string  rootname1        {prompt = ' SBR file name (without .sbr) used as rootname):'}
file    cfile            {"dir_mcsred$DATABASE/ana_apr16.cfg", prompt = ' Configuration file in MCSRED format :'}
string  imdir            {"data$", prompt="Raw Data Directory"}
bool    iretry1          {no, prompt = ' Re-use mosaiced STAR images from previous measure ? :'}
bool    iretry2          {no, prompt = ' Re-use mosaiced MASK images from previous measure ? :'}
bool    iinter1          {yes, prompt = ' Interactive star position measurement (messtar) ?:'}
bool    iinter2          {yes, prompt = ' Interactive hole position measurement (meshole) ? :'}

struct *list1
struct *list2

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
    string    list_star, list_mask, list_starmask
    string    list_geotran

    int       detid1, detid2
    string    configfile
    string    sbrfile
    real      data1, data2, data3
    real      data4, data5, data6
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
       num_mask_chip1 = num_star_chip1 + 4
       inmask_chip1 = imdir//"MCSA000"//num_mask_chip1//".fits[0]"
       num_mask_chip2 = num_star_chip2 + 4
       inmask_chip2 = imdir//"MCSA000"//num_mask_chip2//".fits[0]"
    }
    else if( num_star_chip1 < 1000000 ){ 
       instar_chip1 = imdir//"MCSA00"//num_star_chip1//".fits[0]"
       num_star_chip2 = num_star_chip1 + 1
       instar_chip2 = imdir//"MCSA00"//num_star_chip2//".fits[0]"
       num_mask_chip1 = num_star_chip1 + 4
       inmask_chip1 = imdir//"MCSA00"//num_mask_chip1//".fits[0]"
       num_mask_chip2 = num_star_chip2 + 4
       inmask_chip2 = imdir//"MCSA00"//num_mask_chip2//".fits[0]"
    }
    else if( num_star_chip1 < 10000000 ){ 
       instar_chip1 = imdir//"MCSA0"//num_star_chip1//".fits[0]"
       num_star_chip2 = num_star_chip1 + 1
       instar_chip2 = imdir//"MCSA0"//num_star_chip2//".fits[0]"
       num_mask_chip1 = num_star_chip1 + 4
       inmask_chip1 = imdir//"MCSA0"//num_mask_chip1//".fits[0]"
       num_mask_chip2 = num_star_chip2 + 4
       inmask_chip2 = imdir//"MCSA0"//num_mask_chip2//".fits[0]"
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
    interac1 = iinter1
    interac2 = iinter2

# New tasks
#    task $sed = $foreign
    task $awk = $foreign
#    task makemosaic = "$../../MOS/makemosaic.cl"
    task $messtar = "$../../MOS2/mes_star.py"
    task $meshole = "$../../MOS2/mes_hole.py"
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

# Apply gaussian filter
    frame_starg10 = rootname//"_starg10.fits"
    if(retry1 != yes ){
       imdelete( frame_starg10 )
       gauss( frame_star, frame_starg10, 1.0 )
    }

# Measure star positions on the star frame
    star_OK = no
    while( star_OK != yes ){
       sbrfile = rootname//".sbr"
       list_star = rootname//"_star.coo"
       delete( list_star, >&"dev$null" )
       if( interac1 == yes ){
          messtar( frame_starg10, sbrfile, list_star, "yes" )
       }
       else{
          messtar( frame_starg10, sbrfile, list_star, "no" )
       }

       print( " STAR measurement results " )
       cat( list_star )
       print( " Are you confident with the STAR measurements ? ")
       scan(star_OK)
    }

# Wait for mask images
    mask_ready = no
    if( retry2 != yes ){
      while( mask_ready != yes ){
         print( " Are mask images ready for analysis ? ")
         scan(mask_ready)
      }
      print( " Are MASK frames "//inmask_chip1//" and "//inmask_chip2//" ?")
      maskframe_same = no
      scan(maskframe_same)
      if( maskframe_same == no ){
         print( " Input MASK frame NUMBER (MCSA000?????.fits) for chip1 :")
         scan(num_mask_chip1)
         if( num_mask_chip1 < 100000 ){ 
            inmask_chip1 = imdir//"MCSA000"//num_mask_chip1//".fits[0]"
            num_mask_chip2 = num_mask_chip1 + 1
            inmask_chip2 = imdir//"MCSA000"//num_mask_chip2//".fits[0]"
         }
         else if( num_mask_chip1 < 1000000 ){ 
            inmask_chip1 = imdir//"MCSA00"//num_mask_chip1//".fits[0]"
            num_mask_chip2 = num_mask_chip1 + 1
            inmask_chip2 = imdir//"MCSA00"//num_mask_chip2//".fits[0]"
         }
         print("Mask frames = ", inmask_chip1, " and ", inmask_chip2)
    
      }
    }

# Mosaic mask frames
    frame_mask = rootname//"_mask.fits"
    if(retry2 != yes ){
       imdelete( frame_mask )
# added
       imdelete(frame_ss_chip1, >&"dev$null")
       imdelete(frame_ss_chip2, >&"dev$null")
       chpixtype (inmask_chip1, frame_ss_chip1, "real")
       chpixtype (inmask_chip2, frame_ss_chip2, "real")
#       makemosaic( inmask_chip1, inmask_chip2, frame_mask, configfile )
       makemosaic( frame_ss_chip1, frame_ss_chip2, frame_mask, configfile )
    }

# Measure hole positions on the mask frame
   mask_OK = no
   while( mask_OK != yes ){
#       print( " Interactive mes_hole ? :")
#       scan( interac2 )
      list_mask = rootname//"_mask.coo"
      delete( list_mask, >&"dev$null" )
#       if( interac2 == yes ){
      meshole( frame_mask, sbrfile, list_mask, "yes" )
#       }
#       else{
#          meshole( frame_mask, sbrfile, list_mask, "no" )
#       }
       cat( list_mask )
       print( " Are you confident with the MASK measurements ? ")
       scan(mask_OK)
    }
   
# Combine the results
    list_starmask = rootname//"_starmask.coo"
    list1 = list_star
    list2 = list_mask
    delete( list_starmask, >&"dev$null" )
    print("Input data to geomap :")
    while( fscan( list1, data1, data2 ) == 2 && fscan( list2, data4, data5, data6 ) == 3 ){
       if( data1>0 && data2>0 && data4>0 && data5>0 ){ 
          print( data4, data5, data1, data2, >> list_starmask )
          print( data4, data5, data1, data2 )
       }
    }

# Geotran
    list_geotran = rootname//"_starmask.dbs"
    geomap( frame_starg10, list_starmask, list_geotran, xmin=INDEF, xmax=INDEF, ymin=INDEF, ymax=INDEF )

# Calculate offset value
    log_mesoffset = rootname//"_log"
    print("=======================================================", >> log_mesoffset)
    print("mesoffset1 :", >> log_mesoffset)
    print("=======================================================")
    print("")
    print("=========================================== ")
    print("==       USE TELOFFSET MODE ANA          == ")
    print("== Put dx dy rotate to the ANA window    ==")
    print("== Ignore dx less than 0.5 (pix)         ==")
    print("== Ignore dy less than 0.5 (pix)         ==")
    print("== Ignore rotate less than 0.01 (degree) ==")
    print(" ========================================== ")
    date( >> log_mesoffset )
    awk ("-f ../../MOS/results.awk", list_geotran, >> log_mesoffset  ) 
    print("")
    print("=======================================================")

    print("This procedure ended ......")
    print("Log file written in ",log_mesoffset)
    print(" ")
    list1=""
    list2=""

end
