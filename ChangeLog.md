V00-32-XX
=========

List of changes with respect to V00-32-XX branch of pkgtools are
 
- Make use of existing installation to symlink packages instead of building
  - This feature can be enabled with `--reference path-to-existsing-installation` command-line option
  
- New usercommand protocol to get package sources e.g. `Source: usercommand://package?command=command-to-run-to-get-sources&output=/name.tar.gz`
- Allow `no-cmssdt-cache=1` paramemter in `Source:` to instruct cmsBuild to not cache the downloaded sources in `cmsrep`
- Allow to build a package using local sources.
  - `--source <package>:<SourceN>=<path-to-local-dir>` Note that the directory name should match to the directory name which package spec file is expacting. For example for building `root` package with local sources first run
  ```
  > cmsBuild -a slc7_amd64_gcc700 ---sources build root
  ...
  ...
  root:Source=root-6.12.07 git+https://....
  ```
  and then use `--source root:Source=/you/path/root-6.12.07` to provide local `root` sources.
- Added `## INCLUDE file-name` support to include the contents of `cmsdist/file-name.file` it to the spec.
- Cache `spec` results to avoid re-parsing when re-run. 
- Allow to use RPM macros in version. This allows to dynamically set the version based on your arch/os.
