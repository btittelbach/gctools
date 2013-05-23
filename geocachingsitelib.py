#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) Bernhard Tittelbach <xro@gmx.net>
# License: public domain, attribution appreciated


import sys
import os
from lxml import etree
import requests
import re
import cPickle
import exceptions
import types

#### Global Constants ####

gc_auth_uri_ = "https://www.geocaching.com/login/default.aspx"
gc_uploadfieldnotes_uri_ = "http://www.geocaching.com/my/uploadfieldnotes.aspx"
gc_wp_uri_ = "http://www.geocaching.com/seek/cache_details.aspx?wp=%s"
gc_pqlist_uri_ = "http://www.geocaching.com/pocket/default.aspx"
gc_pqdownload_host_ = "http://www.geocaching.com"
gc_pqdownload_path_ = '/pocket/downloadpq.ashx?g=%s'

default_config_dir_ = os.path.join(os.path.expanduser('~'),".local","share","gctools")
auth_cookie_default_filename_ = "gctools_cookies"


#### Exceptions ####

class HTTPError(Exception):
    pass

class GeocachingSiteError(Exception):
    pass

class NotLoggedInError(Exception):
    pass


#### Internal Helper Functions ####

def _is_new_requests_lib():
    return "__build__" in requests.__dict__ and requests.__build__ >= 0x000704

def _did_request_succeed(r):
    if "error" in r.__dict__:
        return r.error is None
    elif "status_code" in r.__dict__:
        return r.status_code in [requests.codes.ok, 302]
    else:
        assert False

def _new_cookie_jar():
    if _is_new_requests_lib():
        return {}
    else:
        import cookielib
        return cookielib.CookieJar()

parser_ = etree.HTMLParser(encoding = "utf-8")

def _ask_usr_pwd():
    print "Please provide your geocaching.com login credentials:"
    sys.stdout.write("username: ")
    usr = sys.stdin.readline().strip()
    sys.stdout.write("password: ")
    pwd = sys.stdin.readline().strip("\n")
    return (usr,pwd)

def _parse_for_hidden_inputs(uri):
    gcsession = getDefaultInteractiveGCSession()
    post_data = {}
    r = gcsession.req_get(uri)
    if _did_request_succeed(r):
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


#### Login / Requests-Lib Decorator ####

class GCSession(object):
    def __init__(self, gc_username, gc_password, cookie_session_filename, ask_pass_handler):
        self.logged_in = 0 #0: no, 1: yes but session may have time out, 2: yes
        self.ask_pass_handler = ask_pass_handler
        self.gc_username = gc_username
        self.gc_password = gc_password
        self.cookie_session_filename = cookie_session_filename
        self.user_agent_ = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:10.0.2) Gecko/20100101 Firefox/10.0.2"
        self.cookie_jar_ = _new_cookie_jar()

    def _save_cookie_login(self, cookie_fileobject):
        global cookie_jar_
        saved_data = {
            "jar":self.cookie_jar_,
            "requestsversion": requests.__build__ if  "__build__" in requests.__dict__ else None
        }
        assert(cookie_fileobject.mode == "wb")
        cPickle.dump(saved_data, cookie_fileobject, 2)

    def _load_cookie_login(self, cookie_fileobject):
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
        self.cookie_jar_ = saved_data["jar"]

    def _haveUserPass(self):
        return type(self.gc_username) in types.StringTypes and type(self.gc_password) in types.StringTypes

    def _askUserPass(self):
        if isinstance(self.ask_pass_handler, types.FunctionType):
            try:
                (self.gc_username, self.gc_password) = self.ask_pass_handler()
            except Exception, e:
                if __debug__:
                    print e
                return False
        return self._haveUserPass()

    def login(self):
        if not type(self.gc_username) in types.StringTypes or not type(self.gc_password) in types.StringTypes:
            raise Exception("Login called without known username/passwort")
        remember_me = type(self.cookie_session_filename) in types.StringTypes and _is_new_requests_lib()
        post_data = {
            "__EVENTTARGET":"",
            "__EVENTARGUMENT":"",
            "ctl00$ContentBody$tbUsername":self.gc_username,
            "ctl00$ContentBody$tbPassword":self.gc_password,
            "ctl00$ContentBody$btnSignIn":"Login"
        }
        if remember_me:
            post_data["ctl00$ContentBody$cbRememberMe"] = "1"
        r = requests.post(gc_auth_uri_, data = post_data, allow_redirects = False, cookies = self.cookie_jar_, headers = {"User-Agent":self.user_agent_})
        login_ok = False
        if _is_new_requests_lib():
            self.cookie_jar_ = r.cookies
            login_ok = _did_request_succeed(r) and "userid" in r.cookies
        else:
            login_ok = _did_request_succeed(r) and re.sub(r"<[^>]*>","",r.content).find('You are signed in as %s' % (self.gc_username)) > -1
        if not login_ok:
            return False
        if remember_me:
            self._save_cookie_login(_open_config_file(self.cookie_session_filename,"wb"))
        return login_ok

    def invalidate_cookie(self):
        self.cookie_jar_ = _new_cookie_jar()
        if  type(self.cookie_session_filename) in types.StringTypes:
            _delete_config_file(self.cookie_session_filename)

    def loadSessionCookie(self):
        if not type(self.cookie_session_filename) in types.StringTypes:
            return False
        try:
            self._load_cookie_login(_open_config_file(self.cookie_session_filename,"rb"))
            return True
        except:
            self.invalidate_cookie()
            return False

    def _check_login(self):
        if self.logged_in > 0:
            return True
        if self.loadSessionCookie():
            self.logged_in = 1
            return True
        if not self._haveUserPass():
            if not self._askUserPass():
                raise NotLoggedInError("Don't know login credentials and can't ask user interactively")
        if not self.login():
            raise NotLoggedInError("login failed, wrong username/password")
        self.logged_in = 2
        return True

    def _check_is_session_valid(self, content):
        if content.find("id=\"ctl00_ContentBody_cvLoginFailed\"") >= 0:
            self.invalidate_cookie()
            self.logged_in = 0
            return False
        return True

    def req_wrap(self, reqfun):
        attempts = 2
        while attempts > 0:
            self._check_login()
            attempts -= 1
            r = reqfun(self.cookie_jar_)
            if _did_request_succeed(r):
                if self._check_is_session_valid(r.content):
                    return r
            else:
                raise HTTPError("Recieved HTTP Error "+str(r.status_code))
        raise NotLoggedInError("Request to geocaching.com failed")

    def req_get(self, uri):
        return self.req_wrap(lambda cookies: requests.get(uri, cookies = cookies, headers = {"User-Agent":self.user_agent_, "Referer":uri}))

    def req_post(self, uri, post_data, files = None):
        return self.req_wrap(lambda cookies: requests.post(uri, data = post_data, files = files, allow_redirects = True, cookies = cookies, headers = {"User-Agent":self.user_agent_, "Referer":uri}))


_gc_session_ = False
gc_username = None
gc_password = None
be_interactive = True

def getDefaultInteractiveGCSession():
    global _gc_session_
    if not isinstance(_gc_session_, GCSession):
        _gc_session_ = GCSession( gc_username = gc_username, gc_password = gc_password, cookie_session_filename = auth_cookie_default_filename_, ask_pass_handler = _ask_usr_pwd if be_interactive else None)
    return _gc_session_


#### Library Functions ####

def download_gpx(gccode, dstdir):
    gcsession = getDefaultInteractiveGCSession()
    uri = gc_wp_uri_ % gccode.upper()
    post_data = {"ctl00$ContentBody$btnGPXDL":"GPX file"}
    post_data.update(_parse_for_hidden_inputs(uri))
    r = gcsession.req_post(uri, post_data)
    cd_header = "attachment; filename="
    if "content-disposition" in r.headers and r.headers["content-disposition"].startswith(cd_header):
        filename = r.headers["content-disposition"][len(cd_header):]
        with open(os.path.join(dstdir, filename), "wb") as fh:
            fh.write(r.content)
            return filename
    raise GeocachingSiteError("Invalid gccode or other geocaching.com error")

def get_pq_names():
    gcsession = getDefaultInteractiveGCSession()
    uri = gc_pqlist_uri_
    r = gcsession.req_get(uri)
    rv = {}
    tree = etree.fromstring(r.content, parser_)
    for a_elem in tree.findall(".//a[@href]"):
        if a_elem.get("href").startswith(gc_pqdownload_path_ % ""):
            rv[a_elem.text.strip()] = a_elem.get("href")[len(gc_pqdownload_path_ % ""):]
    return rv

def download_pq(pquid, dstdir):
    gcsession = getDefaultInteractiveGCSession()
    uri = gc_pqdownload_host_ + gc_pqdownload_path_ % pquid
    r = gcsession.req_get(uri)
    cd_header = "attachment; filename="
    if "content-disposition" in r.headers and r.headers["content-disposition"].startswith(cd_header):
        filename = r.headers["content-disposition"][len(cd_header):]
        with open(os.path.join(dstdir, filename),"wb") as fh:
            fh.write(r.content)
            return filename
    raise GeocachingSiteError("Invalid PQ uid or other geocaching.com error")

def upload_fieldnote(fieldnotefileObj, ignore_previous_logs = True):
    gcsession = getDefaultInteractiveGCSession()
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
    post_data = {
          "__EVENTTARGET":"",
          "__EVENTARGUMENT":"",
          "ctl00$ContentBody$btnUpload":"Upload Field Note"
        }
    if ignore_previous_logs:
        post_data["ctl00$ContentBody$chkSuppressDate"] = "1"
    post_files = {"ctl00$ContentBody$FieldNoteLoader" : fieldnotefileObj}
    r = gcsession.req_post(uri, post_data, files = post_files)
    tree = etree.fromstring(r.content, parser_)
    successdiv = tree.find(".//div[@id='ctl00_ContentBody_regSuccess']")
    if not successdiv is None:
        return successdiv.text.strip()
    else:
        raise GeocachingSiteError("geocaching.com did not like the provided file %s" % fieldnotefileObj.name)
