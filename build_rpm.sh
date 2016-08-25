#!/bin/sh -e
# Builds a standalone version of RPM suitable for building the bootstrap kit.
# This is required for all those platforms which do not provide a suitable rpm.

PREFIX=/usr/local/bin
BUILDPROCESSES=2

case ${ARCH} in
  osx*)
    # Darwin is not RPM based, explicitly go for guessing the triplet
    CONFIG_BUILD=guess
    ;;
  *)
    # Assume Linux distro is RPM based and fetch triplet from RPM
    CONFIG_BUILD=auto
    ;;
esac

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
    --build)
      if [ $# -lt 2 ]
      then
        echo "--build requires a triplet/auto/guess as an argument."; exit 1
      fi
        CONFIG_BUILD=$2
        shift; shift
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

case ${ARCH} in
  osx*)
    # Darwin is not RPM based, explicitly go for guessing the triplet
    CONFIG_BUILD=guess
    ;;
  *)
    # Assume Linux distro is RPM based and fetch triplet from RPM
    CONFIG_BUILD=auto
    ;;
esac

set -e

IS_ONLINE=
case ${ARCH} in 
  *onl_*_*)
    IS_ONLINE=1
  ;;
esac

[ "X${ARCH}" = X ] && echo "Please specify an architecture via --arch flag" && exit 1 
case ${ARCH} in
  *_amd64_*|*_mic_*)
    NSPR_CONFIGURE_OPTS="--enable-64bit"
    NSS_USE_64=1
  ;;
esac

# For Mac OS X increase header size
case ${ARCH} in
  osx*)
    export LDFLAGS="-Wl,-headerpad_max_install_names"
  ;;
esac

# Needed to compile on Lion. Notice in later versions of NSS the variable
# became a Makefile internal one and needs to be passed on command line.  Keep
# this in mind if we need to move to a newer NSS.
case $ARCH in
  osx10[4-6]*) ;;
  osx*) export NSS_USE_SYSTEM_SQLITE=1 ;;
esac

HERE=$PWD

case $CONFIG_BUILD in
  auto)
    which rpm >/dev/null
    if [ $? -ne 0 ]; then
      echo "The system is not RPM based. Cannot guess build/host triplet."
      exit 1
    fi
    CONFIG_BUILD=$(rpm --eval "%{_build}")
    echo "System reports your triplet is $CONFIG_BUILD"
  ;;
  guess)
    curl -k -s -o ./config.guess 'http://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.guess;hb=HEAD'
    if [ $? -ne 0 ]; then
      echo "Could not download config.guess from git.savannah.gnu.org."
      exit 1
    fi
    chmod +x ./config.guess
    CONFIG_BUILD=$(./config.guess)
    echo "Guessed triplet is $CONFIG_BUILD"
  ;;
  *)
    curl -k -s -o ./config.sub 'http://git.savannah.gnu.org/gitweb/?p=config.git;a=blob_plain;f=config.sub;hb=HEAD'
    if [ $? -ne 0 ]; then
      echo "Could not download config.sub from git.savannah.gnu.org."
      exit 1
    fi
    chmod +x ./config.sub
    CONFIG_BUILD=$(./config.sub $CONFIG_BUILD)
    echo "Adjusted triplet is $CONFIG_BUILD"
  ;;
esac

CONFIG_HOST=$CONFIG_BUILD
 
# Fetch the sources.
curl -k -s -S https://ftp.mozilla.org/pub/mozilla.org/nspr/releases/v4.9.5/src/nspr-4.9.5.tar.gz | tar xvz
curl -k -s -S http://rpm5.org/files/popt/popt-1.16.tar.gz | tar xvz
[ ! $IS_ONLINE ] && curl -k -s -S http://zlib.net/zlib-1.2.8.tar.gz | tar xvz
curl -k -s -S https://ftp.mozilla.org/pub/mozilla.org/security/nss/releases/NSS_3_14_3_RTM/src/nss-3.14.3.tar.gz | tar xvz
curl -k -s -S ftp://ftp.fu-berlin.de/unix/tools/file/file-5.13.tar.gz | tar xvz
curl -k -s -S http://download.oracle.com/berkeley-db/db-4.5.20.tar.gz | tar xvz
curl -k -s -S -L https://github.com/cms-externals/rpm/archive/cms/v4.8.0.tar.gz | tar xvz
curl -k -s -S http://ftp.gnu.org/gnu/cpio/cpio-2.11.tar.bz2 | tar xvj

# Build required externals.

if [ ! $IS_ONLINE ]; then
cd $HERE/zlib-1.2.8
CFLAGS="-fPIC -O3 -DUSE_MMAP -DUNALIGNED_OK -D_LARGEFILE64_SOURCE=1" \
  ./configure --prefix $PREFIX --static
make -j $BUILDPROCESSES && make install
fi

cd $HERE/file-5.13
./configure --host="${CONFIG_HOST}" --build="${CONFIG_BUILD}" --disable-rpath --enable-static \
            --disable-shared --prefix $PREFIX CFLAGS=-fPIC LDFLAGS=$LDFLAGS
make -j $BUILDPROCESSES && make install

cd $HERE/nspr-4.9.5/mozilla/nsprpub
./configure --host="${CONFIG_HOST}" --build="${CONFIG_BUILD}" --disable-rpath \
            --prefix $PREFIX $NSPR_CONFIGURE_OPTS
make -j $BUILDPROCESSES && make install

cd $HERE/nss-3.14.3
curl -s -S "https://raw.github.com/cms-sw/cmsdist/IB/CMSSW_7_1_X/stable/nss-3.14.3-add-ZLIB-LIBS-DIR-and-ZLIB-INCLUDE-DIR.patch" | patch -p1
export USE_64=$NSS_USE_64
export NSPR_INCLUDE_DIR=$PREFIX/include/nspr
export NSPR_LIB_DIR=$PREFIX/lib
export FREEBL_LOWHASH=1
export USE_SYSTEM_ZLIB=1
if [ ! $IS_ONLINE ]; then
  export ZLIB_INCLUDE_DIR="$PREFIX/include"
  export ZLIB_LIBS_DIR="-L$PREFIX/lib"
fi
 
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

cd $HERE/popt-1.16
./configure --host="${CONFIG_HOST}" --build="${CONFIG_BUILD}" --disable-shared --enable-static \
            --disable-nls --prefix $PREFIX CFLAGS=-fPIC LDFLAGS=$LDFLAGS
make -j $BUILDPROCESSES && make install

cd $HERE/db-4.5.20/build_unix
../dist/configure --host="${CONFIG_HOST}" --build="${CONFIG_BUILD}" --enable-static \
                  --disable-shared --disable-java --disable-rpc --prefix=$PREFIX \
                  --with-posixmutexes CFLAGS=-fPIC LDFLAGS=$LDFLAGS
make -j $BUILDPROCESSES && make install

# Build the actual rpm distribution.
cd $HERE/rpm-cms-v4.8.0
case `uname` in
  Darwin)
    export DYLD_FALLBACK_LIBRARY_PATH=$PREFIX/lib
    USER_LIBS=-liconv
    LIBPATHNAME=DYLD_FALLBACK_LIBRARY_PATH
    for f in $PREFIX/lib/*.dylib*;do
       install_name_tool -id $f $f
       for lib in `otool -L $f | grep executable_path | awk '{print $1}'`;do 
          libn=$PREFIX/lib/`basename $lib`; 
          install_name_tool -change $lib $libn $f; 
       done;
    done
  ;;
  Linux)
    export LD_FALLBACK_LIBRARY_PATH=$PREFIX/lib
    LIBPATHNAME=LD_FALLBACK_LIBRARY_PATH
  ;;
esac

./configure --host="${CONFIG_HOST}" --build="${CONFIG_BUILD}" --prefix $PREFIX \
            --with-external-db --disable-python --disable-nls --localstatedir=$PREFIX/var \
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

# Fix broken RPM symlinks
ln -sf $PREFIX/bin/rpm $PREFIX/bin/rpmdb
ln -sf $PREFIX/bin/rpm $PREFIX/bin/rpmsign
ln -sf $PREFIX/bin/rpm $PREFIX/bin/rpmverify
ln -sf $PREFIX/bin/rpm $PREFIX/bin/rpmquery

# Install GNU cpio
cd $HERE/cpio-2.11
curl -s -S "https://raw.github.com/cms-sw/cmsdist/IB/CMSSW_7_1_X/stable/cpio-2.11-stdio.in-gets.patch" | patch -p1

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

./configure --host="${CONFIG_HOST}" --build="${CONFIG_BUILD}" --disable-rpath \
            --disable-nls --exec-prefix=$PREFIX --prefix=$PREFIX \
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

      case $FILE in
        *.dylib)
          FIX_TYPE="Library:"
          SO_NAME=`otool -L $FILE | head -n 1 | cut -d ':' -f 1`
          install_name_tool -id $SO_NAME $FILE
        ;;
      esac

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
