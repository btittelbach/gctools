#!/usr/bin/python
# -*- coding: utf-8 -*-

# GPLv3 (c) 2011 Bernhard Tittelbach aka xro

import sys, os
import getopt
from lxml import etree
import re
try:
  import wx

# Special GUI for mittene and alopexx :-)
  class ChngWPTDialog(wx.Dialog):
    def __init__(self, parent, title):
      super(ChngWPTDialog, self).__init__(parent=parent, title=title, size=(400, 550))
      sb_type = wx.StaticBox(self, label='Change Cache-Type')
      sbs_type = wx.StaticBoxSizer(sb_type, orient=wx.VERTICAL)
      self.type_cmbbox = wx.ComboBox(self, choices=[""]+cache_type_map.values(), style=wx.CB_DROPDOWN)
      sbs_type.Add(self.type_cmbbox, 0, border=6, flag=wx.ALL|wx.ALIGN_RIGHT|wx.EXPAND)

      self.sb_coord = wx.StaticBox(self, label='Change Coordinates')
      self.sbs_coord = wx.StaticBoxSizer(self.sb_coord, orient=wx.VERTICAL)
      self.coord_txt = wx.TextCtrl(self)
      self.coord_st = wx.StaticText(self,label="No Change")
      self.sbs_coord.Add(self.coord_txt, 0, border=5, flag=wx.ALL|wx.EXPAND)
      self.sbs_coord.Add(self.coord_st, 0, border=6, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT)

      sb_desc = wx.StaticBox(self, label='Description (HTML)')
      sbs_desc = wx.StaticBoxSizer(sb_desc, orient=wx.VERTICAL)
      self.desc_chkbox = wx.CheckBox(self, -1, 'Change Description')
      self.desc_txt = wx.TextCtrl(self, style=wx.TE_MULTILINE)
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
      frame_sizer.Add(sbs_desc, 13, flag=wx.ALL|wx.EXPAND, border=5)
      frame_sizer.Add(button_sizer, flag = wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
      self.SetSizer(frame_sizer)

      self.desc_txt.Bind(wx.EVT_TEXT, self.OnChangeDesc)
      self.coord_txt.Bind(wx.EVT_TEXT, self.OnChangeCoord)

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
      new_description = self.desc_txt.GetValue() if self.desc_chkbox.IsChecked() else None
      return (new_latitude,new_longitude,new_description,new_type)

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
  print("  -d <desc>             | --desc <desc>    Change Coordinates")
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
  opts, files = getopt.gnu_getopt(sys.argv[1:], "hrgc:d:t:s:", ["help","gui","rename","coordinates=","longitude=","latitude=","description=","type=","savedir="])
except getopt.GetoptError as e:
  print "ERROR: Invalid Option: " +str(e)
  usage()
  sys.exit(1)

new_latitude_ = None
new_longitude_ = None
new_description_ = None
new_type_ = None
savedir_ = None
autorename_ = False
display_dialog_ = False

cache_type_map={"multi":"Multi-cache","tradi":"Traditional Cache","myst":"Unknown Cache"}
for o, a in opts:
  if o in "--help":
    usage()
    sys.exit()
  elif o in "--rename":
    autorename_=True
  elif o in "--gui":
    display_dialog_=True
  elif o in "--coordinates":
    (new_latitude_,new_longitude_) = parseCoords(a.strip())
  elif o in "--latitude":
    new_latitude_ = parseSingleCoordinate(a)
  elif o in "--longitude":
    new_longitude_ = parseSingleCoordinate(a)
  elif o in "--description":
    new_description_=a
  elif o in "--savedir":
    if os.path.isdir(a):
      savedir_=a
    else:
      print "Not a directory:", a
  elif o in "--type":
    if a in cache_type_map:
      new_type_=cache_type_map[a]
    else:
      new_type_=a
      sys.stdout.write("Warning: Cachetype unknown, using raw string.")
    print "New Cachetype:", new_type_


if len(files) <1:
  usage()
  sys.exit()

if display_dialog_ or new_latitude_ == new_longitude_ == new_description_ == new_type_ == None:
  if gui_available_:
    wxapp = wx.App()
    dial = ChngWPTDialog(None, "Change "+",".join(files))
    if dial.ShowModal() == wx.ID_OK:
      (new_latitude_,new_longitude_,new_description_,new_type_) = dial.getInput()
    dial.Destroy()
  else:
    print("wyPython not installed: GUI not available")

print changedCoordsString(new_latitude_, new_longitude_)

for gpxfile in files:
  tree = None
  gcname = None
  gccode = None
  with open(gpxfile, mode="rb") as f:
    parser = etree.XMLParser()
    tree = etree.parse(f,parser).getroot()

  for wpt_elem in tree:
    if wpt_elem.tag[-6:] == "bounds":
      if not new_latitude_ is None:
        wpt_elem.set("minlat",str(new_latitude_))
        wpt_elem.set("maxlat",str(new_latitude_))
      if not new_longitude_ is None:
        wpt_elem.set("minlon",str(new_longitude_))
        wpt_elem.set("maxlon",str(new_longitude_))

    if wpt_elem.tag[-3:] == "wpt":
      if not new_latitude_ is None:
        wpt_elem.set("lat",str(new_latitude_))
        print("* updated latitude");
      if not new_longitude_ is None:
        wpt_elem.set("lon",str(new_longitude_))
        print("* updated longitude");

      if autorename_ or not (new_description_ is None and new_type_ is None):
        for cache_elem in wpt_elem:
          if cache_elem.tag[-7:] == "urlname":
            gcname = cache_elem.text
          elif cache_elem.tag[-4:] == "name":
            gccode = cache_elem.text
          elif not new_type_ is None and cache_elem.tag[-4:] == "type":
            cache_elem.text = "Geocache|"+new_type_
            print("* updated cachetype");
          elif cache_elem.tag[-5:] == "cache":
            for desc_elem in cache_elem:
              if not new_type_ is None and desc_elem.tag[-4:] == "type":
                desc_elem.text = new_type_
              elif not new_description_ is None and desc_elem.tag[-16:] == "long_description":
                desc_elem.set("html","True")
                desc_elem.text=new_description_
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

