V00-32-XX
=========

List of changes with respect to V00-32-XX branch of pkgtools are
 
- Make use of existing installation to symlink packages instead of downloading from server. This can save a lot of disk and network band width
  - This feature can be enabled with `--reference path-to-existsing-installation` command-line option
  - `--black-list package-name` can be used to make sure that `package-name` is always install from repository instead of symlink to reference.
- New usercommand protocol to get package sources e.g. `Source: usercommand://package?command=command-to-run-to-get-sources&output=/name.tar.gz`
- Allow `no-cmssdt-cache=1` paramemter in `Source:` to instruct cmsBuild to not cache the downloaded sources in `cmsrep`
  - Avoding caching large cms data packages.
- Allow to build a package using local sources.
  - `--source <package>:<SourceN>=<path>/<package-dir>`. Note that `<package-dir>` should match to the directory name which package spec file is expacting. For example for building `root` package with local sources first run
  ```
  > cmsBuild -a slc7_amd64_gcc700 ---sources build root
  ...
  ...
  root:Source=root-6.12.07 git+https://....
  ```
  and then use `--source root:Source=/you/path/root-6.12.07` to provide local `root` sources.
- Added `## INCLUDE file-name` support to include the contents of `cmsdist/file-name.file` it to the spec.
  - It expand the included file in place as compare to `## IMPORT file` which does it at the end of the generate spec.
- Cache `spec` results to avoid re-parsing when re-run. 
- Allow to use RPM macros in version. This allows to dynamically set the version based on your arch/os.
```
### RPM external zlib %{zlib_version}
%ifarch x86_64
%define zlib_version 1.2.11
%else
%define zlib_version 1.2.8
%endif
```
- Some cleanup of unused code and moved static data in to separate file.
