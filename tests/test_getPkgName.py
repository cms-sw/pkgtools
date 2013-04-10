from cmsBuild import getPkgName

assert(getPkgName("cms+cms-common+1.0-1-1.slc4_ia32_gcc345.rpm") == "cms+cms-common+1.0")
assert(getPkgName("cms+cms-common+1.0-1-2.slc4_ia32_gcc345.rpm") == "cms+cms-common+1.0")
assert(getPkgName("./cms+cms-common+1.0-1-2.slc4_ia32_gcc345.rpm") == "cms+cms-common+1.0")
assert(getPkgName("//cdascas//./cms+cms-common+1.0-1-2.slc4_ia32_gcc345.rpm") == "cms+cms-common+1.0")
assert(getPkgName("//cdascas/1-1/./cms+cms-common+1.0-1-2.slc4_ia32_gcc345.rpm") == "cms+cms-common+1.0")
