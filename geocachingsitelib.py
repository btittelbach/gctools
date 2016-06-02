#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) Bernhard Tittelbach <xro@gmx.net>
# License: GPLv3, attribution is appreciated


from __future__ import print_function
import sys
import os
from lxml import etree
import requests
import re
import cPickle
import exceptions
import types
import urlparse
from collections import namedtuple


#### Global Constants ####

gc_auth_uri_ = "https://www.geocaching.com/login/default.aspx"
gc_uploadfieldnotes_uri_ = "https://www.geocaching.com/my/uploadfieldnotes.aspx"
gc_listfieldnotes_uri_ = "https://www.geocaching.com/my/fieldnotes.aspx"
gc_wp_uri_ = "https://www.geocaching.com/seek/cache_details.aspx?wp=%s"
gc_pqlist_uri_ = "https://www.geocaching.com/pocket/default.aspx"
gc_pqdownload_host_ = "https://www.geocaching.com"
gc_pqdownload_path_ = '/pocket/downloadpq.ashx?g=%s&src=web'
gc_debug = False

gcvote_getvote_uri_='http://gcvote.com/getVotes.php'

default_config_dir_ = os.path.join(os.path.expanduser('~'),".local","share","gctools")
auth_cookie_default_filename_ = "gctools_cookies"

FieldNote = namedtuple("FieldNote",["name","date","time","type","loguri","deluri"])
GarminFieldLog = namedtuple("GarminFieldLog",["gccode","date","time","type","comment"])


#### Exceptions ####

class HTTPError(Exception):
    pass

class GeocachingSiteError(Exception):
    pass

class NotLoggedInError(Exception):
    pass


#### Internal Helper Functions ####

def _debug_print(context,*args):
    if gc_debug:
        print(u"\n\n=============== %s ===============" % context,file=sys.stderr)
        print(*args,file=sys.stderr)

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

def _init_parser():
    global parser_, xml_parser_
    parser_ = etree.HTMLParser(encoding = "utf-8")
    xml_parser_ = etree.XMLParser(encoding="utf-8")

parser_ = None
_init_parser()

def _ask_usr_pwd():
    if allow_use_wx:
        try:
            import wx
            dlg = wx.TextEntryDialog(parent=None,message="Please enter your geocaching.com username")
            if dlg.ShowModal() != wx.ID_OK:
                raise NotLoggedInError("User aborted username/password dialog")
            usr = dlg.GetValue()
            dlg.Destroy()
            dlg = wx.PasswordEntryDialog(parent=None,message="Please enter your geocaching.com password")
            if dlg.ShowModal() != wx.ID_OK:
                raise NotLoggedInError("User aborted username/password dialog")
            pwd = dlg.GetValue()
            dlg.Destroy()
            return (usr,pwd)
        except Exception, e:
            print(e)
            if gc_debug:
                raise e
    print("Please provide your geocaching.com login credentials:")
    sys.stdout.write("username: ")
    usr = sys.stdin.readline().strip()
    sys.stdout.write("password: ")
    pwd = sys.stdin.readline().strip("\n")
    return (usr,pwd)

def _parse_for_hidden_inputs(uri):
    gcsession = getDefaultInteractiveGCSession()
    post_data = {}
    formaction = uri
    r = gcsession.req_get(uri)
    if _did_request_succeed(r):
        tree = etree.fromstring(r.content, parser_)
        formelem = tree.find(".//form")
        if not formelem is None:
            for input_elem in formelem.findall(".//input[@type='hidden']"):
                post_data[input_elem.get("name")] = input_elem.get("value")
            formaction=urlparse.urljoin(uri,formelem.get("action"))
    return (post_data, formaction)

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

def _seek0_files_in_dict(d):
    if isinstance(d,dict):
        for i in d.values():
            if isinstance(i,file):
                i.seek(0)
            elif isinstance(i,tuple) and isinstance(i[1],file):
                i[1].seek(0)
    return d

def _splitList(lst,n):
    i=0
    while i < len(lst):
        yield lst[i:i+n]
        i+=n

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
                _debug_print("_askUserPass",e)
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
            "ctl00_ContentBody_cbRememberMe": True,
            "ctl00$ContentBody$btnSignIn":"Login"
        }
        if remember_me:
            post_data["ctl00$ContentBody$cbRememberMe"] = "1"
        r = requests.post(gc_auth_uri_, data = post_data, allow_redirects = True, cookies = self.cookie_jar_, headers = {"User-Agent":self.user_agent_})
        _debug_print("login",r.content.decode("utf-8"))
        login_ok = False
        if _is_new_requests_lib():
            self.cookie_jar_ = r.cookies
            _debug_print("login cookies ",r.cookies)
            login_ok = _did_request_succeed(r) and "gspkauth" in r.cookies
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
        if content.find("id=\"ctl00_ContentBody_cvLoginFailed\"") >= 0 \
        or content.find('<a id="hlSignIn" accesskey="s" title="Sign In" class="SignInLink" href="/login/">Sign In') >= 0 \
        or content.find('<h2>Object moved to <a href="https://www.geocaching.com/login/?RESET=Y&amp;redir=') >= 0:
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
            _debug_print("req_wrap","uri: %s\n" % r.url,"attempts: %d\n" % attempts, r.content)
            if _did_request_succeed(r):
                if self._check_is_session_valid(r.content):
                    return r
            else:
                raise HTTPError("Recieved HTTP Error "+str(r.status_code))
        raise NotLoggedInError("Request to geocaching.com failed")

    def req_get(self, uri):
        return self.req_wrap(lambda cookies: requests.get(uri, cookies = cookies, headers = {"User-Agent":self.user_agent_, "Referer":uri}))

    def req_post(self, uri, post_data, files = None):
        return self.req_wrap(lambda cookies: requests.post(uri, data = post_data, files = _seek0_files_in_dict(files), allow_redirects = False, cookies = cookies, headers = {"User-Agent":self.user_agent_, "Referer":uri}))


_gc_session_ = False
gc_username = None
gc_password = None
be_interactive = True
allow_use_wx = False

def getDefaultInteractiveGCSession():
    global _gc_session_
    if not isinstance(_gc_session_, GCSession):
        _gc_session_ = GCSession( gc_username = gc_username, gc_password = gc_password, cookie_session_filename = auth_cookie_default_filename_, ask_pass_handler = _ask_usr_pwd if be_interactive else None)
    return _gc_session_


#### Library Functions ####

def download_gpx(gccode, dstdir):
    gcsession = getDefaultInteractiveGCSession()
    uri = gc_wp_uri_ % gccode.upper()
    post_data , formaction = _parse_for_hidden_inputs(uri)
    post_data.update({"ctl00$ContentBody$btnGPXDL":"GPX file"})
    attempts=5
    while attempts > 0:
        attempts-=1
        r = gcsession.req_post(formaction, post_data)
        cd_header = "attachment; filename="
        if "content-disposition" in r.headers and r.headers["content-disposition"].startswith(cd_header):
            filename = r.headers["content-disposition"][len(cd_header):]
            with open(os.path.join(dstdir, filename), "wb") as fh:
                fh.write(r.content)
                return filename
        elif "status_code" in r.__dict__ and r.status_code == 302 and "location" in r.headers:
            formaction=r.headers["location"]
        else:
            attempts=0
            break
    raise GeocachingSiteError("Invalid gccode or other geocaching.com error")

def get_pq_names():
    gcsession = getDefaultInteractiveGCSession()
    uri = gc_pqlist_uri_
    r = gcsession.req_get(uri)
    rv = {}
    tree = etree.fromstring(r.content, parser_)
    gc_pqdownload_path_start, gc_pqdownload_path_end = gc_pqdownload_path_.split("%s")
    for a_elem in tree.findall(".//a[@href]"):
        if a_elem.get("href").startswith(gc_pqdownload_path_start) and a_elem.get("href").endswith(gc_pqdownload_path_end):
            rv[a_elem.text.strip()] = a_elem.get("href")[len(gc_pqdownload_path_start): 0-len(gc_pqdownload_path_end)]
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
    _debug_print("upload_fieldnote",type(tree),type(successdiv))
    if not successdiv is None:
        return successdiv.text.strip()
    else:
        raise GeocachingSiteError("geocaching.com did not like the provided file %s" % fieldnotefileObj.name)

def get_fieldnotes():
    gcsession = getDefaultInteractiveGCSession()
    uri = gc_listfieldnotes_uri_
    r = gcsession.req_get(uri)
    rv = []
    tree = etree.fromstring(r.content, parser_)
    for tr_elem in tree.findall(".//table[@class='Table']/tbody/tr"):
        name = etree.tostring(tr_elem[1][1], method="text", encoding="utf-8").decode("utf-8")
        if tr_elem[1][1].find(".//span[@class='Stike']") is not None:
            name += u" (Disabled|Archived)"
        rv.append(FieldNote(name=name,
                                                date=tr_elem[2].text[:-9],
                                                time=tr_elem[2].text[-8:],
                                                type=tr_elem[3][0].get("alt"),
                                                loguri=urlparse.urljoin(uri,tr_elem[4][0].get("href")),
                                                deluri=urlparse.urljoin(uri,tr_elem[4][1].get("href"))))
    return rv

def submit_log(loguri, logtext, logdate=None, logtype=None, favorite=False, encrypt=False):
    #~ Valid Log Types:
		#~ <option value="-1">- Select Type of Log -</option>
		#~ <option value="2">Found it</option>
		#~ <option value="3">Didn&#39;t find it</option>
		#~ <option value="4">Write note</option>
		#~ <option value="7">Needs Archived</option>
		#~ <option value="45">Needs Maintenance</option>
    gcsession = getDefaultInteractiveGCSession()
    r = gcsession.req_get(loguri)
    loginfo_input_name="ctl00$ContentBody$LogBookPanel1$uxLogInfo"
    valid_logtype_ids = []
    rv = []
    post_data={}
    post_checkboxes=[]
    fieldnote_loginfo=""
    tree = etree.fromstring(r.content, parser_)
    formelem = tree.find(".//form")
    if formelem is None:
        return rv
    formaction=urlparse.urljoin(loguri,formelem.get("action"))

    for textarea_elem in formelem.findall(".//textarea"):
        if textarea_elem.get("name").endswith("LogInfo"):
            loginfo_input_name = textarea_elem.get("name")
            fieldnote_loginfo = textarea_elem.text.strip()

    if fieldnote_loginfo:
        print("Fieldnote stored logtext found:", fieldnote_loginfo)

    for select_elem in formelem.findall(".//select"):
        if not select_elem.get("name").endswith("LogType"):
            continue
        post_data[select_elem.get("name")] = "4"
        for option_elem in select_elem.findall("./option"):
            valid_logtype_ids.append(option_elem.get("value"))
            if option_elem.get("selected"):
                post_data[select_elem.get("name")] = option_elem.get("value")
    valid_logtype_ids.remove("-1")

    for input_elem in formelem.findall(".//input"):
        if input_elem.get("type") == "checkbox":
            post_checkboxes.append(input_elem.get("name"))
        else:
            post_data[input_elem.get("name")] = input_elem.get("value")
    if encrypt:
        input_name = filter(lambda s: s.endswith("Encrypt"), post_checkboxes)
        if input_name:
            post_data[input_name[0]]=1
    if favorite:
        input_name = filter(lambda s: s.endswith("AddToFavorites"), post_checkboxes)
        if input_name:
            post_data[input_name[0]]=1
    if str(logtype) in valid_logtype_ids:
        input_name = filter(lambda s: s.endswith("LogType"), post_data.keys())
        if input_name:
            post_data[input_name[0]]=str(logtype)
    if logdate is not None:
        input_name = filter(lambda s: s.endswith("DateVisited"), post_data.keys())
        if input_name:
            post_data[input_name[0]]=logdate
    post_data[loginfo_input_name]=logtext

    ### Post Log ###
    r = gcsession.req_post(formaction, post_data)
    return _did_request_succeed(r)

def get_gcvotes(gcids_list, gcv_usr=None, gcv_pwd=None, use_median=True, request_limit=10):
    global gcvote_getvote_uri_, xml_parser_
    rdict = {}
    _init_parser()
    if gcv_usr is None:
        gcv_usr=""
    if gcv_pwd is None:
        gcv_pwd=""
    if not gcids_list:
        raise Exception("got empty list")
    for gcids in _splitList(gcids_list, request_limit):
        post_data={"version":"2.4e","userName":gcv_usr, "password":gcv_pwd,"cacheIds":",".join(gcids)}
        r = requests.post(gcvote_getvote_uri_, data=post_data, allow_redirects=False)
        if _did_request_succeed(r) and r.content.find("<votes userName='%s'" % gcv_usr) >= 0:
            try:
                tree = etree.fromstring(r.content, xml_parser_)
                for vote in tree.findall(".//vote[@voteMedian]"):
                    rdict[vote.get("waypoint")] = (  vote.get("voteMedian") if use_median else vote.get("voteAvg")[0:4]   , vote.get("voteCnt"))
                    _debug_print(vote.get("cacheId"), vote.get("waypoint"), vote.get("voteMedian"), vote.get("voteAvg"), vote.get("voteCnt"), vote.get("voteUser"))
            except (etree.ParserError, etree.DocumentInvalid) as e:
                _debug_print(e)
                continue
        else:
            raise Exception("GC-Vote download error." + (" GC-Vote: "+r.content if len(r.content) < 10 else ""))
    return rdict

def read_garmin_fieldnotes_xml(filename):
    _init_parser()
    rv = []
    with open(filename,"rb") as fh:
        tree = etree.parse(fh, xml_parser_).getroot()
    for log_elem in tree:
        timedate=log_elem.find("./{http://www.garmin.com/xmlschemas/geocache_visits/v1}time").text
        rv.append(GarminFieldLog(gccode=log_elem.find("./{http://www.garmin.com/xmlschemas/geocache_visits/v1}code").text,
                                                date=timedate[0:10],
                                                time=timedate[11:19],
                                                type=log_elem.find("./{http://www.garmin.com/xmlschemas/geocache_visits/v1}result").text,
                                                comment=log_elem.find("./{http://www.garmin.com/xmlschemas/geocache_visits/v1}comment").text))
    return rv
