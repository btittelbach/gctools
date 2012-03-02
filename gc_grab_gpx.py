#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import getopt
from lxml import etree
import cookielib
import requests

destination_dir_=os.path.curdir
gc_username_ = None
gc_password_ = None
gc_wp_uri_="http://www.geocaching.com/seek/cache_details.aspx?wp=%s"
gc_auth_uri_="https://www.geocaching.com/login/default.aspx"
gc_pqlist_uri_="http://www.geocaching.com/pocket/default.aspx"
gc_pqdownload_host_="http://www.geocaching.com"

def usage():
  print "Sytax:"
  print "       %s [options] <gccode|pqname> [gccode|pqname [...]]" % (sys.argv[0])
  print "Options:"
  print "       -h           | --help             Show Help"
  print "       -d dir       | --gpxdir=dir       Write gpx to this dir"
  print "       -a           | --allpq            Download all PocketQueries"
  print "       -u username  | --username=gc_user "
  print "       -p password  | --password=gc_pass "

try:
  opts, gccodes = getopt.gnu_getopt(sys.argv[1:], "u:p:had:", ["help","gpxdir=","username","password","allpq"])
except getopt.GetoptError, e:
  print "ERROR: Invalid Option: " +str(e)
  usage()
  sys.exit(1)

fetch_all_pqs_ = False
for o, a in opts:
  if o in ["-h","--help"]:
    usage()
    sys.exit()
  elif o in ["-a","--allpq"]:
    fetch_all_pqs_ = True
  elif o in ["-d","--gpxdir"]:
    destination_dir_=a
  elif o in ["-u","--username"]:
    gc_username_=a
  elif o in ["-p","--password"]:
    gc_password_=a

if (fetch_all_pqs_ == False and len(gccodes) <1) or not os.path.isdir(destination_dir_):
  print "ERROR: No gccodes given or %s may not be a valid writeable directory" % destination_dir_
  usage()
  sys.exit(1)

if gc_username_ is None or gc_password_ is None:
  print "ERROR: username and/or password not given"
  usage()
  sys.exit(1)

destination_dir_=os.path.expanduser(destination_dir_)
user_agent_="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:10.0.2) Gecko/20100101 Firefox/10.0.2"
cookie_jar_=cookielib.CookieJar()
parser_ = etree.HTMLParser(encoding="utf-8")

def gc_login(usr, pwd):
  global cookie_jar_
  post_data={"__EVENTTARGET":"","__EVENTARGUMENT":"","ctl00$ContentBody$tbUsername":usr,"ctl00$ContentBody$tbPassword":pwd,"ctl00$ContentBody$btnSignIn":"Login"}
  r = requests.post(gc_auth_uri_, data=post_data, allow_redirects=False, cookies=cookie_jar_, headers={"User-Agent":user_agent_})
  return r.error is None and r.content.find('<span class="Success">You are logged in as <strong class="LoginUsername" title="%s">%s</strong></span>' % (usr,usr)) > -1

def gc_download_gpx(gccode, dstdir):
  global cookie_jar_
  uri = gc_wp_uri_ % gccode.upper()
  r = requests.post(uri, allow_redirects=True, cookies=cookie_jar_)
  post_data={"ctl00$ContentBody$btnGPXDL":"GPX file"}
  if r.error is None:
    tree = etree.fromstring(r.content, parser_)
    for input_elem in tree.findall(".//input[@type='hidden']"):
      post_data[input_elem.get("name")] = input_elem.get("value")
    r = requests.post(uri, data=post_data, allow_redirects=True, cookies=cookie_jar_, headers={"User-Agent":user_agent_, "Referer":uri})
    if r.error is None:
      cd_header = "attachment; filename="
      filename = "out.gpx"
      if "content-disposition" in r.headers and r.headers["content-disposition"].startswith(cd_header):
        filename=r.headers["content-disposition"][len(cd_header):]
      with open(os.path.join(dstdir,filename),"wb") as fh:
        fh.write(r.content)
        return filename
  raise Exception("Recieved HTTP Error "+str(r.status_code))

def gc_get_pq_names():
  global cookie_jar_
  uri = gc_pqlist_uri_
  r = requests.get(uri, cookies=cookie_jar_, headers={"User-Agent":user_agent_, "Referer":uri})
  if r.error is None:
    rv = {}
    tree = etree.fromstring(r.content, parser_)
    for a_elem in tree.findall(".//a[@href]"):
      if a_elem.get("href").startswith('/pocket/downloadpq.ashx'):
        rv[a_elem.text.strip()] = a_elem.get("href")
    return rv
  raise Exception("Recieved HTTP Error "+str(r.status_code))

def gc_download_pq(remotepath, dstdir):
  global cookie_jar_
  uri = gc_pqdownload_host_+remotepath
  r = requests.get(uri, cookies=cookie_jar_)
  if r.error is None:
    cd_header = "attachment; filename="
    filename = "pq.zip"
    if "content-disposition" in r.headers and r.headers["content-disposition"].startswith(cd_header):
      filename=r.headers["content-disposition"][len(cd_header):]
    with open(os.path.join(dstdir,filename),"wb") as fh:
      fh.write(r.content)
      return filename
  raise Exception("Recieved HTTP Error "+str(r.status_code))

pqnames = filter(lambda x: not x.upper().startswith("GC") or len(x) != 7, gccodes)
gccodes = filter(lambda x: x.upper().startswith("GC") and len(x) == 7, gccodes)

pqdict = {}
if gc_login(gc_username_, gc_password_):
  if len(pqnames) > 0 or fetch_all_pqs_:
    pqdict = gc_get_pq_names()
  for gccode in gccodes:
    try:
      fn = gc_download_gpx(gccode, destination_dir_)
      print "downloaded %s to %s" % (fn, destination_dir_)
    except Exception, e:
      print "ERROR: GPX download of %s to %s failed" % (gccode, destination_dir_)
      print e
  if fetch_all_pqs_:
    pqnames = pqdict.keys()
  for pqname in pqnames:
    if not pqname in pqdict:
      print "ERROR: PQ '%s' is not in list of downloadable pocketquieries on geocaching.com" % pqname
      continue
    try:
      fn = gc_download_pq(pqdict[pqname], destination_dir_)
      print "downloaded PQ '%s' file %s to %s" % (pqname, fn, destination_dir_)
    except Exception, e:
      print "ERROR: download of PQ '%s' to %s failed" % (pqname, destination_dir_)
      print e
else:
  print "ERROR: login failed, wrong username/password"
