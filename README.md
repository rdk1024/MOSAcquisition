# MOSAcquisition
A Ginga local plugin to align the *Multi Object Camera and Spectrograph*
system for Subaru Telecope.

## Installation
### Dependencies
This package requires a Python interpreter. It also makes use of astropy,
ginga, matplotlib, numpy, and pyraf. To install those packages, simply call  
`$ pip install astropy ginga matplotlib numpy pyraf`  
It also requires much of the existing MOIRCS Acquisition software, which is not
on the internet as far as I know, so if you don't work for Subaru, ha ha, too
bad.

### File Locations
The folders in this repository must be merged with the corresponding files in
the user's `.ginga` folder, which should either be at `/.ginga` or `~/.ginga`,
and might be invisible; `plugins` merges with `plugins`, and `util` merges with
`util`.

## Usage
Once this plugin has been installed as specified above, navigate to the
directory with your .sbr mask definition file and start ginga with the command    
`$ ginga --plugins=MESOffset`  
This should launch Ginga with the MESOffset plugin loaded. Click on 'Operation'
and then 'MESOffset' to begin the process. From there, enter any information it
asks for and follow the instructions.

## License
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

