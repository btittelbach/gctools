#!/usr/bin/python
# -*- coding: utf-8 -*-
# GPLv3 (c) 2011 Bernhard Tittelbach aka xro

import sys, os
import getopt
from lxml import etree
import re
from collections import namedtuple

WPTInfo = namedtuple("WPTInfo",["lat","lon","shortdesc","longdesc","type"])
empty_wptinfo_ = WPTInfo(*((None,)*5))

try:
  import wx

# Special GUI for mittene and alopexx :-)
  class ChngWPTDialog(wx.Dialog):
    def __init__(self, parent, title, wptinfo=empty_wptinfo_):
      super(ChngWPTDialog, self).__init__(parent=parent, title=title, size=(400, 650))
      sb_type = wx.StaticBox(self, label='Change Cache-Type')
      sbs_type = wx.StaticBoxSizer(sb_type, orient=wx.VERTICAL)
      self.type_cmbbox = wx.ComboBox(self, choices=[""]+cache_type_map.values(), style=wx.CB_DROPDOWN, value=wptinfo.type if wptinfo.type else u"")
      sbs_type.Add(self.type_cmbbox, 0, border=6, flag=wx.ALL|wx.ALIGN_RIGHT|wx.EXPAND)

      self.sb_coord = wx.StaticBox(self, label='Change Coordinates')
      self.sbs_coord = wx.StaticBoxSizer(self.sb_coord, orient=wx.VERTICAL)
      self.coord_txt = wx.TextCtrl(self)
      self.coord_st = wx.StaticText(self,label="No Change")
      self.sbs_coord.Add(self.coord_txt, 0, border=5, flag=wx.ALL|wx.EXPAND)
      self.sbs_coord.Add(self.coord_st, 0, border=6, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT)

      sb_shortdesc = wx.StaticBox(self, label='Short-Description (HTML)')
      sbs_shortdesc = wx.StaticBoxSizer(sb_shortdesc, orient=wx.VERTICAL)
      self.shortdesc_chkbox = wx.CheckBox(self, -1, 'Change Short-Description')
      self.shortdesc_txt = wx.TextCtrl(self, style=wx.TE_MULTILINE,value=wptinfo.shortdesc if wptinfo.shortdesc else u"")
      sbs_shortdesc.Add(self.shortdesc_chkbox, 0, border=5, flag=wx.TOP|wx.LEFT|wx.RIGHT)
      sbs_shortdesc.Add(self.shortdesc_txt, 1, border=5, flag=wx.EXPAND|wx.ALL)

      sb_desc = wx.StaticBox(self, label='Description (HTML)')
      sbs_desc = wx.StaticBoxSizer(sb_desc, orient=wx.VERTICAL)
      self.desc_chkbox = wx.CheckBox(self, -1, 'Change Description')
      self.desc_txt = wx.TextCtrl(self, style=wx.TE_MULTILINE, value=wptinfo.longdesc if wptinfo.longdesc else u"")
      sbs_desc.Add(self.desc_chkbox, 0, border=5, flag=wx.TOP|wx.LEFT|wx.RIGHT)
      sbs_desc.Add(self.desc_txt, 1, border=5, flag=wx.EXPAND|wx.ALL)

      #panel.SetSizer(sbs)

      button_sizer = wx.BoxSizer(wx.HORIZONTAL)
      okButton = wx.Button(self, id=wx.ID_OK)
      closeButton = wx.Button(self, id=wx.ID_CANCEL)
      button_sizer.Add(okButton)
      button_sizer.Add(closeButton, flag=wx.LEFT, border=5)

      frame_sizer = wx.BoxSizer(wx.VERTICAL)
      frame_sizer.Add(sbs_type, 3, flag=wx.ALL|wx.EXPAND, border=5)
      frame_sizer.Add(self.sbs_coord, 4, flag=wx.ALL|wx.EXPAND, border=5)
      frame_sizer.Add(sbs_shortdesc, 5, flag=wx.ALL|wx.EXPAND, border=5)
      frame_sizer.Add(sbs_desc, 13, flag=wx.ALL|wx.EXPAND, border=5)
      frame_sizer.Add(button_sizer, flag = wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
      self.SetSizer(frame_sizer)

      self.shortdesc_txt.Bind(wx.EVT_TEXT, self.OnChangeShortDesc)
      self.desc_txt.Bind(wx.EVT_TEXT, self.OnChangeDesc)
      self.coord_txt.Bind(wx.EVT_TEXT, self.OnChangeCoord)

    def OnChangeShortDesc(self, event):
      self.shortdesc_chkbox.SetValue(True)

    def OnChangeDesc(self, event):
      self.desc_chkbox.SetValue(True)

    def OnChangeCoord(self, event):
      (new_latitude,new_longitude) = parseCoords(self.coord_txt.GetValue().strip())
      if new_latitude == new_longitude == None:
        self.coord_st.SetLabel("No Change")
      else:
        self.coord_st.SetLabel(changedCoordsString(new_latitude, new_longitude))
      self.sbs_coord.Layout()

    def getInput(self):
      (new_latitude,new_longitude) = parseCoords(self.coord_txt.GetValue().strip())
      new_type = self.type_cmbbox.GetValue().strip() if self.type_cmbbox.GetValue().strip() != "" else None
      new_short_description = self.shortdesc_txt.GetValue() if self.shortdesc_chkbox.IsChecked() else None
      new_description = self.desc_txt.GetValue() if self.desc_chkbox.IsChecked() else None
      return WPTInfo(lat=new_latitude,lon=new_longitude,shortdesc=new_short_description,longdesc=new_description,type=new_type)

  gui_available_ = True
except ImportError:
  gui_available_ = False

def usage():
  print("Sytax:")
  print("       %s [options] <gpx-file>" % (sys.argv[0]))
  print("Options:")
  print("  -c <coords>           | --coord <coords> Change Coordinates")
  print("                          --lat <latitude> Change Latitude")
  print("                          --lon <longitud> Change Longitude")
  print("  -k <shortdesc>        | --shortdesc <tx> Change Short-Description")
  print("  -d <desc>             | --desc <desc>    Change Description")
  print("  -t [multi|tradi|myst] | --type <type>    Change Type")
  print("  -s <dir>              | --savedir <dir>  Save to directory")
  print("  -r                    | --rename         Rename to GCCODE_name.gpx")
  print("  -g                    | --gui           Display GUI (default if no option given)")
  print("  -h                    | --help          Show Help")

RE_SINGLECOORD=re.compile(r"([NEOWS+-])?\s*(?:(\d{1,3})\D+(\d{1,2}\.\d{3})|(\d{1,3}\.\d{1,7}))")
def parseSingleCoordinate(t):
  t = t.replace(",",".")
  m = RE_SINGLECOORD.search(t)
  coord=None
  if not m is None:
    if m.group(2) and m.group(3):
      coord=float(m.group(2))+(float(m.group(3))/60.0)
    else:
      coord=float(m.group(4))
    if not m.group(1) is None and m.group(1) in "SW-":
      coord *= -1
  else:
    try:
      coord=float(t)
    except:
      pass
  return coord

RE_NSWECOORDS=re.compile(r"([NS+-].+)\s+([WEO+-].+)",re.IGNORECASE)
RE_WENSCOORDS=re.compile(r"([WEO+-].+)\s+([NS+-].+)",re.IGNORECASE)
RE_DECCOORDS=re.compile(r"((?:[+-]\s*)?\d+[.,]\d+)\s+((?:[+-]\s*)?\d+[.,]\d+)",re.IGNORECASE)
def parseCoords(t):
  coords=(None,None)
  m1 = RE_NSWECOORDS.search(t)
  m2 = RE_WENSCOORDS.search(t)
  m3 = RE_DECCOORDS.search(t)
  if not m1 is None:
    coords = (parseSingleCoordinate(m1.group(1)),parseSingleCoordinate(m1.group(2)))
  elif not m2 is None:
    coords = (parseSingleCoordinate(m2.group(2)),parseSingleCoordinate(m2.group(1)))
  elif not m3 is None:
    coords = (parseSingleCoordinate(m3.group(1)),parseSingleCoordinate(m3.group(2)))
  return coords

def changedCoordsString(new_latitude, new_longitude):
  return (u"New Latitude: %.4f" % new_latitude if not new_latitude is None else u"Latitude unchanged") +"  "+ ("New Longitude: %.4f" % new_longitude if not new_longitude is None else u"Longitude unchanged")

try:
  opts, files = getopt.gnu_getopt(sys.argv[1:], "hrgc:k:d:t:s:", ["help","gui","rename","coordinates=","longitude=","latitude=","shortdescription=","description=","type=","savedir="])
except getopt.GetoptError as e:
  print "ERROR: Invalid Option: " +str(e)
  usage()
  sys.exit(1)

new_wptinfo_ = empty_wptinfo_
savedir_ = None
autorename_ = False
display_dialog_ = False

cache_type_map={"multi":"Multi-cache","tradi":"Traditional Cache","myst":"Unknown Cache","cito":"Cache In Trash Out Event","event":"Event Cache","megaevent":"Mega-Event Cache","letterbox":"Letterbox Hybrid","earth":"Earthcache"}
for o, a in opts:
  if o in "--help":
    usage()
    sys.exit()
  elif o in "--rename":
    autorename_=True
  elif o in "--gui":
    display_dialog_=True
  elif o in "--coordinates":
    (new_wptinfo_.lat,new_wptinfo_.lon) = parseCoords(a.strip())
  elif o in "--latitude":
    new_wptinfo_.lat = parseSingleCoordinate(a)
  elif o in "--longitude":
    new_wptinfo_.lon = parseSingleCoordinate(a)
  elif o in "--shortdescription":
    new_wptinfo_.shortdesc=a
  elif o in "--description":
    new_wptinfo_.longdesc=a
  elif o in "--savedir":
    if os.path.isdir(a):
      savedir_=a
    else:
      print "Not a directory:", a
  elif o in "--type":
    if a in cache_type_map:
      new_wptinfo_.type=cache_type_map[a]
    else:
      new_wptinfo_.type=a
      sys.stdout.write("Warning: Cachetype unknown, using raw string.")
    print "New Cachetype:", new_wptinfo_.type


if len(files) <1:
  usage()
  sys.exit()

if display_dialog_ or new_wptinfo_.lat == new_wptinfo_.lon == new_wptinfo_.longdesc == new_wptinfo_.type == None:
  if gui_available_:
    wxapp = wx.App()
    dial = ChngWPTDialog(None, "Change "+",".join(files))
    if dial.ShowModal() == wx.ID_OK:
      new_wptinfo_ = dial.getInput()
    dial.Destroy()
  else:
    print("wyPython not installed: GUI not available")

print changedCoordsString(new_wptinfo_.lat, new_wptinfo_.lon)

for gpxfile in files:
  tree = None
  gcname = None
  gccode = None
  with open(gpxfile, mode="rb") as f:
    parser = etree.XMLParser()
    tree = etree.parse(f,parser).getroot()

  for wpt_elem in tree:
    if wpt_elem.tag[-6:] == "bounds":
      if not new_wptinfo_.lat is None:
        wpt_elem.set("minlat",str(new_wptinfo_.lat))
        wpt_elem.set("maxlat",str(new_wptinfo_.lat))
      if not new_wptinfo_.lon is None:
        wpt_elem.set("minlon",str(new_wptinfo_.lon))
        wpt_elem.set("maxlon",str(new_wptinfo_.lon))

    if wpt_elem.tag[-3:] == "wpt":
      if not new_wptinfo_.lat is None:
        wpt_elem.set("lat",str(new_wptinfo_.lat))
        print("* updated latitude");
      if not new_wptinfo_.lon is None:
        wpt_elem.set("lon",str(new_wptinfo_.lon))
        print("* updated longitude");

      if autorename_ or not (new_wptinfo_.longdesc is None and new_wptinfo_.type is None):
        for cache_elem in wpt_elem:
          if cache_elem.tag[-7:] == "urlname":
            gcname = cache_elem.text
          elif cache_elem.tag[-4:] == "name":
            gccode = cache_elem.text
          elif not new_wptinfo_.type is None and cache_elem.tag[-4:] == "type":
            cache_elem.text = "Geocache|"+new_wptinfo_.type
            print("* updated cachetype");
          elif cache_elem.tag[-5:] == "cache":
            for desc_elem in cache_elem:
              if not new_wptinfo_.type is None and desc_elem.tag[-4:] == "type":
                desc_elem.text = new_wptinfo_.type
              elif not new_wptinfo_.shortdesc is None and desc_elem.tag[-17:] == "short_description":
                desc_elem.set("html","True")
                desc_elem.text=new_wptinfo_.shortdesc
                print("* updated description with given html text");
              elif not new_wptinfo_.longdesc is None and desc_elem.tag[-16:] == "long_description":
                desc_elem.set("html","True")
                desc_elem.text=new_wptinfo_.longdesc
                print("* updated description with given html text");
      break

  data = etree.tostring(tree,method="xml",xml_declaration=True,encoding="utf-8")

  (gpxdir, gpxfilename) = os.path.split(gpxfile)
  if autorename_ and gcname and gccode:
    gpxfilename = "%s_%s%s" % (gccode,filter(lambda x: x in u"_ -abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", gcname)[:25], os.path.splitext(gpxfilename)[1])
  if not savedir_ is None:
    gpxdir = savedir_
  dst_gpxfile = os.path.join(gpxdir,gpxfilename)
  with open(dst_gpxfile,mode="wb") as f:
    f.truncate()
    f.write(data)
  print("* successfully written %s" % dst_gpxfile)
  if dst_gpxfile != gpxfile:
    os.unlink(gpxfile)

