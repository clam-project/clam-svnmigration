# Analysis of the svn -> git migration

## TODO

- [x] Fix: GraphicsViewNetworkCanvas, a branch without top level directories -> Moved inside Networkdeditor
- [x] Fix: Partial tags and branches: aplied only to subprojects or specific files -> Turned into full tags and branches
- [x] Fix: unlabeled branches. -> Analyzed: leftovers of deleted CVS branches, grouped as branch by CVS file branch number, joined files of different branches, non-sense -> Deleted
- [x] Remove manufactured tags to build partial -> Side effect of making them full tags/branches
- [x] Annotated: SvnRevision for reference in the log message
- [x] Empty commits (because branches and tags copies are noop in git) -> Removed Tag, added additional SvnRevision to the log
- [x] Tarball tags: -> Recovered `SVN_REVISION` from tarbals and tagged
- [x] Product aware release tags: As the tag is applied to the full repo, specify in the tag the target product.
- [x] Merge commits. -> Done
- [ ] Understand V1, INITIAL_IMPORT_RELEASE_TAG, INITIAL_IMPORT_VENDOR_TAG y GNU
- [ ] Solve dual branch commits
    - [ ] 3723 but found: branches/development-branch, branches/xerces2-porting-branch
      `Writing and Reading context have moved to their own files`
        - Weirdly tests are written on devel and production in xerces2
        - Potser el resultat es moure els tests a xerces2
    - [ ] 3733 but found: branches/development-branch, branches/xerces2-porting-branch
      `XMLStorage changes ported`
    - [ ] 3896 but found: trunk, branches/development-branch
      `Ops a mudgled merge`
    - [ ] 5393 but found: trunk, branches/development-branch
      `+ Ported to new AudioFile interface`
    - [ ] 5617 but found: trunk, branches/development-branch
      build system changes`
    - [ ] 5623 but found: trunk, branches/development-branch
      `*** empty log message ***`
    - [ ] 5633 but found: trunk, branches/development-branch
      `build system changes - macosx compatibility`
    - [ ] 5657 but found: trunk, branches/development-branch
      `*** empty log message ***`
    - [x] 13690 but found: trunk, branches/GraphicsViewNetworkCanvas


   
- [ ] Fix: tags de libsndfile no se collapsan


## Files

clam-original.svn -> The original dump
clam.svn -> Dump with GraphicsViewNetworkCanvas branch fixed
emptycommits.tsv -> in which revisions reposurgeon tags the deletion of which empty commits
fixCanvasBranch.py -> Fix for GraphicsViewNetworkCanvas branch
full_svn_log.txt -> Full svn log of the original dump
generated/  -> path to hold intermediate files
import.lift  -> reposurgeon script
import.sh -> the actual wip migration script
notes.md -> you already read it
previous -> contains previous attempts to migrate, ignore then by now
pyproject.toml  ->  python project config
repomigrate   ->  python script to analyze several aspects of the repo
svn_repo_loaded   ->  a loaded instance of the original repo
tags-and-branches.txt   ->   Analysis: for every tag or branch branching commit and where the files come from (
tags-and-branches.tsv   ->   Rename map from current tag to desired tag name
tarball-revisions.tsv ->   Analysis: Revisions extracted from tarballs
tarballs  -> The tarballs
unlabeled-history.tsv ->  Analysis: Per file operations in unlabeled branches
unlabeled-history.txt ->  Analysis: Commit summary related to unlabeled branches. Manufactured ops in positive, which files took instead which deleted.
unlabeled-ops.txt -> Analysis: A previous, less useful analysis of unlabeled branches.

## Context

Goal: migrate an existing svn repository of 15k+ revisions to git.

### Before subversion

- First the development had no version control system (zips, shared drives)
- Then (2002) the code was imported into CVS, thus the first commit is a big dump
- Then (2006) it was migrated to svn using cvs2svn
    - Aproximatelly between:
        - r9316: Last manufactured cvs2svn commit (last csv tag, not necessarily last commit)
        - r9335: First fixes related to an already done svn migration

### Top level content

- The content consists of a series of subprojects:
  CLAM, NetworkEditor, SMSTools, Voice2Midi, Annotator, ipyclam...
- The main subproject is CLAM, the shared library, which is there from the begining.
  Other subprojects (the applications) were created later, many from `CLAM/examples` others from external sources.
- At first, applications were prefixed with `CLAM_` like in `CLAM_NetworkEditor`;
  at some point that prefix was dropped, like in `NetworkEditor`.
- Branches and tags also preserve this structure but many of them filter out subprojects
- There is a branch `GraphicsViewNetworkCanvas` that has no top level project directory, its current top level content should be inside NetworkEditor/

### Tags

- Tags were created only in the cvs period, none in the svn period. Last r9316 `v0_3_2-rel`
- Because cvs tags are per file and revision, and we tagged subprojects,
  cvs2svn creates a "manufactured commit" holding the deletions of the untagged files.
- Conventions:
    - `-root`: base for a branch
    - `-rel`: release or a prerelease
    - `-merged`: mark for last time a long branch was merged
- Tag content synchrony:
    - At some point, subproject versions diverged and some tags do not refer sub-projects (`v0_3_2-rel` vs `Annotator-0_3_2`),
    - Problem: if we use the same tag for different projects in different momments what happens?
    - Observation: For every tag, all subprojects are copied at the same revision.
    - Conclusion: Either we released all projects with the same version during CVS period or cvs2svn lost information.
    - TODO: During CVS period, were all subprojects released with the same version?
- Release tags during the CVS period:
    - `CLAM-0_4_1-rel` - `CLAM-0_91_0-rel` some with `-pre-rel`, `pre1-rel`... from `trunk`
    - `CLAM-devel-0_5_0-pre3-rel` tags from the `development-branch`
    - `v0_3_2-rel` applications???

            :: tags/v0_1-rel
            >>   7013 - CLAM_Annotator <- trunk/CLAM_Annotator @ 7010
            >>   7013 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 5706
            >>   7013 - CLAM_Voice2MIDI <- branches/imosquera/CLAM_Voice2MIDI @ 5272
            :: tags/v0_2-rel
            >>   7000 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 6999
            >>   7000 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 5778
            >>   7000 - CLAM_Voice2MIDI <- trunk/CLAM_Voice2MIDI @ 6233
            :: tags/v0_2_0-rel
            >>   8292 - CLAM_Annotator <- trunk/CLAM_Annotator @ 8291
            :: tags/v0_3-rel
            >>   6964 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 6963
            :: tags/v0_3_0-rel
            >>   8317 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 8315
            :: tags/v0_3_1-rel
            >>   9020 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 9019
            :: tags/v0_3_2-rel
            >>   9316 - CLAM_Annotator <- trunk/CLAM_Annotator @ 9023
            >>   9316 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 9315
            :: tags/v0_4_0-rel
            >>   8204 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 8203
            :: tags/v0_4_1-rel
            >>   9021 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 9019

- There are no release tags during the svn period:
    - The script that generated the tarballs created an `SVN_REVISION` file in the tarball with the revision.
    - No tags were created

## unlabeled branches (ubranches)

- cvs2svn created a set of branches named `unlabeled-*`, ubranch for short
- Each one has as name a dotted odd serie of numbers, matching cvs file branches
- Usually CVS joins project branches by placing a common label to svn file branches
- Notice that every file in a labeled branch may have a diferent file branch 1.1.5 1.6.3
- Reminder: 1. is trunk, 1.1 is first version in trunk 1.1.2 is the first branch from 1.1
- Reminder: Odd branches are reserved, ie. 1.1.1 reserved for Vendor branch
- Hypothesis:
    - cvs2svn finds unlabeled branches and wrongly uses the file branch as label,
- Consequences
    - That inconsistently relates as branch, files and versions that do not necessarily relate.
    - And also splits files that might be together in a labeled branch.
    - for each of those branches cvs2svn manufactures a commit containing the source versions of every one of those files
    - for branches 1.1.2, 1.1.4... which are for files created in the branch, the branch will start empty.
    - the manufactured commit consists on copying the reference revision and remove all the files not later referend in commits 
    - TODO: How does cvs2svn determines the source revision?
- In the repo:
    - Every file created in a manufatured commit appears later in a modification commit
        - Thus, only meaningfull to get the origin commit, which is not real either
        - The origin commit is the first commit in which all the files appear on that version
        - What happens if there is not such a commit?
    - 2 ubranches created empty
         - 1.1.2 (no previous branch)
         - 1.1.4 (imported from devel after mergin visualization branch, given meaning to the 4)
    - Files in 2 ubranches:
        CLAM/src/Processing/Analysis/SMSAnalysis.cxx        (LOW: 1.6.2.3.2, HIGH: 1.6.2.4.4)
        CLAM/src/Data/BasicProcessing/Spectrum.cxx           (LOW: 1.4.2.5.2, HIGH: 1.4.2.7.4)
        CLAM/src/Defines/CLAM_Math.hxx                      (LOW: 1.3.2.4.2, HIGH: 1.3.2.7.2)
        CLAM/src/Standard/CircularBuffer.hxx                 (LOW: 1.3.2.1.2, HIGH: 1.3.2.3.4)
        CLAM/examples/AnalysisSynthesis/AnalysisSynthesisExampleBase.cxx  (LOW: 1.6.2.25.2, HIGH: 1.6.2.26.4)
    - Last commit with a low ubranch is r1292
    - First commit with a high ubranch is r1372
    - Only a commit in between r1371, only affecting two files not touched anywhere else
    - Files with single ubranch either appear in r1292 or lower or in r1371 or higher
    - Seems fair to deduce two branches
        - Early: r1028 - r1292 ("merged into devel")
        - Late: r1371 - r1589 ("imported from devel") (imports visualization branch)
    - What about the source point?
        - Higher ubranch of pure Early branch files: r925 (first modification r1028)
        - Higher ubranch of pure Later branch files: 1250 (first modification r1371)
        - There are two mixed ubranches:
            - r711 (1.4.2.1.6)
                - Early branch files: Frame.hxx
                - Late branch files: AudioCircularBuffer.hxx
            - r919 (1.3.2.1.6)
                - Early branch files: SinTracking.cxx, SynthSineSpectrum.cxx
                - Late branch files: Fundamental.hxx, SpectralPeak.hxx, OSDefines.hxx, SpectralAnalysis.hxx
            - None above picked higher ubranch
    - Oops all manufactured come from development-branche but 5 from trunk: r48 r49 r78 r1033 r1587
        - This means that there should be different branches.
    - r1033 r1587 are the empty manufactured for 1.1.4 and 1.1.2, kind of normal they start at trunk
    - r48 r49 and r78 are the first manufactured
            r48 | (no author) | Manufactured from 1.3.12
            C  CLAM/src/Data/BasicProcessing/Fundamental.cxx
            C  CLAM/src/Flow/Nodes/AudioStreamBuffer.hxx
            C  CLAM/src/Flow/Nodes/CircularStreamImpl.cxx
            r49 | (no author) | Manufactured from 1.3.8
            C  CLAM/src/Defines/CLAMGL.hxx
            C  CLAM/src/Processing/ArithOps/SpectrumAdder2.cxx
            C  CLAM/src/Standard/BPFTmplDef.hxx
            r78 | (no author) | Manufactured from 1.5.8
            C  CLAM/src/Data/BasicProcessing/Spectrum.hxx
      - Fundamental.cxx is modified at r1552
      - AudioStreamBuffer.hxx r1545
      - CircularStreamImpl.cxx r1544
        

## Branch with no top level directory

Most branches and tags have subprojects as subdirectories.
But there is a branch that does not follow that criteria.
The tool reposurgeon do not resolve it properly.

branches/GraphicsViewNetworkCanvas -> `NetworkEditor`

    :: branches/GraphicsViewNetworkCanvas
      13369 - CHANGES <- trunk/NetworkEditor/CHANGES @ 13189
      13369 - COPYING <- trunk/NetworkEditor/COPYING @ 9352
      13369 - INSTALL <- trunk/NetworkEditor/INSTALL @ 10162
      13369 - README <- trunk/NetworkEditor/README @ 11158
      13369 - SConstruct <- trunk/NetworkEditor/SConstruct @ 13359
      13369 - debian <- trunk/NetworkEditor/debian @ 13304
      13369 - example-data <- trunk/NetworkEditor/example-data @ 13290
      13369 - fileplayer <- trunk/NetworkEditor/fileplayer @ 10943
      13369 - resources <- trunk/NetworkEditor/resources @ 12796
      13369 - src <- trunk/NetworkEditor/src @ 13365
      13369 - test <- trunk/NetworkEditor/test @ 12913

svn annotated the origin, but reposurgeon does not see it.

**Solution:** After migration rewrite the git history.

    git filter-repo --path-rename :NetworkEditor/ --refs GraphicsViewNetworkCanvas


## Tags of subprojects


Prefico `CLAM_` eleminado de los proyectos en 2006-11-10
Turnaround -> Chordata

## Branches (besides trunk) with progressive addition of subprojects

Progressive addition of modules into a branch

:: branches/DT-Inheritance-branch
  724 - CLAM <- trunk/CLAM @ 95
  3242 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 3240
Warning:   Mixed creation revisions: [724, 3242]

:: branches/INITIAL_IMPORT_VENDOR_TAG
  6283 - CLAM_Annotator <- None @ None
  5254 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 5253
  5248 - CLAM_SMSTools <- None @ None
Warning:   Mixed creation revisions: [5248, 5254, 6283]

:: branches/development-branch
  99 - CLAM <- trunk/CLAM @ 96
  2489 - CLAM_NetworkEditor <- None @ None
  2485 - CLAM_SMSTools <- None @ None
Warning:   Mixed creation revisions: [99, 2485, 2489]


## revision tag correspondence


CLAM-Annotator-0.2.0	2006-05-30 11:05:32 -> 0.3.1pre mal subido como 0.2.0
CLAM-Annotator-0.3.1	2006-05-08 09:53:23 -> la buena pero faltaban los datos
CLAM-Annotator-0.3.2	2006-06-16 08:58:37 -> taggeada como 0.3.1 pero con datos

:: tags/v0_2_0-rel
>>   8292 - CLAM_Annotator <- trunk/CLAM_Annotator @ 8291

CLAM-NetworkEditor-0.3.0
CLAM-NetworkEditor-0.3.1
CLAM-NetworkEditor-0.3.2
CLAM-Voice2MIDI-0.3.0
CLAM-Voice2MIDI-0.3.1

CLAM-SMSTools-0.4.0
CLAM-SMSTools-0.4.1
:: tags/v0_3-rel
>>   6964 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 6963
:: tags/v0_4_0-rel
>>   8204 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 8203
:: tags/v0_4_1-rel
>>   9021 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 9019



=== SVN Tags (con fecha y subproyectos incluidos) ===

2005-07-20  r7000   v0_2-rel       NetworkEditor, SMSTools, Voice2MIDI
2005-07-20  r7013   v0_1-rel       Annotator, NetworkEditor, Voice2MIDI

2006-02-08  r8317   v0_3_0-rel     NetworkEditor
2006-06-15  r9020   v0_3_1-rel     NetworkEditor
2006-10-12  r9316   v0_3_2-rel     Annotator, NetworkEditor

:: tags/v0_1-rel
>>   7013 - CLAM_Annotator <- trunk/CLAM_Annotator @ 7010
>>   7013 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 5706
>>   7013 - CLAM_Voice2MIDI <- branches/imosquera/CLAM_Voice2MIDI @ 5272
:: tags/v0_2-rel
>>   7000 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 6999
>>   7000 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 5778
>>   7000 - CLAM_Voice2MIDI <- trunk/CLAM_Voice2MIDI @ 6233
:: tags/v0_3_0-rel
>>   8317 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 8315
:: tags/v0_3_1-rel
>>   9020 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 9019
:: tags/v0_3_2-rel
>>   9316 - CLAM_Annotator <- trunk/CLAM_Annotator @ 9023
>>   9316 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 9315















CLAM-NetworkEditor-0.3.0.tar.gz	170.66 Kb	2006-05-30 11:05:32
CLAM-NetworkEditor-0.3.1.tar.gz	1196.64 Kb	2006-06-15 09:47:46
CLAM-NetworkEditor-0.3.2.tar.gz	1183.20 Kb	2006-10-12 12:30:22
CLAM-SMSTools-0.4.0.tar.gz	777.72 Kb	2006-05-30 11:05:32
CLAM-SMSTools-0.4.1.tar.gz	2.02 Mb	2006-06-15 09:47:47
CLAM-Voice2MIDI-0.3.0.tar.gz	1291.56 Kb	2006-05-30 11:05:32
CLAM-Voice2MIDI-0.3.1.tar.gz	1048.22 Kb	2006-10-03 06:06:54
NetworkEditor-0.4.0.tar.gz	1293.29 Kb	2006-12-13 09:20:34
NetworkEditor-0.4.1.tar.gz	1293.67 Kb	2006-12-22 13:58:57
NetworkEditor-0.4.3.tar.gz	1364.51 Kb	2007-02-14 05:12:54
NetworkEditor-0.4.4.tar.gz	1369.96 Kb	2007-03-19 08:56:24
SMSTools-0.4.2.tar.gz	2.10 Mb	2006-12-13 09:20:51
SMSTools-0.4.3.tar.gz	2.10 Mb	2006-12-22 13:59:17
SMSTools-0.4.5.tar.gz	2.10 Mb	2007-02-14 05:13:08
SMSTools-0.4.6.tar.gz	2.02 Mb	2007-03-19 08:56:25
Voice2MIDI-0.3.1.tar.gz	1057.82 Kb	2006-12-22 13:59:01
Voice2MIDI-0.3.5.tar.gz	1061.18 Kb	2007-03-19 08:56:25



:: tags/SMSTools2-0-0-1-post-rel
>>   2964 - CLAM <- branches/development-branch/CLAM @ 2963
>>   2964 - CLAM_NetworkEditor <- branches/development-branch/CLAM_NetworkEditor @ 2739
>>   2964 - CLAM_SMSTools <- branches/development-branch/CLAM_SMSTools @ 2962
:: tags/SMSTools2-0-1-2-rel
>>   3057 - CLAM <- branches/development-branch/CLAM @ 3056
>>   3057 - CLAM_NetworkEditor <- branches/development-branch/CLAM_NetworkEditor @ 3017
>>   3057 - CLAM_SMSTools <- branches/development-branch/CLAM_SMSTools @ 3052
:: tags/v0_1-rel
>>   7013 - CLAM_Annotator <- trunk/CLAM_Annotator @ 7010
>>   7013 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 5706
>>   7013 - CLAM_Voice2MIDI <- branches/imosquera/CLAM_Voice2MIDI @ 5272
:: tags/v0_2-lastmerge
>>   8360 - CLAM_Annotator <- trunk/CLAM_Annotator @ 8305
:: tags/v0_2-lastmerge-rel
>>   8364 - CLAM_Annotator <- trunk/CLAM_Annotator @ 8305
:: tags/v0_2-maintenance-root
>>   8307 - CLAM_Annotator <- trunk/CLAM_Annotator @ 8305
>>   8307 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 8202
:: tags/v0_2-rel
>>   7000 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 6999
>>   7000 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 5778
>>   7000 - CLAM_Voice2MIDI <- trunk/CLAM_Voice2MIDI @ 6233
:: tags/v0_2_0-rel
>>   8292 - CLAM_Annotator <- trunk/CLAM_Annotator @ 8291
:: tags/v0_3-rel
>>   6964 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 6963
:: tags/v0_3_0-rel
>>   8317 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 8315
:: tags/v0_3_1-rel
>>   9020 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 9019
:: tags/v0_3_2-rel
>>   9316 - CLAM_Annotator <- trunk/CLAM_Annotator @ 9023
>>   9316 - CLAM_NetworkEditor <- trunk/CLAM_NetworkEditor @ 9315
:: tags/v0_4_0-rel
>>   8204 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 8203
:: tags/v0_4_1-rel
>>   9021 - CLAM_SMSTools <- trunk/CLAM_SMSTools @ 9019




