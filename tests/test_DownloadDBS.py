from os.path import join, abspath, exists, dirname
from os import makedirs
from shutil import rmtree
import sys
import md5
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

cvsurl = """cvs://:pserver:anonymous@cmscvs.cern.ch:2401/cvs_server/repositories/CMSSW?passwd=AA_:yZZ3e&module=DBS/Clients/Python&export=DBS&tag=-rDBS_1_1_0&output=/dbs-client.tar.gz"""
protocol, cvsroot, args = parseCvsUrl (cvsurl)
print args
assert (protocol == "cvs")
assert (cvsroot == ":pserver:anonymous@cmscvs.cern.ch:2401/cvs_server/repositories/CMSSW")
assert (args["passwd"] == "AA_:yZZ3e")
assert (args["module"] == "DBS/Clients/Python")
assert (args["export"] == "DBS")
assert (args["tag"] == "DBS_1_1_0")
assert (args["output"] == "/dbs-client.tar.gz")
assert (downloadCvs (cvsurl, downloadDir, options))

m=md5.new ()
m.update (file (join (downloadDir, "dbs-client.tar.gz")).read ())
