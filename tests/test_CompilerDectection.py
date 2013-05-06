import sys, re
from os import getenv
sys.path.append (getenv ("PWD"))
from cmsBuild import detectCompilerVersion
from cmsBuild import parseRPMLine

fakespec = ["### RPM external gcc 3.4.5-CMS"]
class OptionsA (object):
    compilerName = "gcc"
    compilerVersion = ""

class OptionsB (object):
    compilerName = "gcc"
    compilerVersion = "4.0.1"

class OptionsC (object):
    compilerName = "icc"
    compilerVersion = "4.0.1"
    
group, name, version = parseRPMLine (fakespec, OptionsA ())
assert (version == "3.4.5")
group, name, version = parseRPMLine (fakespec, OptionsB ())
assert (version == "4.0.1")
group, name, version = parseRPMLine (fakespec, OptionsC ())
assert (version == "3.4.5")
assert (re.match ("[0-9][0-9][0-9]", detectCompilerVersion ("gcc")))