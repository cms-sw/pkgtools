#!/usr/bin/env python

#
# June 21, 2008
# dlange, LLNL
#
# Simple script to regenerate ME directory listings
#
# Output is series of files in baseDir (defined below)
import md5
import os
from os.path import join, getsize


baseDir='/data/generatorData'
baseDirWeb='http://cmsrep.cern.ch/cmssw/ME/'
listFileEnding='list'
contents={}
mydirs={}

# find all files except for our list files
# under the baseDir

for root, dirs, files in os.walk(baseDir):
    if ( root.find('save')==-1):
        for file in files:
            if ( root != baseDir):
                mysum=md5.md5(open(root+'/'+file).read()).hexdigest()
                contents[root+':'+file]=mysum
                mydirs[root]=1
            else:
                if ( file.split('.')[-1] == listFileEnding ):
                    if ( not os.path.exists(baseDir+'/save')):
                        os.mkdir(baseDir+'/save')
                    os.rename(root+'/'+file,root+'/save/'+file)

# Ok, now for each directly with a file, write out a list file

#-ap: as the version dir may contain subdirs (e.g. sherpa/7TeV/EXO/1.2.1-cms/...)
# first move the existing list files to a backup :
import glob
listFiles = glob.glob('slc*.list')
for lf in listFiles:
    print 'backing up ', lf
    os.rename(lf, lf+'-bkp')

for dir in mydirs:
    webDirSP=dir.split('/')[3:]
    if ( len(webDirSP)<6):
        continue
    webloc=baseDirWeb
    for w in webDirSP:
        webloc=webloc+w+'/'
#magic -- <arch>_<generator>_<energy>_<subdir>_<version>
    outFile=baseDir+'/'+webDirSP[0]+':'+webDirSP[2]+':'+webDirSP[3]+':'+webDirSP[4]+':'+webDirSP[5]+'.'+listFileEnding

    #-ap: now first check if the file was already opened, if so, append:
    if os.path.exists(outFile):
        fout=open(outFile,'a')
    else:
        fout=open(outFile,'w')
    for entry in contents:
        eDir=entry.split(':')[0]
        eFile=entry.split(':')[1]
        if ( eDir == dir ):
            webFile=webloc+eFile    
            fout.write(webFile + ' ' + contents[entry]+'\n')
    fout.close()        
