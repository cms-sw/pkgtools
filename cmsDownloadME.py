#!/usr/bin/env python

#
# June 21, 2008
# dlange, LLNL
#
# Simple script to retrieve ME directory listings
#

import md5
import os
from os.path import join, getsize
import sys
import optparse
import urllib2

usage=\
"""%prog <TYPE> [options].
Examples:
%prog -arch slc4_ia32_gcc345 -gen madgraph --cat QCD --energy 10TeV --version 4.2.11-cms1
"""

parser=optparse.OptionParser(usage)

parser.add_option("-a","--arch",
                  help="The CMSSW architecture (default=slc4_ia32_gcc345)",
                  default="slc4_ia32_gcc345",
                  dest="arch");
parser.add_option("-g","--gen",
                  help="The generator to retrieve MEs for",
                  default="",
                  dest="gen");
parser.add_option("-c","--cat",
                  help="The category of MEs (eg, QCD)",
                  default="",
                  dest="cat");
parser.add_option("-e","--energy",
                  help="The energy of MEs (eg, 10TeV)",
                  default="",
                  dest="energy");
parser.add_option("-v","--ver",
                  help="The version of MEs (eg, 4.2.11-cms1)",
                  default="",
                  dest="ver");


(options,args) = parser.parse_args() # by default the arg is sys.argv[1:]


baseDirWeb='http://cmsrep.cern.ch/cmssw/ME/'
listFileEnding='list'
cmsswbase=os.environ.get('CMS_PATH')
#hack for cern software area
if cmsswbase=='/afs/cern.ch/cms':
    cmsswbase='/afs/cern.ch/cms/sw'

if cmsswbase is None:
    print 'Missing CMSSW_BASE variable to define SW area'
    sys.exit(1)

req=urllib2.Request(baseDirWeb)
try: website=urllib2.urlopen(req)
except IOError, e:
    print 'Can not talk to cmsrep web server. Network problem?'
    sys.exit()    

dlist=website.read()

archList={}
genList={}
catList={}
energyList={}
versionList={}

for line in dlist.split('\n'):
    if ( line.find(listFileEnding)>-1):
        href=line.split('<a')[1].split('</a>')[0].split('">')[1]
        archList[href]=href.split(':')[0]
        genList[href]=href.split(':')[1]
        energyList[href]=href.split(':')[2]
        catList[href]=href.split(':')[3]
        versionList[href]=(href.split(':')[4])[0:-5]

if options.gen == '':
    print 'no generator (--gen) specified. For this arch, choices are:'
    tmpDict={}
    for ent in archList:
        if archList[ent] == options.arch:
            gen=genList[ent]
            if gen not in tmpDict:
                tmpDict[gen]=1
                print '    ' + gen
    sys.exit(0)            

if options.energy == '':
    print 'no energy (--energy) specified. For this arch/generator, choices are:'
    tmpDict={}
    for ent in archList:
        if archList[ent] == options.arch:
            if genList[ent] == options.gen:
                energy=energyList[ent]
                if energy not in tmpDict:
                    tmpDict[energy]=1
                    print '    ' + energy
    sys.exit(0)            

if options.cat == '':
    print 'no category (--cat) specified. For this arch/generator/energy, choices are:'
    tmpDict={}
    for ent in archList:
        if archList[ent] == options.arch:
            if genList[ent] == options.gen:
                if energyList[ent] == options.energy:
                    cat=catList[ent]
                    if cat not in tmpDict:
                        tmpDict[cat]=1
                        print '    ' + cat
    sys.exit(0)            

if options.ver == '':
    print 'no version (--ver) specified. For this arch/generator/category, choices are:'
    tmpDict={}
    for ent in archList:
        if archList[ent] == options.arch:
            if genList[ent] == options.gen:
                if energyList[ent] == options.energy:
                    if catList[ent] == options.cat:
                        ver=versionList[ent]
                        if ver not in tmpDict:
                            tmpDict[ver]=1
                            print '    ' + ver
    sys.exit(0)            

fileExpected=options.arch+':'+options.gen+':'+options.energy+':'+options.cat+':'+options.ver+'.'+ listFileEnding

if ( fileExpected not in archList):
    print 'No MEs for arch='+options.arch+' generator='+options.gen+' energy='+options.energy+' category='+options.cat+' version='+options.ver+' found'
    print 'Remove --ver, --cat, --energy and/or --gen arguments to find available'
    print 'options for this architecture'
    sys.exit(0)

 # otherwise we have work to do.

 
req2=urllib2.Request(baseDirWeb+'/'+fileExpected)
try: listFile=urllib2.urlopen(req2)
except IOError, e:
    print 'Can not talk to cmsrep web server. Network problem?'
    sys.exit()    

listing=listFile.read()

for line in listing.split('\n'):
    if ( len(line.split(' '))==2):
        file=line.split(' ')[0]
        md5Server=line.split(' ')[1]
        fileOut=cmsswbase+'/'+file[file.find(baseDirWeb)+len(baseDirWeb):]
        print 'Considering: '+fileOut
        
        needToGet=0
        if ( os.path.exists(fileOut)):
            mysum=md5.md5(open(fileOut).read()).hexdigest()
            if ( mysum == md5Server):
                print '    File already downloaded'
            else:
                print '    Refetching file (changed on server)....'
                needToGet=1
        else:        
            print '    Fetching file (new)....'
            needToGet=1
            dir=os.path.dirname(fileOut)
            if not os.path.exists(dir):
                os.makedirs(dir)
            if not os.path.exists(dir):
                print 'Could not create directory to download file'
                print dir
                print 'Permissions ok?'
                sys.exit(1)

# do we need to fetch the file
        if ( needToGet==1):
        
            req3=urllib2.Request(file)
            try: listFile=urllib2.urlopen(req3)
            except IOError, e:
                print 'Can not talk to cmsrep web server. Network problem?'
                sys.exit()    
        
            fout=open(fileOut,'w')
            fout.write(listFile.read())
            fout.close()
            print '    done.'
    else:
        if ( line!=''):
            print 'Unknown line.. skipping'
            print line
