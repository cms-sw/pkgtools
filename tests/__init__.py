from os.path import abspath
import imp
location = abspath (__file__)
testDir = location.rsplit ("/", 1)[0]
baseDir = location.rsplit ("/", 2)[0]
cmsBuildFilename = abspath (baseDir+"/cmsBuild")
cmsBuildFile = open (cmsBuildFilename, 'r')
cmsBuild = imp.load_module ("cmsBuild", cmsBuildFile, cmsBuildFilename, ["",'r', imp.PY_SOURCE])
