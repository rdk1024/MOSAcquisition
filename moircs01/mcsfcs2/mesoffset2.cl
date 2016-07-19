# -------------------------------------------

#   Measure offset between STAR and HOLE
#    All in one sequence for STARHOLE images measurements
#
#        Ver 1.0 2006/05/10 Masayuki Akiyama
#        Ver 2   20090105 K. Aoki
#         Revised by IT at 2013-04-09 for da2 work
#         2016-04-13: Updated for numoircs
#
#   USAGE:
#       istar_chip1, istar_chip2 : STAR frame name
#       isky_chip1, isky_chip2 : SKY frame name, if available. If no sky frame, NONE 
#       rootname1 : SBR filename without .sbr
#       cfile : MCSRED configuration file
#       iretry1 : If iretry1=yes, mosaicing STARMASK frames will be skipped
#       interac1 : Interactive ?
# -------------------------------------------

#procedure mesoffset2( istarhole_chip1, isky_chip1, rootname1, cfile, iretry1, iinterac1 )
procedure newmesoffset2( istarhole_chip1, isky_chip1, rootname1, cfile)

int     istarhole_chip1   {prompt = ' Input chip1 STAR frame NUMBER :'}
int     isky_chip1        {prompt = ' Input chip1 SKY frame NUMBER, if not available "0" :'}
string  rootname1         {prompt = ' SBR file name (without .sbr) used as rootname):'}
file    cfile             {"dir_mcsred$DATABASE/ana_apr16.cfg", prompt = ' Configuration file in MCSRED format :'}
string  imdir            {"data$", prompt="Raw Data Directory"}
bool    iretry1           {no, prompt = ' Re-use mosaiced images from previous measure ? :'}
bool    iinterac1         {yes, prompt = ' Interactive messtarhole ? :'}

struct *list1

begin
    int       num_starhole_chip1, num_starhole_chip2
    string    instarhole_chip1, instarhole_chip2
    int       num_sky_chip1, num_sky_chip2
    string    insky_chip1, insky_chip2

    string    frame_ss_chip1, frame_ss_chip2
    string    frame_starhole, frame_starholeg10, frame_mask
    string    log_mesoffset
    string    list_star, list_mask, list_starmask
    string    list_starhole
    string    list_geotran, list_geores

    int       detid1, detid2
    string    configfile
    string    sbrfile
    real      data1, data2, data3
    real      data4, data5, data6
    string    rootname
    bool      retry1
    bool      interac1

    bool      starhole_OK

# Starhole Frames
    num_starhole_chip1 = istarhole_chip1
    if( num_starhole_chip1 < 100000 ){
       instarhole_chip1 = imdir//"MCSA000"//num_starhole_chip1//".fits[0]"
       num_starhole_chip2 = num_starhole_chip1 + 1
       instarhole_chip2 = imdir//"MCSA000"//num_starhole_chip2//".fits[0]"
    }
    else if( num_starhole_chip1 < 1000000 ){
       instarhole_chip1 = imdir//"MCSA00"//num_starhole_chip1//".fits[0]"
       num_starhole_chip2 = num_starhole_chip1 + 1
       instarhole_chip2 = imdir//"MCSA00"//num_starhole_chip2//".fits[0]"
    }
    print("Starhole frames = ", instarhole_chip1, " and ", instarhole_chip2)
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
    interac1 = iinterac1

# New tasks
#    task $sed = $foreign
    task $awk = $foreign
#    task makemosaic = "$../../MOS/makemosaic.cl"
#    task $messtar = "$../../MOS/mes_star"
#    task $meshole = "$../../MOS/mes_hole"
    task $messtarhole_b = "$../../MOS2/mes_starhole_b.py"
    task $resviewer = "$../../MOS/res_viewer"
    task $geomap = "$../../MOS2/geo_map.py"

# Check header info.
    imgets( instarhole_chip1, "DET-ID")
    detid1 = int(imgets.value)
    imgets( instarhole_chip2, "DET-ID")
    detid2 = int(imgets.value)

# Check Detector ID of the Data
    if( detid1 != 1 ){
       print( "Error: "//instarhole_chip1//" is not data from chip1")
    }
    if( detid2 != 2 ){
       print( "Error: "//instarhole_chip2//" is not data from chip2")
    }

# Subtract sky frames
    frame_ss_chip1 = rootname//"_ss_chip1.fits"
    frame_ss_chip2 = rootname//"_ss_chip2.fits"

    if(retry1 != yes ){
       imdelete(frame_ss_chip1, >&"dev$null")
       imdelete(frame_ss_chip2, >&"dev$null")
       if( insky_chip1 != "NONE" && insky_chip2 != "NONE" ){
          imarith( instarhole_chip1, "-", insky_chip1, frame_ss_chip1 )
          imarith( instarhole_chip2, "-", insky_chip2, frame_ss_chip2 )
       }
       else{
          imcopy( instarhole_chip1, frame_ss_chip1 )
          imcopy( instarhole_chip2, frame_ss_chip2 )
       }
    }

# Mosaic target frames
    frame_starhole = rootname//"_starhole.fits"
    if(retry1 != yes ){
       imdelete( frame_starhole )
       makemosaic( frame_ss_chip1, frame_ss_chip2, frame_starhole, configfile )
    }

# Apply gaussian filter
    frame_starholeg10 = rootname//"_starholeg10.fits"
    if(retry1 != yes ){
       imdelete( frame_starholeg10 )
       gauss( frame_starhole, frame_starholeg10, 1.0 )
    }

# Measure star positions on the star frame
    starhole_OK = no
    while( starhole_OK != yes ){
       sbrfile = rootname//".sbr"
       list_starhole = rootname//"_starhole.coo"
       list_mask = rootname//"_mask.coo"
       delete( list_starhole, >&"dev$null" )
       if( interac1 == yes ){
          messtarhole_b( frame_starholeg10, list_mask, list_starhole, "yes" )
       }
       else{
          messtarhole_b( frame_starholeg10, list_mask, list_starhole, "no" )
       }
       cat( list_starhole )
       print( " Are you confident with the STARHOLE measurements ? ")
       scan(starhole_OK)
    }

# Format the results
    list_starmask = rootname//"_starholemask.coo"
    delete( list_starmask, >&"dev$null" )
print("test",list_starhole)
    list1 = list_starhole
    while( fscan( list1, data1, data2, data3, data4 ) == 4 ){
       if( data1>0 && data2>0 && data3>0 && data4>0 ){ 
          print( data1, data2, data3, data4, >> list_starmask )
       }
    }

# Geotran
    log_mesoffset = rootname//"_log"
    list_geotran = rootname//"_starholemask.dbs"
    list_geores = rootname//"_starholemask.res"
    geomap( frame_starhole, list_starmask, list_geotran, log_mesoffset, results=list_geores )

# Plot the results
    resviewer( list_geores )

    print("This procedure ended ......")
    print("Log file written in ",log_mesoffset)
    print(" ")
    list1=""
       imdelete(frame_ss_chip1, >&"dev$null")
       imdelete(frame_ss_chip2, >&"dev$null")

end
