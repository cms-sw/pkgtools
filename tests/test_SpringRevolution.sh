#!/bin/sh -ex
# Stress test the new command synopsis.
set -e
TESTDIR=test-spring
case `uname` in
  Darwin) 
    ARCH=osx106_amd64_gcc421
    CMSDISTTAG=CMSSW_4_2_0_pre7-ports
  ;;
  Linux)
    ARCH=slc5_amd64_gcc434
    CMSDISTTAG=pe20110307a-for4XY
  ;;
esac

rm -rf $TESTDIR
cvs -q co -r $CMSDISTTAG -d $TESTDIR/CMSDIST CMSDIST
CMSDIST=$TESTDIR/CMSDIST

#echo "Build pcre without bootstrapping."
#PKGTOOLS/cmsBuild -c $CMSDIST --no-bootstrap --work-dir $TESTDIR/a --architecture $ARCH build pcre
#echo "This should pick pcre from the server area."
PKGTOOLS/cmsBuild -c $CMSDIST --work-dir $TESTDIR/b --architecture $ARCH build pcre
echo "This should rebuild zlib in an already boostrapped area, without bootstrapping again."
echo " " >> $CMSDIST/zlib.spec
PKGTOOLS/cmsBuild -c $CMSDIST --work-dir $TESTDIR/b --architecture $ARCH build zlib
echo "This should rebuild pcre in an already boostrapped area, and use a different tag."
echo " " >> $CMSDIST/pcre.spec
PKGTOOLS/cmsBuild -c $CMSDIST --work-dir $TESTDIR/b --architecture $ARCH build pcre
echo "This should rebuild pcre in an already boostrapped area and yet another different tag."
echo " " >> $CMSDIST/pcre.spec
PKGTOOLS/cmsBuild -c $CMSDIST --work-dir $TESTDIR/b --architecture $ARCH build pcre
echo "This should pick up pcre from the repository."
rm -rf $CMSDIST/pcre.spec
cvs -q co -r $CMSDISTTAG -d $TESTDIR/CMSDIST CMSDIST
PKGTOOLS/cmsBuild -c $CMSDIST --work-dir $TESTDIR/b --architecture $ARCH build pcre
echo "This should pick up python from the repository."
rm -rf $CMSDIST/pcre.spec
rm -rf $CMSDIST/zlib.spec
cvs -q co -r $CMSDISTTAG -d $TESTDIR/CMSDIST CMSDIST
PKGTOOLS/cmsBuild -c $CMSDIST --work-dir $TESTDIR/b --architecture $ARCH build python
echo "This should rebuild zlib and all the python dependencies"
echo "#Foo" >> $CMSDIST/zlib.spec
PKGTOOLS/cmsBuild -c $CMSDIST -j 5 --work-dir $TESTDIR/b --architecture $ARCH build python
echo "This should pick up everything from the repository."
PKGTOOLS/cmsBuild --cmsdist-tag $CMSDISTTAG --work-dir $TESTDIR/b --architecture $ARCH build python

# Upload 
echo "Do not upload pcre, since its already there."
PKGTOOLS/cmsBuild -c $CMSDIST --work-dir $TESTDIR/c --architecture $ARCH upload pcre
echo "Upload pcre-cms, since its not there."
echo " " >> $CMSDIST/pcre.spec
PKGTOOLS/cmsBuild -c $CMSDIST --work-dir $TESTDIR/c --architecture $ARCH upload pcre

# Test uploaded stuff.
curl -O http://cmsrep.cern.ch/cmssw/cms/bootstrap.sh
sh -ex ./bootstrap.sh -arch $ARCH -path $TESTDIR/d setup
INIT_SH=`find $TESTDIR/d -path "/apt/" -name init.sh`
(source $INIT_SH ; apt-get update ; apt-get install external+pcre+4.4-cms) 

# Build and upload the bootstrap kit in a separate repository.
set -x
TEST_REPO=test-`whoami`
WORKDIR=$TESTDIR/f
ssh cmsbuild@cmsrep.cern.ch rm -rf /data/cmssw/test-`whoami`
PKGTOOLS/cmsBuild --repository $TEST_REPO --cmsdist-tag  pe20110324a-for43X-ports --no-bootstrap --work-dir $TESTDIR/f --architecture $ARCH upload bootstrap-driver SCRAMV1 cms-common
scp $WORKDIR/SOURCES/cms/cms-common/1.0/cmsos cmsbuild@cmsrep.cern.ch:/data/cmssw/$TEST_REPO.`whoami`/cmsos
scp $WORKDIR/$ARCH/external/bootstrap-driver/`ls -rt $WORKDIR/$ARCH/external/bootstrap-driver/ | tail -1`/$ARCH-driver.txt cmsbuild@cmsrep.cern.ch:/data/cmssw/$TEST_REPO.`whoami`
scp $WORKDIR/$ARCH/external/apt/`ls -rt $WORKDIR/$ARCH/external/apt/ | tail -1`/bin/bootstrap.sh cmsbuild@cmsrep.cern.ch:/data/cmssw/$TEST_REPO.`whoami`

curl -O http://cmsrep.cern.ch/cmssw/$TEST_REPO.`whoami`/bootstrap.sh
sh -ex ./bootstrap.sh -repository $TEST_REPO.`whoami` -arch $ARCH -path $TESTDIR/g setup
INIT_SH=`find $TESTDIR/g -path "*/apt/*/etc/*" -name init.sh`
(source $INIT_SH ; apt-get update ; apt-cache search "*")

# Test building and uploading an old CMSSW.
echo "This should not build anything and simply install CMSSW"
PKGTOOLS/cmsBuild --cmsdist-tag $CMSDISTTAG --work-dir $TESTDIR/h --architecture $ARCH upload cmssw

echo "This should build a new cmssw and install it from the temporary repository"
PKGTOOLS/cmsBuild --cmsdist-tag pe20110324a-for43X-ports --work-dir $TESTDIR/h --architecture $ARCH upload cmssw
curl -O http://cmsrep.cern.ch/cmssw/cms.`whoami`/bootstrap.sh
sh -ex ./bootstrap.sh -repository cms.`whoami` -arch $ARCH -path $TESTDIR/i setup
INIT_SH=`find $TESTDIR/i -path "*/apt/*/etc/*" -name init.sh`
(source $INIT_SH ; apt-get update ; apt-get install cms+cmssw+CMSSW_4_2_0_pre7)

# Platform specific tests.
case `uname` in
  Darwin)
    echo This should not work, because on mac there is no system gcc 4.2.3
    if PKGTOOLS/cmsBuild --work-dir $TESTDIR/c --architecture osx106_amd64_gcc423 build pcre
    then
      echo "This should not have run."
      exit 1
    fi
    echo This should not work, because on mac you cannot build slc5.
    if PKGTOOLS/cmsBuild --work-dir $TESTDIR/c --architecture slc5_amd64_gcc451 build pcre
    then
      echo "This should not have run."
      exit 1
    fi
  ;;
  Linux)
    echo This should not work, because on linux there is no gcc 4.2.3 in the CMSSW_4_2_0_pre7 tag
    if PKGTOOLS/cmsBuild --cmsdist-tag $CMSDISTTAG --work-dir $TESTDIR/c --architecture slc5_amd64_gcc423 build pcre
    then
      echo "This should not have run."
      exit 1
    fi
  ;;
esac
