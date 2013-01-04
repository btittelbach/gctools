#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) Bernhard Tittelbach <xro@gmx.net>
# License: public domain, attribution appreciated


import sys
import os
import getopt
from lxml import etree
import requests
import re
import geocachingsitelib as gc

destination_dir_=os.path.curdir
gc_username_ = None
gc_password_ = None

def usage():
    print "Sytax:"
    print "       [%s -u <user> -p <pass>] geocache_visits.txt" % (sys.argv[0])
    print "Options:"
    print "       -h           | --help             Show Help"
    print "       -u username  | --username=gc_user "
    print "       -p password  | --password=gc_pass "
    print "       -i           | --noninteractive   Never prompt for pwd, just fail"    
    print "If username and password are not provided, we interactively"
    print "ask for them the first time and store a session cookie. Unless -i is given"

try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], "u:p:hi", ["username=","password=","noninteractive"])
except getopt.GetoptError, e:
    print "ERROR: Invalid Option: " +str(e)
    usage()
    sys.exit(1)

fetch_all_pqs_ = False
list_pqs_ = False
create_pq_dir_ = False
be_interactive_ = True
for o, a in opts:
    if o in ["-h","--help"]:
        usage()
        sys.exit()
    elif o in ["-u","--username"]:
        gc_username_ = a
    elif o in ["-p","--password"]:
        gc_password_ = a
    elif o in ["-i","--noninteractive"]:
        be_interactive_ = False

gcvisitfiles = filter(os.path.exists, args)
if len(gcvisitfiles) < 1:
    print "ERROR: No fieldnote files found"
    usage()
    sys.exit(1)

try:
    if gc_username_ is None or gc_password_ is None:
        gc.autologin_interactive_save_cookie(be_interactive_)
    else:
        gc.login(gc_username_, gc_password_)
except Exception, e:
    gc.autologin_invalidate_cookie()
    print "ERROR during authentication/login"
    print e
    sys.exit(1)

for gcvisitfile in gcvisitfiles:
    try:
        with open(gcvisitfile, "rb") as fileObj:
            print "%s: %s" % (gcvisitfile, gc.upload_fieldnote(fileObj))
    except Exception, e:
        print "ERROR: upload of fieldnotefile %s failed" % (gcvisitfile)
        print e
