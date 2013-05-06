from tests import cmsBuild
from cmsBuild import PackageFactory, TagCacheAptImpl
from os import makedirs, rmdir
from os.path import exists, basename
from cmsBuild import logLevel
from cmsBuild import FileNotFound

cmsBuild.logLevel = 3

if exists ("tmptest"):
    rmdir ("tmptest")
makedirs ("tmptest")

class Options (object):
    def __init__ (self):
        self.architecture = "sltest_ia32_gcc345"
        self.workDir = "tmptest"
        self.cmsdist = "CMSDISTXXX"
        self.compilerVersion = "3.4.5"
        self.compilerName = "gcc"
        self.systemCompiler = True
        self.buildCommandPrefix = ""
        self.use32BitOn64 = False
        self.unsafeMode = False
        self.doNotBootstrap = True
        self.bootstrap = False
        self.tag = "test"
        self.testTag = True

class FakeCMSOSDumper (object):
    def __init__ (self, opts):
        pass
        
    def dump (self, args):
        pass

class TestPackageFactory (PackageFactory):
    def __init__ (self, options):
        def dummyPreamble (*anything):
            return """%define cmsplatf sltest_ia32_gcc345
"""
        PackageFactory._PackageFactory__getPreamble = dummyPreamble
        PackageFactory.__init__ (self, options, FakeCMSOSDumper)

cmsBuild.tags_cache = TagCacheAptImpl (Options ())

factory = TestPackageFactory (Options ())
pkg1 = factory.create ()
spec = ["""### RPM test test 1.0
Source: foo
Source1: bar
Patch0: http://www.google.com
Patch1: http://www.google.com
"""]
pkg2 = factory.create ()
pkg2.initWithSpec (spec)
print [basename (source) for source in pkg2.sources]
assert ([basename (source) for source in pkg2.sources] == ["foo.file", "bar.file"])
assert (pkg2.patches == ["http://www.google.com", "http://www.google.com"])
assert (pkg2.requires == [])
assert (pkg2.cmsplatf == "sltest_ia32_gcc345")
assert (pkg2.pkgName () == "test+test+1.0-test")
assert (pkg2.sectionPostambles["%install"] == cmsBuild.DEFAULT_INSTALL_POSTAMBLE + "\n".join ([pkg2._Package__createProfileDScript, 
                                                                                               pkg2.initSh, 
                                                                                               pkg2.initCsh]))
assert (pkg2.sectionPreambles["%post"] == cmsBuild.DEFAULT_POST_PREAMBLE)
try:
    pkg2.sectionPreambles["%post"] = "Foo"
    assert (False)
except cmsBuild.ReadOnlyDict.PermissionError, e:
    pass
assert (pkg2.compiler.name == "system-compiler")
rmdir ("tmptest")

spec = """### RPM test test 1.0
## IMPORT foo
## IMPORT bar"""
pkg3 = factory.create ()
try:
    pkg3.initWithSpec (spec.split ("\n"))
    assert (False)
except FileNotFound, e:
    assert (True)