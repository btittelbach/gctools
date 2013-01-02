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

destination_dir_=os.path.curdir
gc_username_ = None
gc_password_ = None
gc_auth_uri_="https://www.geocaching.com/login/default.aspx"
gc_upload_uri_="http://www.geocaching.com/my/uploadfieldnotes.aspx"

def usage():
  print "Sytax:"
  print "       %s -u <user> -p <pass> geocache_visits.txt" % (sys.argv[0])
  print "Options:"
  print "       -h           | --help             Show Help"
  print "       -u username  | --username=gc_user "
  print "       -p password  | --password=gc_pass "

try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "u:p:h", ["username","password"])
except getopt.GetoptError, e:
  print "ERROR: Invalid Option: " +str(e)
  usage()
  sys.exit(1)

fetch_all_pqs_ = False
list_pqs_ = False
create_pq_dir_ = False
for o, a in opts:
  if o in ["-h","--help"]:
    usage()
    sys.exit()
  elif o in ["-u","--username"]:
    gc_username_ = a
  elif o in ["-p","--password"]:
    gc_password_ = a

gcvisitfiles = filter(os.path.exists, args)
if len(gcvisitfiles) < 1:
  print "ERROR: fieldnote files not found" % destination_dir_
  usage()
  sys.exit(1)

if gc_username_ is None or gc_password_ is None:
  print "ERROR: username and/or password not given"
  usage()
  sys.exit(1)

user_agent_="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:10.0.2) Gecko/20100101 Firefox/10.0.2"

if  "__build__" in requests.__dict__ and requests.__build__ >= 0x000704:
    cookie_jar_ = {}
else:
    import cookielib
    cookie_jar_ =cookielib.CookieJar()

parser_ = etree.HTMLParser(encoding="utf-8")

def gc_login(usr, pwd):
  global cookie_jar_
  post_data={"__EVENTTARGET":"","__EVENTARGUMENT":"","ctl00$ContentBody$tbUsername":usr,"ctl00$ContentBody$tbPassword":pwd,"ctl00$ContentBody$btnSignIn":"Login"}
  r = requests.post(gc_auth_uri_, data=post_data, allow_redirects=False, cookies=cookie_jar_, headers={"User-Agent":user_agent_})
  if  "__build__" in requests.__dict__ and requests.__build__ >= 0x000704:
    cookie_jar_ = r.cookies
    return r.error is None and "userid" in r.cookies
  else:
    return r.error is None and re.sub(r"<[^>]*>","",r.content).find('You are logged in as %s' % (usr)) > -1

def gc_upload_fieldnote(fieldnotefileObj, ignore_previous_logs=True):
  global cookie_jar_
  #<input id="ctl00_ContentBody_chkSuppressDate" type="checkbox" checked="checked" name="ctl00$ContentBody$chkSuppressDate">
  #<input id="ctl00_ContentBody_FieldNoteLoader" type="file" name="ctl00$ContentBody$FieldNoteLoader">
  #<input id="__EVENTTARGET" type="hidden" value="" name="__EVENTTARGET">
  #<input id="__EVENTARGUMENT" type="hidden" value="" name="__EVENTARGUMENT">
  
  if not isinstance(fieldnotefileObj, file):
    try:
      fieldnotefileObj = open(fieldnotefileObj, "rb")
    except:
      return False
  
  uri = gc_upload_uri_
  post_data={
        "__EVENTTARGET":"",
        "__EVENTARGUMENT":"",
        "ctl00$ContentBody$btnUpload":"Upload Field Note"
    }
  if ignore_previous_logs:
    post_data["ctl00$ContentBody$chkSuppressDate"] = "1"
  post_files = { "ctl00$ContentBody$FieldNoteLoader" : fieldnotefileObj }
  
  r = requests.post(uri, data=post_data, files=post_files, allow_redirects=True, cookies=cookie_jar_, headers={"User-Agent":user_agent_, "Referer":uri})
  if r.error is None:
    with open("/tmp/result.html","w") as fh:
      fh.truncate()
      fh.write(r.content)
    tree = etree.fromstring(r.content, parser_)
    successdiv = tree.find(".//div[@id='ctl00_ContentBody_regSuccess']")
    if not successdiv is None:
      return successdiv.text.strip()
    else:
      raise Exception("geocaching.com did not like the provided file  %s" % fieldnotefileObj.name)
  raise Exception("Recieved HTTP Error "+str(r.status_code))

if not gc_login(gc_username_, gc_password_):
  print "ERROR: login failed, wrong username/password"
  sys.exit(1)

for gcvisitfile in gcvisitfiles:
  try:
    with open(gcvisitfile, "rb") as fileObj:
      print "%s: %s" % (gcvisitfile, gc_upload_fieldnote(fileObj))
  except Exception, e:
    print "ERROR: upload of fieldnotefile %s failed" % (gcvisitfile)
    print e
