from re import compile
USE_COMPILER_VERSION = [ "slc7_aarch64_gcc820", "slc7_ppc64le_gcc820" ]
NO_VERSION_SUFFIX = [
  compile("cmssw"), compile("cmssw-patch"), compile("cmssw-ib"),
  compile("fwlite"), compile("fwlite-patch"),
  compile("^data-[A-Z][A-Za-z0-9]+-[A-Za-z][A-Za-z0-9]+$")
]
NO_AUTO_RUNPATH = []
