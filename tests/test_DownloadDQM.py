from os.path import join, abspath, exists, dirname
from os import makedirs
from shutil import rmtree
import sys
import md5
import tarfile

from cmsBuild import DownloadOptions, initDownloadHandlers
from cmsBuild import parseCvsUrl, downloadCvs

downloadDir = join (dirname (abspath (__file__)), "testtmp")
if exists (downloadDir):
    rmtree (downloadDir)
makedirs (downloadDir)

initDownloadHandlers ()
options = DownloadOptions  ()
options.workDir = abspath (downloadDir)
options.verbose = True

cvsurl = """cvs://:pserver:anonymous@cmscvs.cern.ch:2401/cvs_server/repositories/CMSSW?passwd=AA_:yZZ3e&strategy=checkout&module=CMSSW/VisMonitoring/DQMServer&nocache=true&export=VisMonitoring/DQMServer&tag=-rV04-01-01&output=/DQMServer.tar.gz"""
protocol, cvsroot, args = parseCvsUrl (cvsurl)
print args
assert (protocol == "cvs")
assert (cvsroot == ":pserver:anonymous@cmscvs.cern.ch:2401/cvs_server/repositories/CMSSW")
assert (args["passwd"] == "AA_:yZZ3e")
assert (args["module"] == "CMSSW/VisMonitoring/DQMServer")
assert (args["export"] == "VisMonitoring/DQMServer")
assert (args["tag"] == "V04-01-01")
assert (args["output"] == "/DQMServer.tar.gz")
assert (downloadCvs (cvsurl, downloadDir, options))

m=md5.new ()
m.update (file (join (downloadDir, "DQMServer.tar.gz")).read ())

tf = tarfile.open(join (downloadDir, "DQMServer.tar.gz"), "r:gz")
tf.getmember("VisMonitoring/DQMServer//")
rmtree(downloadDir)
