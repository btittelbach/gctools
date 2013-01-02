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
import cPickle

gc_auth_uri_="https://www.geocaching.com/login/default.aspx"
gc_upload_uri_="http://www.geocaching.com/my/fieldnotes.aspx"
gc_wp_uri_="http://www.geocaching.com/seek/cache_details.aspx?wp=%s"
gc_auth_uri_="https://www.geocaching.com/login/default.aspx"
gc_pqlist_uri_="http://www.geocaching.com/pocket/default.aspx"
gc_pqdownload_host_="http://www.geocaching.com"
gc_pqdownload_path_='/pocket/downloadpq.ashx?g=%s'

user_agent_="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:10.0.2) Gecko/20100101 Firefox/10.0.2"

def is_new_requests_lib():
    return "__build__" in requests.__dict__ and requests.__build__ >= 0x000704

if is_new_requests_lib():
    cookie_jar_ = {}
else:
    import cookielib
    cookie_jar_ =cookielib.CookieJar()

parser_ = etree.HTMLParser(encoding="utf-8")

def save_cookie_login(cookie_filepath):
    global cookie_jar_
    saved_data = {
        "jar":cookie_jar_,
        "requestsversion": requests.__build__ if  "__build__" in requests.__dict__ else None
    }
    with open(cookie_filepath, "wb") as fh:
        cPickle.dump(saved_data,fh,version=2)

def load_cookie_login(cookie_filepath):
    global cookie_jar_
    with open(cookie_filepath, "rb") as fh:
        saved_data = cPickle.load(fh,version=2)
    if not ("jar" in saved_data and "requestsversion" in saved_data):
        raise Exception("No Cookies in this pickle jar")
    if is_new_requests_lib():
        if saved_data["requestsversion"] is None or saved_data["requestsversion"] > requests.__build__:
            raise Exception("given cookie file is not compatible")
    else:
        if not saved_data["requestsversion"] is None:
            raise Exception("given cookie file is not compatible")
    cookie_jar_ = saved_data["jar"]

def parse_for_hidden_inputs(uri):
    global cookie_jar_
    post_data = {}
    r = requests.get(uri, cookies=cookie_jar_, headers={"User-Agent":user_agent_, "Referer":uri})
    if r.error is None:
        tree = etree.fromstring(r.content, parser_)
        for input_elem in tree.findall(".//input[@type='hidden']"):
            post_data[input_elem.get("name")] = input_elem.get("value")
    return post_data
    
def gc_login(usr, pwd, remember=False):
    global cookie_jar_
    post_data = {
        "__EVENTTARGET":"",
        "__EVENTARGUMENT":"",
        "ctl00$ContentBody$tbUsername":usr,
        "ctl00$ContentBody$tbPassword":pwd,
        "ctl00$ContentBody$btnSignIn":"Login"
    }
    if remember:
        post_data["ctl00$ContentBody$cbRememberMe"]="1"
    r = requests.post(gc_auth_uri_, data=post_data, allow_redirects=False, cookies=cookie_jar_, headers={"User-Agent":user_agent_})
    if is_new_requests_lib():
        cookie_jar_ = r.cookies
        return r.error is None and "userid" in r.cookies
    else:
        return r.error is None and re.sub(r"<[^>]*>","",r.content).find('You are logged in as %s' % (usr)) > -1

def gc_download_gpx(gccode, dstdir):
    global cookie_jar_
    uri = gc_wp_uri_ % gccode.upper()
    post_data={"ctl00$ContentBody$btnGPXDL":"GPX file"}
    post_data.update(parse_for_hidden_inputs(uri))
    r = requests.post(uri, data=post_data, allow_redirects=True, cookies=cookie_jar_, headers={"User-Agent":user_agent_, "Referer":uri})
    if r.error is None:
        cd_header = "attachment; filename="
        if "content-disposition" in r.headers and r.headers["content-disposition"].startswith(cd_header):
            filename=r.headers["content-disposition"][len(cd_header):]
            with open(os.path.join(dstdir,filename),"wb") as fh:
                fh.write(r.content)
                return filename
        raise Exception("Invalid gccode or other geocaching.com error")
    raise Exception("Recieved HTTP Error "+str(r.status_code))

def gc_get_pq_names():
  global cookie_jar_
  uri = gc_pqlist_uri_
  r = requests.get(uri, cookies=cookie_jar_, headers={"User-Agent":user_agent_, "Referer":uri})
  if r.error is None:
    rv = {}
    tree = etree.fromstring(r.content, parser_)
    for a_elem in tree.findall(".//a[@href]"):
      if a_elem.get("href").startswith(gc_pqdownload_path_ % ""):
        rv[a_elem.text.strip()] = a_elem.get("href")[len(gc_pqdownload_path_ % ""):]
    return rv
  raise Exception("Recieved HTTP Error "+str(r.status_code))

def gc_download_pq(pquid, dstdir):
  global cookie_jar_
  uri = gc_pqdownload_host_ + gc_pqdownload_path_ % pquid
  r = requests.get(uri, cookies=cookie_jar_)
  if r.error is None:
    cd_header = "attachment; filename="
    if "content-disposition" in r.headers and r.headers["content-disposition"].startswith(cd_header):
      filename=r.headers["content-disposition"][len(cd_header):]
      with open(os.path.join(dstdir,filename),"wb") as fh:
        fh.write(r.content)
        return filename
    raise Exception("Invalid PQ uid or other geocaching.com error")
  raise Exception("Recieved HTTP Error "+str(r.status_code))

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

