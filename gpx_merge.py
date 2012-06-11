#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) Bernhard Tittelbach <xro@gmx.net>
# License: public domain, attribution appreciated


import sys
import getopt
from lxml import etree
import codecs
from itertools import *


def usage():
  print("This tool will merge two GPX Files")
  print("\nOptions:")
  print("   -o <output-gpx-file>")
  print("   -l <maximum number of waypoints in output-gpx-file>")
  print("\nSyntax:")
  print("   %s -o <output-gpx-file> <gpx-file1> [gpx-file2 [...]]" % (sys.argv[0]))

def guessEncodingFromBOM(filename):
  with open(filename,"rb") as fh:
    sample = fh.read(4)
  for (bom,codec) in [(codecs.BOM_UTF32_LE,"utf_32_le"),(codecs.BOM_UTF32_BE,"utf_32_be"),(codecs.BOM_UTF16_LE,"utf_16_le"),(codecs.BOM_UTF16_BE,"utf_16_be"),(codecs.BOM_UTF8,"utf_8_sig")]:
    if sample.startswith(bom):
      return codec
  return "utf_8"

def calcBounds(wpt, bounds):
  comp_func = {"max":max, "min":min}
  for attrib in ["minlat", "minlon", "maxlat", "maxlon"]:
    if not bounds.attrib.has_key(attrib):
      bounds.set(attrib,wpt.get(attrib[-3:]))
    else:
      try:
        cfun = comp_func[attrib[:3]]
        bounds.attrib[attrib] = cfun(wpt.get(attrib[-3:]), bounds.get(attrib))
      except KeyError:
        pass


if __name__ == '__main__':

######### Global Vars ##########
  output_file_ = None
  wpt_limit_ = None


######### Parse Arguments ##########
  try:
    opts, files = getopt.gnu_getopt(sys.argv[1:], "ho:l:", ["help","output=","limit="])
  except getopt.GetoptError as e:
    print("ERROR: Invalid Option: " +str(e), file=sys.stderr)
    usage()
    sys.exit(1)

  for o, a in opts:
    if o in ["-h","--help"]:
      usage()
      sys.exit()
    elif o in ["-o","--output"]:
      output_file_ = a
    elif o in ["-l","--limit"]:
      try:
        wpt_limit_ = int(a)
      except ValueError:
        print("Warning: given limit is not an integer, ignoring it...",file=sys.stderr)

######### Main Program ##########
  if len(files) <1 or output_file_ is None:
    print("ERROR: no input files and/or no output file given",file=sys.stderr)
    usage()
    sys.exit()
    
  wptdict = {}
  gpxmetainfo = {}
  nsmap = {}
  bounds = etree.Element ( 'bounds' , nsmap = nsmap)
  xml_parser = etree.XMLParser(encoding="utf-8")
  for gpxfile in files:
    fgpx = open(gpxfile, encoding=guessEncodingFromBOM(gpxfile))
    try:
      gpxtree = etree.parse(fgpx,xml_parser).getroot()
      nsmap.update(gpxtree.nsmap)  #get namespace info from gpx files
    except (etree.ParserError,etree.DocumentInvalid,etree.XMLSyntaxError) as e:
      print("Warning: could not parse %s" % (gpxfile), file=sys.stderr)
      print("\tErrorMsg: %s" % (str(e)), file=sys.stderr)
      continue
    fgpx.close()

    for wpt_elem in gpxtree:
      if wpt_elem.tag == "wpt" or (wpt_elem.tag.startswith("{http://www.topografix.com/GPX/") and wpt_elem.tag.endswith("}wpt")):
        calcBounds(wpt_elem, bounds)
        for wpt_subelem in wpt_elem:
          if wpt_subelem.tag == "name" or (wpt_subelem.tag.startswith("{http://www.topografix.com/GPX/") and wpt_subelem.tag.endswith("}name")):
            wptname = wpt_subelem.text.strip()
            wptdict[wptname] = wpt_elem
            break
      elif wpt_elem.tag[-6:] == "bounds":
        pass
      else:
        gpxmetainfo[wpt_elem.tag] = wpt_elem
  
  newgpx = etree.Element ( 'gpx' , nsmap = nsmap)
  newgpx.attrib["version"]="1.0" 
  newgpx.attrib["creator"]="GPX Merge Tool" 
  doc = etree.ElementTree ( newgpx)

  if wpt_limit_ is None:
    wpt_limit_ = len(wptdict)
  else:
    wpt_limit_ = min(wpt_limit_,len(wptdict))
  
  for elem in gpxmetainfo.values():
    newgpx.append(elem)
  newgpx.append(bounds)
  for elem in islice(wptdict.values(),wpt_limit_):
    newgpx.append(elem)
  
  with open(output_file_, "wb") as nfh:
    nfh.truncate()
    nfh.write(etree.tostring(doc,method="xml",xml_declaration=True,encoding="utf-8"))
  print ("%d waypoints merged into %s" % (wpt_limit_, output_file_))
  if wpt_limit_ < len(wptdict):
    print("Waypoint limit was exceeded and the following waypoints were dropped:")
    print(", ".join(islice(wptdict.keys(),wpt_limit_,None)))
