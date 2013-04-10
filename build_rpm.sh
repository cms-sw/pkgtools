#!/bin/sh -e
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
    --arch)
       if [ $# -lt 2 ] 
       then 
         echo "--arch requires an architecture as argument." ; exit 1
       fi
       ARCH=$2
       shift ; shift
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
      echo "usage: build_rpm.sh --prefix PREFIX --arch SCRAM_ARCH [-j N]"
      exit 1
    ;;
    *)
      echo "Unsupported option $1"
      exit 1
    ;;
  esac
done

[ "X$ARCH" = X ] && echo "Please specify an architecture via --arch flag" && exit 1 
case $ARCH in
  *_amd64_*)
    NSPR_CONFIGURE_OPTS="--enable-64bit"
    NSS_USE_64=1
  ;;
esac

# For Mac OS X increase header size
if [[ $ARCH == osx* ]]; then
  export LDFLAGS="-Wl,-headerpad_max_install_names" 
fi

# Needed to compile on Lion. Notice in later versions of NSS the variable
# became a Makefile internal one and needs to be passed on command line.  Keep
# this in mind if we need to move to a newer NSS.
case $ARCH in
  osx10[0-6]*) ;;
  osx*) export NSS_USE_SYSTEM_SQLITE=1 ;;
esac

HERE=$PWD

set -e
# Fetch the sources.
curl https://ftp.mozilla.org/pub/mozilla.org/nspr/releases/v4.8.4/src/nspr-4.8.4.tar.gz | gzip -dc | tar x
curl http://rpm5.org/files/popt/popt-1.15.tar.gz | gzip -dc | tar x
curl https://ftp.mozilla.org/pub/mozilla.org/security/nss/releases/NSS_3_12_6_RTM/src/nss-3.12.6.tar.gz | gzip -dc | tar x
curl ftp://ftp.fu-berlin.de/unix/tools/file/file-5.04.tar.gz | gzip -dc | tar x
curl http://download.oracle.com/berkeley-db/db-4.5.20.tar.gz | tar xz
curl http://rpm.org/releases/rpm-4.8.x/rpm-4.8.0.tar.bz2 | tar xj
curl http://ftp.gnu.org/gnu/cpio/cpio-2.11.tar.bz2 | tar xj

# Build required externals.
cd $HERE/file-5.04
./configure --disable-rpath --enable-static --disable-shared --prefix $PREFIX CFLAGS=-fPIC LDFLAGS=$LDFLAGS
make -j $BUILDPROCESSES ; make install

cd $HERE/nspr-4.8.4/mozilla/nsprpub
./configure --disable-rpath --prefix $PREFIX $NSPR_CONFIGURE_OPTS
make -j $BUILDPROCESSES ; make install

cd $HERE/nss-3.12.6
export USE_64=$NSS_USE_64
export NSPR_INCLUDE_DIR=$PREFIX/include/nspr
export NSPR_LIB_DIR=$PREFIX/lib
case $ARCH in
  slc[345]*|osx*) ;;
  *)
export FREEBL_NO_DEPEND=1
  ;;
esac
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
            --prefix $PREFIX CFLAGS=-fPIC LDFLAGS=$LDFLAGS
make -j $BUILDPROCESSES ; make install

cd $HERE/db-4.5.20/build_unix
../dist/configure --enable-static --disable-shared --disable-java \
  --disable-rpc --prefix=$PREFIX --with-posixmutexes CFLAGS=-fPIC LDFLAGS=$LDFLAGS
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
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-fix-fontconfig-provides.patch?revision=HEAD" | patch -p1
curl "http://cmssw.cvs.cern.ch/cgi-bin/cmssw.cgi/COMP/CMSDIST/rpm-4.8.0-disable-internal-dependency-generator-libtool.patch?revision=HEAD" | patch -p1

case `uname` in
  Darwin)
    export DYLD_FALLBACK_LIBRARY_PATH=$PREFIX/lib
    USER_CFLAGS=-fnested-functions
    USER_LIBS=-liconv
    LIBPATHNAME=DYLD_FALLBACK_LIBRARY_PATH
  ;;
  Linux)
    export LD_FALLBACK_LIBRARY_PATH=$PREFIX/lib
    LIBPATHNAME=LD_FALLBACK_LIBRARY_PATH
  ;;
esac

./configure --prefix $PREFIX \
    --with-external-db --disable-python --disable-nls \
    --disable-rpath --disable-lua --without-lua \
    CFLAGS="-ggdb -O0 $USER_CFLAGS -I$PREFIX/include/nspr \
            -I$PREFIX/include/nss3" \
    LDFLAGS="-L$PREFIX/lib $LDFLAGS" \
    CPPFLAGS="-I$PREFIX/include/nspr \
          -I$PREFIX/include \
          -I$PREFIX/include/nss3" \
    LIBS="-lnspr4 -lnss3 -lnssutil3 \
          -lplds4 -lplc4 -lz -lpopt \
          -ldb $USER_LIBS"

make -j $BUILDPROCESSES && make install

# Install GNU cpio
cd $HERE/cpio-2.11

# For Mac OS X patch cpio, otherwise compilation will fail
# NOTE: This patch should not be needed for newer GNU cpio
if [ `uname` = Darwin ]; then
  echo ABC2
  cat > cpio_osx_fix_stat.patch <<PATCH_FILE
--- src/filetypes.h.orig  2012-01-05 15:09:42.000000000 +0100
+++ src/filetypes.h 2012-01-05 15:10:20.000000000 +0100
@@ -82,4 +82,6 @@
 #define lstat stat
 #endif
 int lstat ();
+#ifndef stat
 int stat ();
+#endif
PATCH_FILE

  patch -p0 < cpio_osx_fix_stat.patch
fi

./configure --disable-rpath --disable-nls \
    --exec-prefix=$PREFIX --prefix=$PREFIX \
    CFLAGS=-fPIC LDFLAGS=$LDFLAGS
make -j $BUILDPROCESSES && make install

# For Mac OS X hardcode full paths to the RPM libraries, otherwise cmsBuild
# will fail with fatal error: "unable to find a working rpm."
if [ `uname` = Darwin ]; then
  echo "Mac OS X detected."
  echo "Fixing executables and dynamic libraries..."
  FILES=`find $PREFIX/bin -type f ; find $PREFIX/lib -name '*.dylib' -type f`
  for FILE in $FILES; do
    FILE_TYPE=`file --mime -b -n $FILE`
    if [ "$FILE_TYPE" != "application/octet-stream; charset=binary" ]; then
      continue
    fi

    NUM=`otool -L $FILE | grep '@executable_path' | wc -l`
    if [ $NUM -ne 0 ]; then
      FIX_TYPE="Executable:"
      SO_PATHS=`otool -L $FILE | grep '@executable_path' | cut -d ' ' -f 1`

      for SO_PATH in $SO_PATHS; do
        LIB_NAME=`echo $SO_PATH | cut -d '/' -f 2`
        install_name_tool -change $SO_PATH $PREFIX/lib/$LIB_NAME $FILE
      done

      if [[ $FILE = *.dylib ]]; then
        FIX_TYPE="Library:"
        SO_NAME=`otool -L $FILE | head -n 1 | cut -d ':' -f 1`
        install_name_tool -id $SO_NAME $FILE
      fi

      echo "$FIX_TYPE $FILE"
    fi

  done
fi

echo "Removing broken symlinks..."
for i in `find $PREFIX/bin -type l`; do
  if [ ! -e $i ]; then
    echo "Broken symlink: $i"
    rm -f $i
  fi
done

perl -p -i -e 's|^.buildroot|#%%buildroot|' $PREFIX/lib/rpm/macros
echo "# Build done."
echo "# Please add $PREFIX/lib to your $LIBPATHNAME and $PREFIX/bin to your path in order to use it."
echo "# E.g. "
echo "export PATH=$PREFIX/bin:\$PATH"
echo "export $LIBPATHNAME=$PREFIX/lib:\$$LIBPATHNAME"
