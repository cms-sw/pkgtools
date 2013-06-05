---
title: PKGTOOLS
layout: default
related:
 - { name: Home, link: index.html }
 - { name: Project, link: https://github.com/cms-sw/pkgtools }
 - { name: Feedback, link: https://github.com/cms-sw/pkgtools/issues/new }
---

# How cmsBuild fetches sources.

spec files should only fetch sources and scripts by specifying the appropriate 

    Source<X>: <URL>

tag at the top. 

* `<X>` can either be empty or an integer number.
* `<URL>` specifies what needs to be fetched.

Notice that downloaded sources are cached based on the hash of the url.

`<URL>` differs depending on the type of resource in particular:

## `http`, `https`, `ftp`, `ftps`

This is the standard way of getting sources from a web or FTP server. There is
no particular option that can be specified.

###  Fetching sources from cvs:

In order to fetch sources from cvs, you need to specify a few options to login
on the server select the correct module.
The full syntax is:

    Source[0-9]*: cvs://<server>?<options>

* `<server>` uses the usual way of specifying a `CVSROOT`, e.g.

    :pserver:anonymous@cmscvs.cern.ch:2401/cvs_server/repositories/CMSSW

* `<options>` can be either:

* `passwd`: cypted password to access the repository.
* `module`: the name of the cvs module to be used for checkout
* `export`: the directory where the files are checked out (the -d option passed to cvs).
* `strategy`: can be either `checkout` or `export` and tells the system what
  cvs command to use to download sources.
* `output`: the name of the tarfile where the sources have to be packed. Notice that the
  value of this option has to start with '/'.

## `git`

You can checkout from git by using one of the following syntax:

    Source<X>: git<transfer-protocol>://<server>/<path-to-repository>?obj=<branch>/<sha1>&

Where 

* `<X>` is either empty or a integer number which identifies the source.
* `<transfer-protocol>` can be empty (in which case the standard git protocol
  is used) or `+http`, `+https`, `+ssh` to specify the associated protocol.

* `<server>` is the git server which hosts the repository.
* `<branch>` is the branch from which to checkout.
* `<sha1>` is the unique id of the commit object to checkout.
