from sys import platform
# Macros for creating git repo out of sources and applying patches
PATCH_SOURCE_MACROS = """
%define package_init_source  if [ ! -d .git ] ; then git init && git add . && git commit -a -m 'init repo' && _PKGTOOLS_PKG_BASE_DIR=`/bin/pwd` && PKGTOOLS_PATCH_NUM=0 ; fi
%define package_commit_patch let PKGTOOLS_PATCH_NUM=$PKGTOOLS_PATCH_NUM+1 && git add . && [ $(git diff --name-only HEAD | wc -l) -gt 0 ] && git commit -a -m "applying patch ${PKGTOOLS_PATCH_NUM}"
%define package_final_source if [ "X${_PKGTOOLS_PKG_BASE_DIR}" != "X" ] ; then mv ${_PKGTOOLS_PKG_BASE_DIR}/.git %{_builddir}/pkgtools-pkg-src-move2git ; fi
"""
# FIXME: write a more valuable description
DEFAULT_SECTIONS = {"": """
""",
                    "%%description": """
No description
""",
                  "%prep": """
%%setup -n %n-%realversion
""",
                  "%build": """
%initenv
./configure --prefix=%i
make
""",
                "%install": """
%initenv
make install
""",
                "%pre": """
if [ X"$(id -u)" = X0 ]; then
  if [ ! -f /etc/cms-root-install-allowed ]; then
    echo "*** CMS SOFTWARE INSTALLATION ABORTED ***"
    echo "CMS software cannot be installed as the super-user."
    echo "(We recommend reading a unix security guide)."
    exit 1
  fi
fi
""",
                "%post": """
if [ "X$CMS_INSTALL_PREFIX" = "X" ] ; then CMS_INSTALL_PREFIX=$RPM_INSTALL_PREFIX; export CMS_INSTALL_PREFIX; fi
%{relocateConfig}etc/profile.d/init.sh
%{relocateConfig}etc/profile.d/init.csh
""",
                "%preun": """
""",
                "%postun": """
if [ "X$CMS_INSTALL_PREFIX" = "X" ] ; then CMS_INSTALL_PREFIX=$RPM_INSTALL_PREFIX; export CMS_INSTALL_PREFIX; fi
""",
                "%files": """
%{i}/
%dir %{instroot}/
%dir %{instroot}/%{cmsplatf}/
%dir %{instroot}/%{cmsplatf}/%{pkgcategory}/
%dir %{instroot}/%{cmsplatf}/%{pkgcategory}/%{pkgname}/
"""}

COMPILER_DETECTION = { "gcc": "gcc -v 2>&1 | grep version | sed -e \'s|.*\\([0-9][.][0-9][.][0-9]\\).*|\\1|\'",
"icc": "echo no detection callback for icc."}

# Preambles. %dynamic_path_var is defined in rpm-preamble.

INITENV_PREAMBLE = [
("CMD_SH", "if", "[ -f %i/etc/profile.d/dependencies-setup.sh ]; then . %i/etc/profile.d/dependencies-setup.sh; fi"),
("CMD_CSH", "if", "( -f %i/etc/profile.d/dependencies-setup.csh ) source %i/etc/profile.d/dependencies-setup.csh; endif"),
("SETV", "%(uppername)s_ROOT", "%i"),
("SETV", "%(uppername)s_VERSION", "%v"),
("SETV", "%(uppername)s_REVISION", "%pkgrevision"),
("SETV", "%(uppername)s_CATEGORY", "%pkgcategory"),
("+PATH", "PATH", "%i/bin"),
("+PATH", "%%{dynamic_path_var}", "%i/lib")]

DEFAULT_PREAMBLE = """
"""
if platform == 'darwin' : DEFAULT_PREAMBLE = """
AutoReqProv: no
"""

DEFAULT_DESCRIPTION_PREAMBLE = """
"""

DEFAULT_PREP_PREAMBLE = """
%initenv
[ -d %i ] && chmod -R u+w %i
rm -fr %i
"""

DEFAULT_BUILD_PREAMBLE = """
%initenv
"""

DEFAULT_INSTALL_PREABLE = """
mkdir -p %i
mkdir -p %_rpmdir
mkdir -p %_srcrpmdir
%initenv
"""

DEFAULT_PRE_PREAMBLE = """
if [ X"$(id -u)" = X0 ]; then
    echo "*** CMS SOFTWARE INSTALLATION ABORTED ***"
    echo "CMS software cannot be installed as the super-user."
    echo "(We recommend reading a unix security guide)."
    exit 1
fi
"""

DEFAULT_POST_PREAMBLE = """
if [ "X$CMS_INSTALL_PREFIX" = "X" ] ; then CMS_INSTALL_PREFIX=$RPM_INSTALL_PREFIX; export CMS_INSTALL_PREFIX; fi
%{relocateConfig}etc/profile.d/init.sh
%{relocateConfig}etc/profile.d/init.csh
"""
DEFAULT_PREUN_PREAMBLE = """
"""
DEFAULT_POSTUN_PREAMBLE = """
if [ "X$CMS_INSTALL_PREFIX" = "X" ] ; then CMS_INSTALL_PREFIX=$RPM_INSTALL_PREFIX; export CMS_INSTALL_PREFIX; fi
"""

DEFAULT_FILES_PREAMBLE = """
%%defattr(-, root, root)
"""
DEFAULT_RPATH_PREAMBLE = "\n%{?post_initenv:%post_initenv}\n%{?add_rpath:%add_rpath}\n"

COMMANDS_SH = {"SETV":      """%(var)s="%(value)s"\n""",
               "SET":       """export %(var)s="%(value)s";\n""",
               "+PATH":     """[ ! -d %(value)s ] || export %(var)s="%(value)s${%(var)s:+:$%(var)s}";\n""",
               "UNSET":     """unset %(var)s || true\n""",
               "CMD":       """%(var)s %(value)s\n""",
               "CMD_SH":    """%(var)s %(value)s\n""",
               "CMD_CSH":   "",
               "ALIAS":     """alias %(var)s="%(value)s"\n""",
               "ALIAS_CSH": "",
               "ALIAS_SH":  """alias %(var)s="%(value)s"\n"""}

COMMANDS_CSH = {"SETV":     """set %(var)s="%(value)s"\n""",
                "SET":      """setenv %(var)s "%(value)s"\n""",
                "+PATH":    """if ( -d %(value)s ) then\n"""
                            """  if ( ${?%(var)s} ) then\n"""
                            """    setenv %(var)s "%(value)s:$%(var)s"\n"""
                            """  else\n"""
                            """    setenv %(var)s "%(value)s"\n"""
                            """  endif\n"""
                            """endif\n""",
                "UNSET":    """unset %(var)s || true\n""",
                "CMD":      """%(var)s %(value)s\n""",
                "CMD_SH":   "",
                "CMD_CSH":  """%(var)s %(value)s\n""",
                "ALIAS":    """alias %(var)s "%(value)s"\n""",
                "ALIAS_SH": "",
                "ALIAS_CSH":"""alias %(var)s "%(value)s"\n"""}

SPEC_HEADER = """
%%define pkgname        %(name)s
%%define pkgversion     %(version)s
%%define pkgcategory    %(group)s
%%define cmsroot        %(workDir)s
%%define instroot       %(workDir)s/%(tempDirPrefix)s/BUILDROOT/%(checksum)s%(installDir)s
%%define realversion    %(realVersion)s
%%define gccver         %(compilerRealVersion)s
%%define compilerRealVersion %(compilerRealVersion)s
%%define pkgrevision    %(pkgRevision)s
%%define pkgreqs        %(pkgreqs)s
%%define directpkgreqs	%(directpkgreqs)s
%%define specchecksum   %(checksum)s
%%define cmscompiler	%(compilerName)s
%%define cmsbuildApiVersion 1
%%define installroot    %(installDir)s
%%define tempprefix     %(tempDirPrefix)s
Name: %(group)s+%(name)s+%(version)s
Group: %(group)s
Version: %(rpmVersion)s
Release: %(pkgRevision)s
License:  "As required by the orginal provider of the software."
Summary: %(summary)s SpecChecksum:%(checksum)s
%(requiresStatement)s
Packager: CMS <hn-cms-sw-develtools@cern.ch>
Distribution: CMS
Vendor: CMS
Provides: %(group)s+%(name)s+%(version)s
Obsoletes: %(group)s+%(name)s+%(version)s
Prefix: %(installDir)s
"""

DEFAULT_INSTALL_POSTAMBLE="""
# Avoid pkgconfig dependency.  Notice you still need to keep the rm statement
# to support architectures not being build with cmsBuild > V00-19-XX
%if "%{?keep_pkgconfig:set}" != "set"
if [ -d "%i/lib/pkgconfig" ]; then rm -rf %i/lib/pkgconfig; fi
%endif

# Do not package libtool and archive libraries, unless required.
%if "%{?keep_archives:set}" != "set"
# Don't need archive libraries.
rm -f %i/lib/*.{l,}a
%endif

# Strip executable / paths which were specified in the strip_files macro.
%if "%{?strip_files:set}" == "set"
for x in %strip_files
do
  if [ -e $x ]
  then
    find $x -type f -perm -a+x -exec %strip {} \;
  fi 
done
%endif

# remove files / directories which were specified by the drop_files macro.
%if "%{?drop_files:set}" == "set"
for x in %drop_files
do
  if [ -e $x ]; then rm -rf $x; fi
done
%endif

case %{cmsplatf} in
    osx* )
        for x in `find %{i} -type f -perm -u+x | grep -v -e "[.]pyc"`; 
        do 
            if [ "X`file --mime $x | sed -e 's| ||g' | cut -d: -f2 | cut -d\; -f1`" = Xapplication/octet-stream ]
            then
              chmod +w $x
              old_install_name=`otool -D $x | tail -1 | sed -e's|:$||'`
              new_install_name=`basename $old_install_name`
              install_name_tool -change $old_install_name $new_install_name -id $new_install_name $x
              # Make sure also dependencies do not have an hardcoded path.
              for dep in `otool -L $x | sed -e"s|[^\\t\\s ]*%{instroot}|%{instroot}|" | grep -e '^/' | sed -e's|(.*||'`
              do
                install_name_tool -change $dep `basename $dep` $x
              done
              chmod -w $x
            fi
        done
    ;;
    * )
    ;;
esac
"""

DEFAULT_PREP_POSTAMBLE="""
"""

DEFAULT_BUILD_POSTAMBLE="""

# make sure that at least an empty file list does exist
touch %_builddir/files
"""

