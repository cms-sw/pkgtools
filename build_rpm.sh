#!/bin/sh
# Builds a standalone version of RPM suitable for building the bootstrap kit.
# This is required for all those platforms which do not provide a suitable rpm.

PREFIX=/usr/local/bin
BUILDPROCESSES=2

while [ $# -gt 0 ]
do
  case "$1" in
    --prefix)
      if [ $# -lt 2 ] 
      then 
        echo "--prefix option wants an argument. Please specify the installation path." ; exit 1
      fi
      if [ ! "X`echo $2 | cut -b 1`" = "X/" ] 
      then 
        echo "--prefix takes an absolute path as an argument." ; exit 1 
      fi
      PREFIX=$2
      shift ; shift
    ;;
    --64bit)
      NSPR_CONFIGURE_OPTS="--enable-64bit"
      NSS_USE_64=1
      shift
    ;;
    -j)
      if [ $# -lt 2 ]
      then
        echo "-j option wants an argument. Please specify the number of build processes." ; exit 1
      fi
      BUILDPROCESSES=$2 
      shift ; shift
    ;;
    --help)
      echo "usage: build_rpm.sh [--prefix PREFIX] [--64bit] [-j N]"
      exit 1
    ;;
    *)
      echo "Unsupported option $1"
      exit 1
    ;;
  esac
done

HERE=$PWD

set -e
# Fetch the sources.
curl https://ftp.mozilla.org/pub/mozilla.org/nspr/releases/v4.8.4/src/nspr-4.8.4.tar.gz | gzip -dc | tar x
curl http://rpm5.org/files/popt/popt-1.15.tar.gz | gzip -dc | tar x
curl https://ftp.mozilla.org/pub/mozilla.org/security/nss/releases/NSS_3_12_6_RTM/src/nss-3.12.6.tar.gz | gzip -dc | tar x
curl ftp://ftp.fu-berlin.de/unix/tools/file/file-5.04.tar.gz | gzip -dc | tar x
curl http://download.oracle.com/berkeley-db/db-4.5.20.tar.gz | tar xz
curl http://rpm.org/releases/rpm-4.8.x/rpm-4.8.0.tar.bz2 | tar xj

# Build required externals.
cd $HERE/file-5.04
./configure --disable-rpath --enable-static --disable-shared --prefix $PREFIX CFLAGS=-fPIC
make -j $BUILDPROCESSES ; make install

cd $HERE/nspr-4.8.4/mozilla/nsprpub
./configure --disable-rpath --prefix $PREFIX $NSPR_CONFIGURE_OPTS
make -j $BUILDPROCESSES ; make install

cd $HERE/nss-3.12.6
export USE_64=$NSS_USE_64
export NSPR_INCLUDE_DIR=$PREFIX/include/nspr
export NSPR_LIB_DIR=$PREFIX/lib
export FREEBL_NO_DEPEND=1
make -C ./mozilla/security/coreconf clean
make -C ./mozilla/security/dbm clean
make -C ./mozilla/security/nss clean
make -C ./mozilla/security/coreconf
make -C ./mozilla/security/dbm
make -C ./mozilla/security/nss
install -d $PREFIX/include/nss3
install -d $PREFIX/lib
find mozilla/dist/public/nss -name '*.h' -exec install -m 644 {} $PREFIX/include/nss3 \;
find . -path '*/mozilla/dist/*.OBJ/lib/*.dylib' -exec install -m 755 {} $PREFIX/lib \;
find . -path '*/mozilla/dist/*.OBJ/lib/*.so' -exec install -m 755 {} $PREFIX/lib \;

cd $HERE/popt-1.15
./configure --disable-shared --enable-static --disable-nls \
            --prefix $PREFIX CFLAGS=-fPIC
make -j $BUILDPROCESSES ; make install

cd $HERE/db-4.5.20/build_unix
../dist/configure --enable-static --disable-shared --disable-java \
  --disable-rpc --prefix=$PREFIX --with-posixmutexes CFLAGS=-fPIC
make -j $BUILDPROCESSES ; make install

# Build the actual rpm distribution.
cd $HERE/rpm-4.8.0
rm -rf lib/rpmhash.*
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-case-insensitive-sources.patch?revision=1.1" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-add-missing-__fxstat64.patch?revision=1.1" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-case-insensitive-fixes.patch?revision=1.1" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-fix-glob_pattern_p.patch?revision=1.1" | patch -p1    
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-remove-chroot-check.patch?revision=1.1" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-remove-strndup.patch?revision=1.1" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-allow-empty-buildroot.patch?revision=HEAD" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-fix-missing-libgen.patch?revision=HEAD" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-fix-find-provides.patch?revision=HEAD" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-increase-line-buffer.patch?revision=HEAD" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-increase-macro-buffer.patch?revision=HEAD" | patch -p1

case `uname` in
  Darwin)
    export DYLD_LIBRARY_PATH=$PREFIX/lib 
    USER_CFLAGS=-fnested-functions
    USER_LIBS=-liconv
    LIBPATHNAME=DYLD_LIBRARY_PATH
  ;;
  Linux)
    export LD_LIBRARY_PATH=$PREFIX/lib
    LIBPATHNAME=LD_LIBRARY_PATH
  ;;
esac

./configure --prefix $PREFIX \
    --with-external-db --disable-python --disable-nls \
    --disable-rpath --disable-lua --without-lua \
    CFLAGS="-ggdb -O0 $USER_CFLAGS -I$PREFIX/include/nspr \
            -I$PREFIX/include/nss3" \
    LDFLAGS="-L$PREFIX/lib" \
    CPPFLAGS="-I$PREFIX/include/nspr \
          -I$PREFIX/include \
          -I$PREFIX/include/nss3" \
    LIBS="-lnspr4 -lnss3 -lnssutil3 \
          -lplds4 -lplc4 -lz -lpopt \
          -ldb $USER_LIBS"
make -j $BUILDPROCESSES ; make install

perl -p -i -e 's|^.buildroot|#%%buildroot|' $PREFIX/lib/rpm/macros
echo "# Build done."
echo "# Please add $PREFIX/lib to your $LIBPATHNAME and $PREFIX/bin to your path in order to use it."
echo "# E.g. "
echo "export PATH=$PREFIX/bin:\$PATH"
echo "export $LIBPATHNAME=$PREFIX/lib:\$$LIBPATHNAME"
