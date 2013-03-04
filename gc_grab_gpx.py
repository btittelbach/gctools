#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) Bernhard Tittelbach <xro@gmx.net>
# License: public domain, attribution appreciated


import sys
import os
import getopt
import re
import geocachingsitelib as gc

destination_dir_ = os.path.curdir
gc_username_ = None
gc_password_ = None

def usage():
    print "Sytax:"
    print "       %s [options] <gccode|pquid|pqname> [...]" % (sys.argv[0])
    print "Options:"
    print "       -h           | --help             Show Help"
    print "       -d dir       | --gpxdir=dir       Write gpx to this dir"
    print "       -l           | --listpq           List PocketQueries"
    print "       -a           | --allpq            Download all PocketQueries"
    print "       -c           | --createpqdir      Create dir for PQ"
    print "       -u username  | --username=gc_user "
    print "       -p password  | --password=gc_pass "
    print "       -i           | --noninteractive   Never prompt for pwd, just fail"
    print "If username and password are not provided, we interactively"
    print "ask for them the first time and store a session cookie. Unless -i is given"

try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], "u:p:hlad:ci", ["listpq","help","gpxdir=","username=","password=","allpq","createpqdir","noninteractive"])
except getopt.GetoptError, e:
    print "ERROR: Invalid Option: " +str(e)
    usage()
    sys.exit(1)

fetch_all_pqs_ = False
list_pqs_ = False
create_pq_dir_ = False
gc.be_interactive = True
for o, a in opts:
    if o in ["-h","--help"]:
        usage()
        sys.exit()
    elif o in ["-a","--allpq"]:
        fetch_all_pqs_ = True
    elif o in ["-l","--listpq"]:
        list_pqs_ = True
    elif o in ["-d","--gpxdir"]:
        destination_dir_ = a
    elif o in ["-c","--createpqdir"]:
        create_pq_dir_ = True
    elif o in ["-u","--username"]:
        gc.gc_username = a
    elif o in ["-p","--password"]:
        gc.gc_password = a
    elif o in ["-i","--noninteractive"]:
        gc.be_interactive = False

re_gccode = re.compile(r'GC[a-z0-9]{1,6}',re.IGNORECASE)
re_pquid = re.compile(r'[a-f0-9-]{36}',re.IGNORECASE)
pquids = filter(re_pquid.match, args)
gccodes = filter(re_gccode.match, args)
pqnames = set(args) - set(pquids) - set(gccodes)
destination_dir_ = os.path.expanduser(destination_dir_)

if (list_pqs_ == False and fetch_all_pqs_ == False and len(args) <1) or not os.path.isdir(destination_dir_):
    print "ERROR: No gccodes given or %s may not be a valid writeable directory" % destination_dir_
    usage()
    sys.exit(1)

pqdict = {}
pqrevdict = {}
pq_to_get_tuplelist = []

if len(pqnames) > 0 or len(pquids) > 0 or fetch_all_pqs_ or list_pqs_:
    try:
        pqdict = gc.get_pq_names()
    except gc.NotLoggedInError, e:
        print "ERROR:", e
        sys.exit(1)
    pqrevdict = dict(zip(pqdict.values(),pqdict.keys()))

for gccode in gccodes:
    try:
        fn = gc.download_gpx(gccode, destination_dir_)
        print "downloaded %s to %s" % (fn, destination_dir_)
    except gc.NotLoggedInError, e:
        print "ERROR:", e
        sys.exit(1)
    except Exception, e:
        print "ERROR: GPX download of %s to %s failed" % (gccode, destination_dir_)
        print e

if list_pqs_:
    print "Listing downloadable PQs:"
    for (pqname, pquid) in pqdict.items():
        print "  %s :  %s" % (pquid, pqname)

for pquid in pquids:
    if not pquid in pqrevdict:
        print "ERROR: a PQ with UID '%s' is not in the list of downloadable pocketquieries on geocaching.com" % pquid
        continue
    pq_to_get_tuplelist.append((pqrevdict[pquid],pquid))

for pqname in pqnames:
    if not pqname in pqdict:
        print "ERROR: a PQ named '%s' is not in the list of downloadable pocketquieries on geocaching.com" % pqname
        continue
    pq_to_get_tuplelist.append((pqname,pqdict[pqname]))

if fetch_all_pqs_:
    pq_to_get_tuplelist = pqdict.items()

for (pqname,pquid) in pq_to_get_tuplelist:
    if create_pq_dir_:
        pq_save_dir = os.path.join(destination_dir_,pqname)
    else:
        pq_save_dir = destination_dir_
    try:
        if not os.path.exists(pq_save_dir):
            os.mkdir(pq_save_dir)
        fn = gc.download_pq(pquid, pq_save_dir)
        print "downloaded %s and saved %s to %s" % (pqname, fn, pq_save_dir)
    except gc.NotLoggedInError, e:
        print "ERROR:", e
        sys.exit(1)
    except Exception, e:
        print "ERROR: download of PQ '%s' with id '%s' to %s failed" % (pqname, pquid, pq_save_dir)
        print e
