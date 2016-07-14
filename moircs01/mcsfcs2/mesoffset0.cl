# mesoffset0 -- moircs mask align script user interface:
# Created by Ichi Tanaka
#   Special thanks to Mike Lemmen for the useful discussion on UI algorithm.
#
# Last Update: 2016-06-29
# 
# MOIRCS mask alignment process uses 3 scripts below.
#  mesoffset1.cl  ... for rough alignment during the start
#  mesoffset2.cl  ... for fine alignment after mesoffset1
#  mesoffset3.cl  ... "realign" process during the observation
#
# The mesoffset0.cl script automatically fills the file names necessary to 
# run these tasks above. Users can proceed the processes interactively.
# 
# The execution mode (exemode) is the key parameter for controlling the action.
# 
#   - If exemode=normal, the script runs mesoffset1 and 2 continuously.
#
#   - If exemode=fine, the script runs mesoffset3 or mesoffset2 using the old
#      hole measurement data. You can choose the newest hole position 
#      measurement data file during mesoffset2 process.
#
# Input Parameters:
#  istar_chip1: Input chip1 STAR frame NUMBER (MCSA000?????.fits). It must 
#               be odd number. It is the first frame number after SETUPSLIT
#		starts for normal mode, or, the first frame number after
#		realignment process starts (fine mode). For fine mode, the
#		frame is always with the stars in the alignment holes.
#
#  rootname1    SBR file name (without .sbr) used as rootname.
#
#  imdir        Raw Data Directory. For the open-use observation, it will be
#   		 like '/data/o16010/'. Always check the accessibility from
#		 moircs01 account on sumda.
#
#  cfile        The mcsred configuration file. Always use the most recent one. 
#   		The SA will usually update it before the obs.
#
# exemode	The alignment mode. 'normal' or 'fine' as explained above.
# 

procedure mesoffset0 (istar_chip1, rootname1, imdir)

int     istar_chip1      {prompt = ' Input chip1 STAR frame NUMBER (MCSA000?????.fits) :'}
string  rootname1        {prompt = ' SBR file name (without .sbr) used as rootname):'}
string  exemode		 {"normal", prompt="alignment mode (normal/fine)?"}
string  imdir            {"data$", prompt="Raw Data Directory"}
file    cfile            {"dir_mcsred$DATABASE/ana_apr16.cfg", prompt = ' Configuration file in MCSRED format :'}

begin
	bool ans, ans2, useold
	int nm, nm2, j, isky_chip1
	string fnm, list_mask, list_mask2, frame_mask, holefile

	j=strlen(imdir)
	if (substr(imdir,j,j) != "/" &&  substr(imdir,j,j) != "$"){
	   print ("!!! WARNING. No / is found. adding to imdir...")
	   imdir = imdir//"/"
	}

	if (exemode == "normal"){
 	   print (">>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<")
 	   print (">>> Mode=normal -->  mesoffset1 process <<<")
 	   print (">>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<")

# input file check
  	   nm=istar_chip1
	   ans=no
	   while (ans != yes){
	      fnm = imdir//"MCSA00000000"+nm//".fits"
	      print ("    Target field image --> ", fnm)
	      print (">>> Is the input frame number correct? [y/n]")
	      scan (ans)
	      if (ans == no){
	      	 print (">>> Put the correct chip number [MCSA000?????.fits] for ch1.")
 	 	 scan (nm)
	      }
	   }
# 
  	   nm2=istar_chip1 + 2
	   ans=no
	   while (ans != yes){
	      fnm = imdir//"MCSA00000000"+nm2//".fits"
	      print ("    'SKY' data for target image --> ", fnm)
	      print (">>> Is the input SKY frame correct? [y/n]")
	      scan (ans)
	      if (ans == no){
	      	 print (">>> Put the correct chip number [MCSA000?????.fits] for ch1.")
 	 	 scan (nm2)
	      }
	      
	   }

	   ans2=no
	   while (!ans2){
           	print (">>> Are you ready to go to mesoffset1 process? [y/n]")
           	scan (ans2)
           }


# delete previously-generated hole position data by mesoffset3	   
  	       list_mask2 = rootname//"_maskcheck.coo"
	       if (access (list_mask2)) delete (list_mask2, ver-)
#
		print ("   *** Starting mesoffset1 process ***")
	   	mesoffset1 (nm, nm2, rootname1, cfile, imdir=imdir)
		nm=nm+4
	   	fnm = imdir//"MCSA00000000"+nm//".fits"

		ans2=no
	      	while (!ans2){
	          print (">>> Are you ready to go to mesoffset2 process? [y/n]")
	          scan (ans2)
	        }

		if (!access(fnm)){
		      	 print (">> !! Expected Mask Frame ", fnm, " is not found.")
		      	 print ("   Put the ch1 chip number [MCSA000?????.fits] for Mask used.")
 		      	 scan (nm)
		      	 fnm = imdir//"MCSA00000000"+nm//".fits"
	        }
		
		print (">>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<")
		print (">>>  Going to mesoffset2 (fine) process <<<")
		print (">>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<")
		nm2=nm+2
		useold = yes
	}
	else if (exemode == "fine"){
	       print (">>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<")
	       print (">>> !!!! JUMP TO MESOFFSET2/3 (fine) PROCESS !!! <<<")
	       print (">>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<")

# check the availability of the proper hole position data...
  	       list_mask = rootname//"_mask.coo"
  	       list_mask2 = rootname//"_maskcheck.coo"
	       frame_mask = rootname//"_mask.fits"

  	       if (access (list_mask) || access (list_mask2)){
	       	  print ("   !! Previous Hole Position Data is found !!")
		  ls ("-l", list_mask)
		  if (access (list_mask2))
	 		ls ("-l", list_mask2)

		  print (">>> Do you want to use the old hole position data? -- [y/n]")
		  scan (useold)
		  holefile = ""
		  if  (useold && access (list_mask2)){
		      print (">>> Which file do you want to use?")
		      scan (holefile)
		      if (holefile == list_mask) delete (list_mask2, ver-)
		  }
	       }
	       nm2 = istar_chip1
	       if (useold){
	       	  nm = nm2 - 2
		  if  (access (list_mask2) && holefile == list_mask2){
		     print ("    ... running mesoffset2 using the mask data from previous mesoffset3 task...")
		     del (list_mask, ver-)
		     cp (list_mask2, list_mask)
		  }
		  else{
		     print ("    ... running mesoffset2 using the mask data from previous mesoffset1 task...")
		  }
	       }
	       else{
	       	  nm = nm2 + 2
	       }
	}
	else{
		print ('!!!Err!!! Choose "normal" or "fine" for exemode. Bye.')
		bye
	}

#       
#
	ans=no
	while (ans != yes){
	      fnm = imdir//"MCSA00000000"+nm2//".fits"
	      print ("    ... Mask Image with stars in holes --> ", fnm)
	      print (">>> Is the input MASK+STAR frame number correct? [y/n]")
	      scan (ans)
	      if (ans == no){
	      	 print (">>> Put the correct chip number [MCSA000?????.fits] for ch1.")
 	 	 scan (nm2)
	      }
	}

	ans=no
	while (ans != yes){
	      fnm = imdir//"MCSA00000000"+nm//".fits"
	      print ("    ... Mask Image with holes only --> ", fnm)
	      print (">>> Is the input MASK image number correct? [y/n]")
	      scan (ans)
	      if (ans == no){
	      	 print (">>> Put the new chip number [MCSA000?????.fits] for ch1.")
 	 	 scan (nm)
	      }
	}

	if (useold){
# mesoffset2: check the availability of the proper hole position data...
  	      list_mask = rootname//"_mask.coo"
	      if (!access (list_mask)){
	      	 print ("!!! ERR !!! No hole position data in the current directory!")
	   	 print ("    Re-run the task with exemode=normal. Bye.") 
		 bye
	      }
#
	      ans2=no
	      while (!ans2){
	          print (">>> Is the data available and ready to go? [y/n]")
	          scan (ans2)
		  if (!access(fnm)) ans2=no
	      }
#
	      ans=no
	      while (ans != yes){
	      print ("    ** starting mesoffset2 process **") 
       	      	    mesoffset2 (nm2, nm, rootname1, cfile, imdir=imdir)
       	      	    print (">>> END? [y/n]: More Iteration -> type n.")
       	      	    scan (ans)
		    if (!ans){
       	      	        nm2=nm2+2
#  
			fnm = imdir//"MCSA00000000"+nm2//".fits"
	      	   	print ("    ...New Mask Image with stars in holes --> ", fnm)
	      	   	print (">>> Is the input MASK+STAR frame number correct? [y/n]")
	      	   	scan (ans2)
	    	   	if (ans2 == no){
		            print (">>> Put the correct chip number [MCSA000?????.fits] for ch1.")
 	 		    scan (nm2)
	      	   	}
			ans2=no
			while (!ans2){
	      	   	      print (">>> Is the data available and ready to go? [y/n]")
			      scan (ans2)
			      if (!access(fnm)) ans2=no
			}
			
			
		    }
       	      }
	      print ("!!! CONGRATURATIONS ^_^ !!!!")
	}
	else{
# mesoffset3: check the availability of the proper hole position data...
  	      list_mask = rootname//"_maskcheck.coo"
	      if (access (list_mask)){
	      	 print ("  ...Previously-measured hole position data is found...")
	   	 print ("     Note that it will be updated...") 
	      }
	      print ("    *********************************") 
	      print ("    ** starting mesoffset3 process **") 
	      print ("    *********************************") 
	      mesoffset3 (nm2, nm, rootname1, cfile, imdir=imdir)
	      nm2=nm2+2
	      ans=no
	      while (ans != yes){
       	      	    print (">>> END? [y/n]: More Iteration -> type n.")
       	      	    scan (ans)
		    if (ans) break

# during iteration mesoffset2 is used...
    	       	    list_mask = rootname//"_mask.coo"
  	       	    list_mask2 = rootname//"_maskcheck.coo"
		    print ("   ...Running mesoffset2 using the mask data from previous mesoffset3 run...")
		    del (list_mask, ver-)
		    cp (list_mask2, list_mask)
#		    
       	      	    nm2=nm2+2
		    fnm = imdir//"MCSA00000000"+nm2//".fits"
	      	    print ("   ...New Mask Image with stars in holes --> ", fnm)
	      	    print (">>> Is the input MASK+STAR frame number correct? [y/n]")
	      	    scan (ans2)
	    	    if (ans2 == no){
		       	 print (">>> Put the correct chip number [MCSA000?????.fits] for ch1.")
 	 		 scan (nm2)
	      	    }

		    ans2=no
		    while (!ans2){
	      	          print (">>> Is the data available and ready to go? [y/n]")
		          scan (ans2)
			  if (!access(fnm)) ans2=no
		    }
	      print ("    ** starting mesoffset2 process **") 
		    mesoffset2 (nm2, nm, rootname1, cfile, imdir=imdir)

       	      }
	      print ("!!! CONGRATURATIONS ^o^ !!!!")
	}

end
