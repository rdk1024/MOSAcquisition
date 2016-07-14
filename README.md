# MOSAcquisition
A series of scripts and plugins that use Ginga to align the Multi Object Camera and Spectrograph system for Subaru Telecope.

## Installation
### Dependencies
This package makes use of numpy, astropy, and ginga. To install, simply use  
`pip install numpy astropy ginga`  
It also requires much of the existing MOIRCS Acquisition software, which is not on the internet as far as I know, so if you don't work for Subaru, ha ha, too bad.

### Installation
The files in this repository need to go in several different places:  
The .ginga subdirectory (might be invisible) must be merged with $HOME/.ginga.
The moircs01 subdirectory must be merged with $HOME/moircs01.  
Now, assuming you have the rest of the MOS Acquisition stuff and you know how to use it, it should work just fine.

## Liscense
Copyright (c) 2016, Justin Kunimune

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met: 

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer. 

* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the
  distribution. 

* Neither the name of Justin Kunimune nor the names of any
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 
