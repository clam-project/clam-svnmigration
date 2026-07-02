# Makefile for clam conversion using reposurgeon
#
# Steps to using this:
# 1. Make sure reposurgeon and repotool are on your $PATH.
# 2. (Skip this step if you're starting from a stream file.) For svn, set
#    REMOTE_URL to point at the remote repository you want to convert.
#    If the repository is already in a DVCS such as hg or git,
#    set REMOTE_URL to either the normal cloning URL (starting with hg://,
#    git://, etc.) or to the path of a local clone.
# 3. For cvs, set CVS_HOST to the repo hostname and CVS_MODULE to the module,
#    then uncomment the line that builds REMOTE_URL 
#    Note: for CVS hosts other than Sourceforge or Savannah you will need to 
#    include the path to the CVS modules directory after the hostname.
# 4. Set any required read options, such as --user-ignores or --nobranch,
#    by setting READ_OPTIONS.
# 5. Optionally, replace the default value of DUMPFILTER with a
#    command or pipeline that actually filters the dump rather than
#    just copying it through.  The most usual reason to do this is
#    that your Subversion repository is multiproject and you want to
#    strip out one subtree for conversion with repocutter sift and pop
#    commands.  Note that if you ever did copies across project
#    subtrees this simple stripout will not work - you are in deep
#    trouble and should find an expert to advise you
# 6. Run 'make stubmap' to create a stub author map.
# 7. Run 'make' to build a converted repository.
#
# The reason both first- and second-stage stream files are generated is that,
# especially with Subversion, making the first-stage stream file is often
# painfully slow. By splitting the process, we lower the overhead of
# experiments with the lift script.
#
# For a production-quality conversion you will need to edit the map
# file and the lift script.  During the process you can set EXTRAS to
# name extra metadata such as a comments message-box.
#
# Afterwards, you can use the headcompare and tagscompare productions
# to check your work.
#

EXTRAS = 
REMOTE_URL = https://clam-project.org/clam
#REMOTE_URL = svn://svn.debian.org/clam
#REMOTE_URL = https://clam.googlecode.com/svn/
CVS_HOST = clam.cvs.sourceforge.net
#CVS_HOST = cvs.savannah.gnu.org
CVS_MODULE = clam
#REMOTE_URL = cvs://$(CVS_HOST)/clam\#$(CVS_MODULE)
READ_OPTIONS =
DUMPFILTER = cat
#VERBOSITY = "set progress"
REPOSURGEON = reposurgeon
LOGFILE = conversion.log

# Configuration ends here

.PHONY: local-clobber remote-clobber gitk gc compare clean dist stubmap
# Tell make not to auto-remove tag directories, because it only tries rm 
# and hence fails
.PRECIOUS: clam-%-checkout clam-%-git

default: clam-git

# Build the converted repo from the second-stage fast-import stream
clam-git: clam.fi
	rm -fr clam-git; $(REPOSURGEON) $(VERBOSITY) 'read <clam.fi' 'prefer git' 'rebuild clam-git'

# Build the second-stage fast-import stream from the first-stage stream dump
clam.fi: clam.svn clam.opts clam.lift clam.map $(EXTRAS)
	$(REPOSURGEON) $(VERBOSITY) 'logfile $(LOGFILE)' 'script clam.opts' "read $(READ_OPTIONS) <clam.svn" 'authors read <clam.map' 'sourcetype svn' 'prefer git' 'script clam.lift' 'legacy write >clam.fo' 'write >clam.fi'

# Build the first-stage stream dump from the local mirror
clam.svn: clam-mirror
	(cd clam-mirror/ >/dev/null; repotool export) | $(DUMPFILTER) >clam.svn

# Build a local mirror of the remote repository
clam-mirror:
	repotool mirror $(REMOTE_URL) clam-mirror

# Make a local checkout of the source mirror for inspection
clam-checkout: clam-mirror
	cd clam-mirror >/dev/null; repotool checkout $(PWD)/clam-checkout

# Make a local checkout of the source mirror for inspection at a specific tag
clam-%-checkout: clam-mirror
	cd clam-mirror >/dev/null; repotool checkout $(PWD)/clam-$*-checkout $*

# Force rebuild of first-stage stream from the local mirror on the next make
local-clobber: clean
	rm -fr clam.fi clam-git *~ .rs* clam-conversion.tar.gz clam-*-git

# Force full rebuild from the remote repo on the next make.
remote-clobber: local-clobber
	rm -fr clam.svn clam-mirror clam-checkout clam-*-checkout

# Get the (empty) state of the author mapping from the first-stage stream
stubmap: clam.svn
	$(REPOSURGEON) $(VERBOSITY) "read $(READ_OPTIONS) <clam.svn" 'authors write >clam.map'

# Compare the histories of the unconverted and converted repositories at head
# and all tags.
EXCLUDE = -x CVS -x .svn -x .git
EXCLUDE += -x .svnignore -x .gitignore
headcompare: clam-mirror clam-git
	repotool compare $(EXCLUDE) clam-mirror clam-git
tagscompare: clam-mirror clam-git
	repotool compare-tags $(EXCLUDE) clam-mirror clam-git
branchescompare: clam-mirror clam-git
	repotool compare-branches $(EXCLUDE) clam-mirror clam-git
allcompare: clam-mirror clam-git
	repotool compare-all $(EXCLUDE) clam-mirror clam-git

# General cleanup and utility
clean:
	rm -fr *~ .rs* clam-conversion.tar.gz *.svn *.fi *.fo

# Bundle up the conversion metadata for shipping
SOURCES = Makefile clam.lift clam.map $(EXTRAS)
clam-conversion.tar.gz: $(SOURCES)
	tar --dereference --transform 's:^:clam-conversion/:' -czvf clam-conversion.tar.gz $(SOURCES)

dist: clam-conversion.tar.gz

#
# The following productions are git-specific
#

# Browse the generated git repository
gitk: clam-git
	cd clam-git; gitk --all

# Run a garbage-collect on the generated git repository.  Import doesn't.
# This repack call is the active part of gc --aggressive.  This call is
# tuned for very large repositories.
gc: clam-git
	cd clam-git; time git -c pack.threads=1 repack -AdF --window=1250 --depth=250
