#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) Bernhard Tittelbach <xro@gmx.net>
# License: public domain, attribution appreciated


import sys
import os
import fnmatch
import getopt
#import xml.etree.ElementTree as etree
from lxml import etree
import re
import urllib.request, urllib.parse, urllib.error
import atexit
import imghdr
import codecs
from multiprocessing import Pool, Lock, RLock


def usage():
  print("This tool will merge two GPX Files")
  print("\nSyntax:")
  print("   %s -o <output-gpx-file> <gpx-file1> [gpx-file2 [...]]" % (sys.argv[0]))

def guessEncodingFromBOM(filename):
  with open(filename,"rb") as fh:
    sample = fh.read(4)
  for (bom,codec) in [(codecs.BOM_UTF32_LE,"utf_32_le"),(codecs.BOM_UTF32_BE,"utf_32_be"),(codecs.BOM_UTF16_LE,"utf_16_le"),(codecs.BOM_UTF16_BE,"utf_16_be"),(codecs.BOM_UTF8,"utf_8_sig")]:
    if sample.startswith(bom):
      return codec
  return "utf_8"


if __name__ == '__main__':

######### Global Vars ##########
  num_threads_=None #None means: use num_cpu threads
  imagemagick_available_=False
  geotag_images_=True
  delete_old_images_=False
  re_imgnamefilter_=None
  lat_offset_=0.00
  lon_offset_=0.00015
  img_save_path_="./"
  dir_lock_filename_="gc_spoiler_pics.lock"
  look_for_gcjpg_files_and_skip_gc_=False
  files_in_savedir_=None
  done_file_=None
  done_list_= []
  done_list_lock_=Lock()
  gc_in_gpx_list_=[]
  images_ext_=".jpg".lower()
  print_lock_=RLock()

######### Parse Arguments ##########
  try:
    opts, files = getopt.gnu_getopt(sys.argv[1:], "ho:", ["help","output="])
  except getopt.GetoptError as e:
    print("ERROR: Invalid Option: " +str(e))
    usage()
    sys.exit(1)

  output_file_ = None

  for o, a in opts:
    if o in ["-h","--help"]:
      usage()
      sys.exit()
    elif o in ["-o","--output"]:
      output_file_=a

######### Main Program ##########
  if len(files) <1 or output_file_ is None:
    usage()
    sys.exit()
    
    
  wptdict = {}
  gpxmetainfo = {}
  nsmap = {}
  bounds = etree.Element ( 'bounds' , nsmap = nsmap)
  comp_func = {"max":max, "min":min}
  xml_parser = etree.XMLParser(encoding="utf-8")
  for gpxfile in files:
    fgpx = open(gpxfile, encoding=guessEncodingFromBOM(gpxfile))
    try:
      gpxtree = etree.parse(fgpx,xml_parser).getroot()
      nsmap.update(gpxtree.nsmap)  #get namespace info from gpx files
    except (etree.ParserError,etree.DocumentInvalid) as e:
      parprint("ERROR, could not parse %s" % (gpxfile))
      parprint("\tErrorMsg: %s" % (str(e)))
      continue
    fgpx.close()
    
    for wpt_elem in gpxtree:
      if wpt_elem.tag[-3:] == "wpt":
        for cache_elem in wpt_elem:
          if cache_elem.tag[-4:] == "name":
            wptname = cache_elem.text.strip()
            wptdict[wptname] = wpt_elem
      elif wpt_elem.tag[-6:] == "bounds":
        for attrib in ["minlat", "minlon", "maxlat", "maxlon"]:
          if not bounds.attrib.has_key(attrib):
            bounds.attrib[attrib] = wpt_elem.attrib[attrib]
          else:
            try:
              cfun = comp_func[attrib[0:3]]
              bounds.attrib[attrib] = cfun(wpt_elem.get(attrib), bounds.get(attrib))
            except KeyError:
              pass
      else:
        gpxmetainfo[wpt_elem.tag] = wpt_elem
  
  newgpx = etree.Element ( 'gpx' , nsmap = nsmap)
  newgpx.attrib["version"]="1.0" 
  newgpx.attrib["creator"]="GPX Merge Tool" 
  doc = etree.ElementTree ( newgpx)
  
  for elem in gpxmetainfo.values():
    newgpx.append(elem)
  newgpx.append(bounds)
  for elem in wptdict.values():
    newgpx.append(elem)
  
  with open(output_file_, "wb") as nfh:
    nfh.truncate()
    nfh.write(etree.tostring(doc,method="xml",xml_declaration=True,encoding="utf-8"))