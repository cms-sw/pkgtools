PREFIX=/usr
#FILES=$(glob ls *.pl *.sh *.xsl)

.PHONY: all install

all:
	echo Nothing to be done for all.
install:
	install -d -m 755 ${PREFIX}/bin
	install -d -m 755 ${PREFIX}/share
	install -d -m 755 ${PREFIX}/share/source
	cp -r * ${PREFIX}/share/source 
	chmod -R 755 ${PREFIX}/share/source
	for pkg in *.pl *.sh *.xsl; do [ -f "$$pkg" ] || continue; echo $${pkg}; ln -sf ../share/source/$${pkg} ${PREFIX}/bin/$${pkg} ; done
	# for pkg in . $(FILES); do [ X"$$pkg" = X. ] && continue; echo $${pkg}; ln -sf ../../share/source/$${pkg} ${PREFIX}/bin/$${pkg} ; done
