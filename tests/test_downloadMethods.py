from os.path import join, abspath, exists
from os import makedirs
from shutil import rmtree
import sys
import md5

# Emulate rsplit in python 2.3
def rsplit24 (string, splitter, *amounts):
    return string.rsplit (splitter, *amounts)

def rsplit23 (string, splitter, *amounts):
    if not splitter in string:
        return [string]
    splitResults = string.split (splitter)
    if amounts:
        res = splitter.join (splitResults[:-amounts[0]])
        resultList = []
        resultList.append (res)
        for t in splitResults[-amounts[0]:]:
            resultList.append (t)
        return resultList
rsplit = rsplit24

if not hasattr (str, "rsplit"):
    rsplit = rsplit23

selfDir = rsplit (abspath (__file__), "/", 1)[0]
print selfDir
sys.path.append (selfDir)

downloadDir = join (selfDir, "testtmp")
if exists (downloadDir):
    rmtree (downloadDir)
makedirs (downloadDir)

from cmsBuild import parseGitUrl, downloadGit
from cmsBuild import DownloadOptions, initDownloadHandlers

initDownloadHandlers ()
options = DownloadOptions  ()
options.workDir = abspath (downloadDir)

giturl = """gitroot://ssh://ktf@hifi-bonsai.com/Users/git/COMP/PKGTOOLS.git?export=PKGTOOLS&tag=HEAD&output=/PKGTOOLS.tgz"""
protocol, gitroot, args = parseGitUrl (giturl)
assert (protocol == "gitroot")
assert (gitroot == "ssh://ktf@hifi-bonsai.com/Users/git/COMP/PKGTOOLS.git")
assert (args["tag"] == "HEAD")
assert (args["branch"] == "master") 
assert (args["output"] == "/PKGTOOLS.tgz")
#assert (downloadGit (giturl, downloadDir, options))

from cmsBuild import parseCvsUrl, downloadCvs

cvsurl = """cvs://:pserver:anonymous@cmscvs.cern.ch:2401/cvs_server/repositories/CMSSW?passwd=AA_:yZZ3e&module=BOSS&export=BOSS&tag=-rBOSS_4_3_6&output=/BOSS.tar.gz"""
protocol, cvsroot, args = parseCvsUrl (cvsurl)
print args
assert (protocol == "cvs")
assert (cvsroot == ":pserver:anonymous@cmscvs.cern.ch:2401/cvs_server/repositories/CMSSW")
assert (args["passwd"] == "AA_:yZZ3e")
assert (args["module"] == "BOSS")
assert (args["export"] == "BOSS")
assert (args["tag"] == "BOSS_4_3_6")
assert (args["output"] == "/BOSS.tar.gz")
assert (downloadCvs (cvsurl, downloadDir, options))

m=md5.new ()
m.update (file (join (downloadDir, "BOSS.tar.gz")).read ())
from cmsBuild import downloadWget, downloadCurl

assert (not downloadWget ("""http://ftp.coin3d.org/coin/src/Coin-2.4.444.tar.gz""", downloadDir, options))
assert (not downloadWget ("""http://ftp.coin3d.org/coin/src/Coin-2.4.4.tar.gz""", downloadDir, options))
assert (downloadWget ("""http://cmsrep.cern.ch/cmssw/cms/SOURCES/external/coin/2.4.5/Coin-2.4.5.tar.gz""", downloadDir, options))

m=md5.new ()
m.update (file (join (downloadDir, "Coin-2.4.5.tar.gz")).read ())
print downloadDir
print m.hexdigest ()
assert (m.hexdigest () == "99b83c5189c3755fd5f08fcad0994a7b")
#downloadCvs ("""cvs://:pserver:anonymous@cmscvs.cern.ch:2401/cvs_server/repositories/CMSSW?passwd=AA_:yZZ3e&module=BOSS&export=BOSS&&tag=-rHEAD
#&output=/BOSS.tar.gz""", downloadDir)

assert (not downloadCurl ("""http://ftp.coin3d.org/coin/src/Coin-2.4.444.tar.gz""", downloadDir, options))
assert (not downloadCurl ("""http://ftp.coin3d.org/coin/src/Coin-2.4.4.tar.gz""", downloadDir, options))
assert (downloadCurl ("""http://cmsrep.cern.ch/cmssw/cms/SOURCES/external/coin/2.4.5/Coin-2.4.5.tar.gz""", downloadDir, options))

m=md5.new ()
m.update (file (join (downloadDir, "Coin-2.4.5.tar.gz")).read ())
assert (m.hexdigest () == "99b83c5189c3755fd5f08fcad0994a7b")

from cmsBuild import download
downloadDir = join (selfDir, "testtmp2")

if exists (downloadDir):
    rmtree (downloadDir)
makedirs (downloadDir)

class MyOptions (object):
    def __init__ (self, workDir):
        self.server = "http://cmsrep.cern.ch/cmssw"
        self.repository = "cms"
        self.workDir = workDir
        
otherOptions = MyOptions (downloadDir)
assert (not download ("""http://ftp.coin3d.org/coin/src/Coin-2.4.444.tar.gz""", downloadDir, otherOptions))
assert (not download ("""http://ftp.coin3d.org/coin/src/Coin-2.4.4.tar.gz""", downloadDir, otherOptions))
assert (download ("""http://cmsrep.cern.ch/cmssw/cms/SOURCES/external/coin/2.4.5/Coin-2.4.5.tar.gz""", downloadDir, otherOptions))

m=md5.new ()
m.update (file (join (downloadDir, "Coin-2.4.5.tar.gz")).read ())
assert (m.hexdigest () == "99b83c5189c3755fd5f08fcad0994a7b")

m=md5.new ()
murl=md5.new ()

murl.update ("""http://cmsrep.cern.ch/cmssw/cms/SOURCES/external/coin/2.4.5/Coin-2.4.5.tar.gz""")
pathname = join (downloadDir, "SOURCES/cache", murl.hexdigest (), "Coin-2.4.5.tar.gz")
m.update (file (pathname).read ())
assert (m.hexdigest () == "99b83c5189c3755fd5f08fcad0994a7b")
assert (download (cvsurl, downloadDir, otherOptions))

assert (download ("cmstc://?tag=CMSSW_1_7_0&module=CMSSW&export=src&output=/src.tar.gz", downloadDir, otherOptions))
m=md5.new ()
murl=md5.new ()
murl.update ("""cmstc://?tag=CMSSW_1_7_0&module=CMSSW&export=src&output=/src.tar.gz""")
pathname = join (downloadDir, "SOURCES/cache", murl.hexdigest (), "src.tar.gz")
print pathname
m.update (file (pathname).read ())
