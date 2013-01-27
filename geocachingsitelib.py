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
import exceptions

#### Global Constants ####

gc_auth_uri_="https://www.geocaching.com/login/default.aspx"
gc_uploadfieldnotes_uri_="http://www.geocaching.com/my/uploadfieldnotes.aspx"
gc_wp_uri_="http://www.geocaching.com/seek/cache_details.aspx?wp=%s"
gc_pqlist_uri_="http://www.geocaching.com/pocket/default.aspx"
gc_pqdownload_host_="http://www.geocaching.com"
gc_pqdownload_path_='/pocket/downloadpq.ashx?g=%s'

user_agent_="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:10.0.2) Gecko/20100101 Firefox/10.0.2"

default_config_dir_= os.path.join(os.path.expanduser('~'),".local","share","gctools")
auth_cookie_default_filename_= "gctools_cookies"


#### Exceptions ####

class HTTPError(Exception):
    pass

class GeocachingSiteError(Exception):
    pass


#### Internal Helper Functions ####

def _is_new_requests_lib():
    return "__build__" in requests.__dict__ and requests.__build__ >= 0x000704

if _is_new_requests_lib():
    cookie_jar_ = {}
else:
    import cookielib
    cookie_jar_ =cookielib.CookieJar()

parser_ = etree.HTMLParser(encoding="utf-8")

def _ask_usr_pwd():
    print "Please provide your geocaching.com login credentials:"
    sys.stdout.write("username: ")
    usr = sys.stdin.readline().strip()
    sys.stdout.write("password: ")
    pwd = sys.stdin.readline().strip("\n")
    return (usr,pwd)

def _parse_for_hidden_inputs(uri):
    global cookie_jar_
    post_data = {}
    r = requests.get(uri, cookies=cookie_jar_, headers={"User-Agent":user_agent_, "Referer":uri})
    if r.error is None:
        tree = etree.fromstring(r.content, parser_)
        for input_elem in tree.findall(".//input[@type='hidden']"):
            post_data[input_elem.get("name")] = input_elem.get("value")
    return post_data

def _open_config_file(filename, mode):
    if not os.path.isdir(default_config_dir_):
        os.makedirs(default_config_dir_)
    filepath = os.path.join(default_config_dir_, os.path.basename(filename))
    return open(filepath, mode)

def _delete_config_file(filename):
    filepath = os.path.join(default_config_dir_, os.path.basename(filename))
    try:
        os.unlink(filepath)
    except:
        pass

def _save_cookie_login(cookie_fileobject):
    global cookie_jar_
    saved_data = {
        "jar":cookie_jar_,
        "requestsversion": requests.__build__ if  "__build__" in requests.__dict__ else None
    }
    assert(cookie_fileobject.mode == "wb")
    cPickle.dump(saved_data, cookie_fileobject, 2)

def _load_cookie_login(cookie_fileobject):
    global cookie_jar_
    assert(cookie_fileobject.mode == "rb")
    saved_data = cPickle.load(cookie_fileobject)
    if not ("jar" in saved_data and "requestsversion" in saved_data):
        raise Exception("No Cookies in this pickle jar")
    if _is_new_requests_lib():
        if saved_data["requestsversion"] is None or saved_data["requestsversion"] > requests.__build__:
            raise Exception("given cookie file is not compatible")
    else:
        if not saved_data["requestsversion"] is None:
            raise Exception("given cookie file is not compatible")
    cookie_jar_ = saved_data["jar"]


#### Library Functions ####

def login(usr, pwd, remember=False):
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
    login_ok = False
    if _is_new_requests_lib():
        cookie_jar_ = r.cookies
        login_ok = r.error is None and "userid" in r.cookies
    else:
        login_ok = r.error is None and re.sub(r"<[^>]*>","",r.content).find('You are logged in as %s' % (usr)) > -1
    if not login_ok:
        raise GeocachingSiteError("login failed, wrong username/password")

def autologin_invalidate_cookie():
    _delete_config_file(auth_cookie_default_filename_)    

def autologin_interactive_save_cookie(be_interactive = True):
    global cookie_jar_
    try:
        _load_cookie_login(_open_config_file(auth_cookie_default_filename_,"rb"))
        #TODO: check if session has timed out or cookie expired
    except:
        if be_interactive:
            (usr,pwd) = _ask_usr_pwd()
            login(usr, pwd, True)
            _save_cookie_login(_open_config_file(auth_cookie_default_filename_,"wb"))
        else:
            autologin_invalidate_cookie()
            raise Exception("Missing or invalid login-cookie-file")

def download_gpx(gccode, dstdir):
    global cookie_jar_
    uri = gc_wp_uri_ % gccode.upper()
    post_data={"ctl00$ContentBody$btnGPXDL":"GPX file"}
    post_data.update(_parse_for_hidden_inputs(uri))
    r = requests.post(uri, data=post_data, allow_redirects=True, cookies=cookie_jar_, headers={"User-Agent":user_agent_, "Referer":uri})
    if r.error is None:
        cd_header = "attachment; filename="
        if "content-disposition" in r.headers and r.headers["content-disposition"].startswith(cd_header):
            filename=r.headers["content-disposition"][len(cd_header):]
            with open(os.path.join(dstdir, filename), "wb") as fh:
                fh.write(r.content)
                return filename
        raise GeocachingSiteError("Invalid gccode or other geocaching.com error")
    raise HTTPError("Recieved HTTP Error "+str(r.status_code))

def get_pq_names():
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
    raise HTTPError("Recieved HTTP Error "+str(r.status_code))

def download_pq(pquid, dstdir):
    global cookie_jar_
    uri = gc_pqdownload_host_ + gc_pqdownload_path_ % pquid
    r = requests.get(uri, cookies=cookie_jar_)
    if r.error is None:
        cd_header = "attachment; filename="
        if "content-disposition" in r.headers and r.headers["content-disposition"].startswith(cd_header):
            filename=r.headers["content-disposition"][len(cd_header):]
            with open(os.path.join(dstdir, filename),"wb") as fh:
                fh.write(r.content)
                return filename
        raise GeocachingSiteError("Invalid PQ uid or other geocaching.com error")
    raise HTTPError("Recieved HTTP Error "+str(r.status_code))

def upload_fieldnote(fieldnotefileObj, ignore_previous_logs=True):
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
    uri = gc_uploadfieldnotes_uri_
    post_data={
          "__EVENTTARGET":"",
          "__EVENTARGUMENT":"",
          "ctl00$ContentBody$btnUpload":"Upload Field Note"
        }
    if ignore_previous_logs:
        post_data["ctl00$ContentBody$chkSuppressDate"] = "1"
    post_files = {"ctl00$ContentBody$FieldNoteLoader" : fieldnotefileObj}
    r = requests.post(uri, data=post_data, files=post_files, allow_redirects=True, cookies=cookie_jar_, headers={"User-Agent":user_agent_, "Referer":uri})
    if r.error is None:
        tree = etree.fromstring(r.content, parser_)
        successdiv = tree.find(".//div[@id='ctl00_ContentBody_regSuccess']")
        if not successdiv is None:
            return successdiv.text.strip()
        else:
            raise GeocachingSiteError("geocaching.com did not like the provided file %s" % fieldnotefileObj.name)
    raise HTTPError("Recieved HTTP Error "+str(r.status_code))
