#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) Bernhard Tittelbach <xro@gmx.net>
# License: GPLv3, attribution is appreciated

import sys
import getopt
import geocachingsitelib as gc
from collections import namedtuple

DialogInfo = namedtuple("DialogInfo",["selection","favorite","encrypt","substvars","text"])

try:
  import wx

  def tupleSizeRestrict(a,maxsize,margin=0):
    return (min(a[0],maxsize[0]-margin), min(a[1],maxsize[1]-margin))

# Special GUI for mittene and alopexx :-)
  class WriteFieldnoteLogsDialog(wx.Dialog):
    def __init__(self, parent, title, fieldnotes=[]):
      super(WriteFieldnoteLogsDialog, self).__init__(parent=parent, title=title, size=tupleSizeRestrict((950, 550),wx.DisplaySize(),30))

      sb_fieldnotes = wx.StaticBox(self, label='Select fieldnotes to bulk-log')
      sbs_fieldnotes = wx.StaticBoxSizer(sb_fieldnotes, orient=wx.VERTICAL)
      self.fnnames_listbox = wx.ListBox(self, choices=map(lambda e: "%s (%s,%s %s)" % (e.name,e.type,e.date,e.time), fieldnotes), style=wx.LB_EXTENDED)
      sbs_fieldnotes.Add(self.fnnames_listbox, 1, border=5, flag=wx.EXPAND|wx.ALL)

      sb_loginfo = wx.StaticBox(self, label='Logtext for selected fieldnotes')
      sbs_loginfo = wx.StaticBoxSizer(sb_loginfo, orient=wx.VERTICAL)
      self.encrypt_chkbox = wx.CheckBox(self, -1, 'Encrypt Logs')
      self.favorite_chkbox = wx.CheckBox(self, -1, 'Add Selected to Favorites')
      self.substvars_chkbox = wx.CheckBox(self, -1, 'Substitute time for %T and date for %D')
      self.loginfo_txt = wx.TextCtrl(self, style=wx.TE_MULTILINE, value="")
      sbs_loginfo.Add(self.encrypt_chkbox, 0, border=5, flag=wx.TOP|wx.LEFT|wx.RIGHT)
      sbs_loginfo.Add(self.favorite_chkbox, 0, border=5, flag=wx.TOP|wx.LEFT|wx.RIGHT)
      sbs_loginfo.Add(self.substvars_chkbox, 0, border=5, flag=wx.TOP|wx.LEFT|wx.RIGHT)
      sbs_loginfo.Add(self.loginfo_txt, 1, border=5, flag=wx.EXPAND|wx.ALL)

      button_sizer = wx.BoxSizer(wx.HORIZONTAL)
      okButton = wx.Button(self, id=wx.ID_OK)
      closeButton = wx.Button(self, id=wx.ID_CANCEL)
      button_sizer.Add(okButton)
      button_sizer.Add(closeButton, flag=wx.LEFT, border=5)

      frame_sizer = wx.BoxSizer(wx.VERTICAL)
      frame_sizer1 = wx.BoxSizer(wx.HORIZONTAL)
      frame_sizer1.Add(sbs_fieldnotes, 2, flag=wx.ALL|wx.EXPAND, border=5)
      frame_sizer1.Add(sbs_loginfo, 2, flag=wx.ALL|wx.EXPAND, border=5)
      frame_sizer.Add(frame_sizer1, 1,flag = wx.ALL|wx.EXPAND, border=5)
      frame_sizer.Add(button_sizer, 0, flag = wx.ALIGN_CENTER|wx.BOTTOM, border=10)
      self.SetSizer(frame_sizer)

    def getInput(self):
      return DialogInfo(selection=self.fnnames_listbox.GetSelections(),
                                        favorite=self.favorite_chkbox.IsChecked(),
                                        encrypt=self.encrypt_chkbox.IsChecked(),
                                        substvars=self.substvars_chkbox.IsChecked(),
                                        text=self.loginfo_txt.GetValue())

  wxapp = wx.App()
  gui_available_ = True
except ImportError:
  gui_available_ = False


def usage():
    print "Sytax:"
    print "       %s [-u <user> -p <pass>]" % (sys.argv[0])
    print "Options:"
    print "       -h           | --help             Show Help"
    print "       -u username  | --username=gc_user "
    print "       -p password  | --password=gc_pass "
    print "       -i           | --noninteractive   Never prompt for pwd, just fail"
    print "If username and password are not provided, we interactively"
    print "ask for them the first time and store a session cookie. Unless -i is given"

try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], "u:p:hi", ["help","username=","password=","noninteractive","debug"])
except getopt.GetoptError, e:
    print "ERROR: Invalid Option: " +str(e)
    usage()
    sys.exit(1)

gc.be_interactive = True
gc.allow_use_wx = True
for o, a in opts:
    if o in ["-h","--help"]:
        usage()
        sys.exit()
    elif o in ["-u","--username"]:
        gc.gc_username = a
    elif o in ["-p","--password"]:
        gc.gc_password = a
    elif o in ["-i","--noninteractive"]:
        gc.be_interactive = False
    elif o in ["--debug"]:
        gc.gc_debug = True

if not gui_available_:
    print("wyPython not installed: GUI not available, exiting...")
    sys.exit(1)

dialog_title=u"Bulk-Log Fieldnotes"

fieldnotes = gc.get_fieldnotes()

if len(fieldnotes) == 0:
    print "No pending fieldnotes, nothing to do"
    msgdlg = wx.MessageDialog(None, "No pending fieldnotes!\nnothing to do", dialog_title, wx.ICON_INFORMATION)
    msgdlg.ShowModal()
    msgdlg.Destroy()
    sys.exit(0)

dial = WriteFieldnoteLogsDialog(None, dialog_title, fieldnotes)
if dial.ShowModal() != wx.ID_OK:
    print "Abort selected"
    dial.Destroy()
    sys.exit(1)

dialinfo =  dial.getInput()
dial.Destroy()

progressdial = wx.ProgressDialog(title=dialog_title, message="Logging selected fieldnotes", parent=None, maximum=len(dialinfo.selection), style = wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT)
progress=0
for fnindex in dialinfo.selection:
    fn = fieldnotes[fnindex]
    progress +=1
    if not progressdial.Update(progress, "Logging %s" % fn.name):
        break
    logtxt = dialinfo.text
    if dialinfo.substvars:
        logtxt = logtxt.replace("%T",fn.time).replace("%D",fn.date)
    if not gc.submit_log(fn.loguri, logtxt, favorite=dialinfo.favorite, encrypt=dialinfo.encrypt):
        print "ERROR logging fieldnote for", fn.name
progressdial.Destroy()