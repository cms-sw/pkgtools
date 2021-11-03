The PKGTOOLS package contains the scripts needed for handling the 
packaging of software packages built and distributed as part of the cms 
software/computing. The spec files describing how to build any given
package are in a separate package called CMSDIST.

SETTING UP A WORKING BUILD ENVIRONMENT
======================================

While cmsBuild tries to be as self consistent as possible a few external
dependencies are required to create the initial bootstrap kit.

In particular, on platforms which do not provide rpm (e.g. macosx) you need to
build an initial rpm to build a bootstrap kit. This can be done by using the
`build_rpm.sh` script, e.g.:

  PKGTOOLS/build_rpm.sh --prefix /usr/local

DOCUMENTATION
=============

Documentation is found in the docs directory, in the form of a bunch of 
markdown formatted text files. For an HTML version, simply open the 
`PKGTOOLS/docs/index.html` file. Deployment of web pages on the server can be 
done by simply copying the docs directory in some web area.

LICENSE
=======

This software is provided under FERMILAB variation of the BSD license. For the
full disclaimer see docs/license.txt
  
