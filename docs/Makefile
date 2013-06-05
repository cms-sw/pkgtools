.PHONEY: all clean

MARKDOWN=python markdown.py
SRCDOCS=$(shell find . -name \*.txt)
SRCCSS=$(shell find css -name \*.css)
CSS=$(foreach file,$(SRCCSS),html/$(file))
DOCS=$(foreach file,$(subst .txt,.html,$(SRCDOCS)),html/$(file))
all: $(DOCS) $(CSS)
	echo $(CSS)
	echo $(DOCS)
	
clean:
	rm -rf html

html/%.css: %.css 
	mkdir -p html/css
	cp -f $< $@

html/%.html: %.txt templates/header.tmpl templates/footer.tmpl
	echo Foo $?
	mkdir -p $(dir $@)
	cat templates/header.tmpl > $@
	$(MARKDOWN) $< >> $@
	cat templates/footer.tmpl >> $@
    perl -p -i -e 's|(<a href="[^h][^t][^t][^p][^"]*)(.*)|$$1/index.html$$2|g;s|cmsbuild/|../cmsbuild/|g' $@
