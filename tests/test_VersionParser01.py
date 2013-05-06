#!/usr/bin/env python

from cmsBuild import VersionString

assert (VersionString () < VersionString ("1"))
assert (VersionString ("3.4.5") > VersionString ("2.10.1"))
assert (VersionString ("3.4.5") > VersionString ("3.4"))
assert (VersionString ("3.4") > VersionString ("3.3a"))
assert (VersionString ("0.4.5lorg3.2") > VersionString ("0.4.5lorg3.1"))
assert (VersionString ("3.10b") > VersionString("3.10a"))
assert (VersionString ("3.10a") > VersionString("3.9b"))
assert (VersionString ("3.10-CMS") < VersionString ("3.10-CMS2"))
assert (VersionString ("3.10-CMS") < VersionString ("3.10-wt"))
assert (VersionString ("3.10-CMS3") < VersionString ("3.10-wt10"))
assert (VersionString ("3.10-CMS3") < VersionString ("3.10-wt2"))
