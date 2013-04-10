#!/bin/python
requires = """
foo
barrr

Requires: external+gcc+3.4.5-giulio4 external+cppunit+1.10.2-giulio2 external+zlib+1.1.4-giulio2 external+expat+2.0.0-giulio2 external+bz2lib+1.0.2-giulio2 external+db4+4.4.20-giulio2 external+gdbm+1.8.3-giulio2 external+openssl+0.9.7d-giulio2 external+qt+3.3.6-giulio2 external+gsl+1.8-giulio2 external+castor+2.1.1-4-giulio2 external+mysql+5.0.18-giulio3 external+libpng+1.2.10-giulio3 external+dcap+1.2.35-giulio3 external+pcre+4.4-giulio3 external+oracle+10.2.0.2-giulio3 external+libungif+4.1.4-giulio3 external+libjpg+6b-giulio3 external+clhep+1.9.2.3-giulio3 external+boost-build+2.0-m10-giulio2 external+uuid+1.38-giulio3 external+cmake+2.4.2-giulio2 external+gccxml+0.6.0-giulio2 external+libtiff+3.8.2-giulio2 external+python+2.4.2-giulio2 external+boost+1.33.1-giulio2 lcg+root+5.14.00f-giulio2
# This little magic incantation figures out "Requires" from this
Requires: gcc
Requires: pcre
Requires: zlib
Requires: bz2lib
Requires: python
Requires: gccxml
Requires: boost
Requires: gsl
Requires: clhep
Requires: root
Requires: cppunit

Foo
bar
"""

import re
from os.path import abspath
spec = re.sub ("Requires:[^+\n]*\n", "\n", requires)
print spec
