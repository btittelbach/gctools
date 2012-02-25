#!/usr/bin/python3 -OO
# -*- coding: utf-8 -*-
# (c) Bernhard Tittelbach <xro@gmx.net>
# License: public domain, attribution appreciated

# Thanks:
#  Philipp Becker suggested using ImageMagick to convert non-jpg images from geocaching.com

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
from multiprocessing import Pool, Lock, RLock
from hashlib import md5
import pickle
import codecs

def usage():
  print("This tool will take a geocaching.com pocketquery and download and geotag spoiler pics")
  print("\nSyntax:")
  print("   %s [options] <pq-gpx-file> [pq-gpx-file2 [...]]" % (sys.argv[0]))
  print("\nOptions:")
  print("   --lat_offset <degrees>      Latitude Offset for Images Geotag")
  print("   --lon_offset <degrees>      Longitude Offset for Images Geotag")
  print("   --savedir <dir>             Directory to save images in")
  print("   --filter </regex/>          Regex that needs to match the Image Description")
  print("   --threads <num>             use <num> threads, 0 disables threading, default is number of CPUs")
  print("   -f | --flat                 put all photos in one directory instead of sorting them into GeocachePhotos subdirectories")
  print("   -s | --skip_present         skip GC if at least one picture of GC present in savedir")
  print("   -d | --done_file <filename> use and update list of previously downloaded data")
  print("   -g | --no_geotag            don't geotag images")
  print("   -x | --delete_old           delete images of gc not found in given gpx")
  print("   -h | --help                 Show this Help")
  print("\nExample:")
  print("   This checks all caches in pocketquery 123.gpx for attached pictures that have")  
  print("   either cache, stage or spoiler in their name and downloads them to")  
  print("   ./spoilerpics/ unless done.store say's they've already been checked:")  
  print("  >   %s --savedir ./spoilerpics/  \\" % (sys.argv[0]))
  print("      -d ./spoilerpics/done.store --filter \"cache|stage|spoiler\" 123.gpx")
  print("   Example for a common filter string:")
  print("     --filter \"cache|stage|hinweis|spoiler|hint|area|gegend|karte|wichtig|weg|map|beschreibung|description|blick|view|park|blick|hier|waypoint|track|hiding|place|nah|doserl\"")
  
class GCDoneInfo:
  def __init__(self, gchash=None, imghashset=set()):
    self.gchash = gchash
    self.imghashset = imghashset
  
  def update(self, gchash=None, imghashset=None):
    if not gchash is None:
      self.gchash = gchash
    if not imghashset is None:
      self.imghashset.union(imghashset)
  
def checkImageMagick():
  return (os.system("convert -version &>/dev/null") == 0)

def checkImageIsJPEGAndConvert(filename):
  global imagemagick_available_
  image_file_type = imghdr.what(filename)
  if image_file_type != 'jpeg':
    if imagemagick_available_:
      #imagemagic automatically detects the filetype of the input file and converts to the format specified by the output filename's extension
      if os.system("convert %s %s &>/dev/null" % (filename,filename)) != 0:
        parprint("  successfully converted %s of type %s to jpeg" % (filename, image_file_type))
      else:
        parprint("  ERROR converting %s of type %s to jpeg" % (filename, image_file_type))
        # don't return False, try tagging anyway
    else:
      parprint("  ERROR: %s is of type %s and needs to be converted to jpeg.\nthis can and will be done automatically if you install ImageMagick's convert utility." % (filename, image_file_type))
      return False
  return True

def checkExifTool():
  print("ExifTool version: ", end='', file=sys.stdout)
  sys.stdout.flush()
  return (os.system("exiftool -ver") == 0)

def geotagImage(imgfile, lat, lon, altitude=0):
  latref='N'
  lonref='E'
  if lat < 0.0:
    lat *= -1
    latref='S'
  if lon < 0.0:
    lon *= -1
    lonref='W'
  imgfile_esc=imgfile.replace("'","\\'")
  exiftool_geotag_cmd = "exiftool -ExifIFD= -MakerNotes= -GPSLatitude='%f' -GPSLatitudeRef='%s' -GPSLongitude='%f' -GPSLongitudeRef='%s' -GPSAltitude='%d' -GPSAltitudeRef='0' -overwrite_original -n '%s' &>/dev/null"
  exiftool_deltags_cmd = "exiftool -All= -overwrite_original '%s' &>/dev/null"
  cmd = exiftool_geotag_cmd % (lat,latref,lon,lonref,altitude,imgfile_esc)
  if os.system(cmd) != 0:
    parprint("  Problem geotagging file, deleting all tags of %s and trying again.." % imgfile)
    os.system(exiftool_deltags_cmd % imgfile_esc)
    if os.system(cmd) != 0:
      parprint("  Could not geotag %s" % imgfile)

def downloadImage(imguri, saveas):
  if not saveas is None:
    urllib.request.urlretrieve(url=imguri, filename=saveas)
    urllib.request.urlcleanup()
    return saveas
  return None
  
def getAttachedImages(tree,searchstring):
  for atag in tree.findall(searchstring):
    if atag.tag == "a" and atag.get("class") == "lnk" and atag.get("rel") == "lightbox":
      imguri=atag.get("href")
      imgdesc=etree.tostring(atag,method="text",encoding="utf-8").decode("utf8").strip()
      if imgdesc is None:
        imgdesc=""
      yield (imguri, imgdesc)

def getFileSaveDir(gccode):
  global img_save_path_, allinonedir_
  if allinonedir_:
    return img_save_path_
  else:
    return os.path.join(img_save_path_, gccode[-1], "0" if len(gccode) < 4 else gccode[-2], gccode)

def getFileSavePath(gccode, gcname, imgdesc):
  global allinonedir_, images_ext_
  filename_transtab = bytes.maketrans(b"/ \\",b"___")
  gccode = gccode.encode("utf-8").translate(filename_transtab, b'?&!;:"<=>*#[]{}()\'').decode("utf-8")
  gcname = gcname.encode("utf-8").translate(filename_transtab, b'?&!;:"<=>*#[]{}()\'').decode("utf-8")
  imgdesc = imgdesc.encode("utf-8").translate(filename_transtab, b'?&!;:"<=>*#[]{}()\'').decode("utf-8")
  return os.path.join(getFileSaveDir(gccode), "_".join([gccode, gcname, imgdesc]) +  images_ext_  if allinonedir_ else imgdesc+images_ext_)

def checkExistsFilePatternInDir(img_save_path, pattern):
  for fn in os.listdir(img_save_path):
    if fnmatch.fnmatch(fn, pattern):
      return True
  return False

def getFilePatternInSaveDir(pattern):
  global files_in_savedir_, img_save_path_
  if files_in_savedir_ is None:
    files_in_savedir_=os.listdir(img_save_path_)
  for fn in files_in_savedir_:
    if fnmatch.fnmatch(fn, pattern):
      yield fn

def deleteFilePatternInSaveDir(pattern):
  global files_in_savedir_, img_save_path_
  deleted_files=[]
  if files_in_savedir_ is None:
    files_in_savedir_=os.listdir(img_save_path_)
  for fn in files_in_savedir_:
    if fnmatch.fnmatch(fn, pattern):
      os.remove(fn)
      deleted_files.append(fn)
  return deleted_files
  
def rmdirEmptyDirs(path):
  if not os.path.isdir(path):
    return False
  for dn in os.listdir(path):
    fdp=os.path.join(path,dn)
    if os.path.isdir(fdp):
      rmdirEmptyDirs(fdp)
  if len(os.listdir(path)) == 0:
    os.rmdir(path)

def genListOfImagesNotStartingWithGCCodeInSaveDir(list_of_gccodes_to_preserve):
  global files_in_savedir_, img_save_path_, images_ext_
  all_files = list(map(lambda x: os.path.join(img_save_path_, x), os.listdir(img_save_path_)))
  for fp in all_files:
    if os.path.isdir(fp):
      all_files += list(map(lambda x: os.path.join(fp, x), os.listdir(fp)))
    elif os.path.isfile(fp):
      #only check and delete images
      if fp.lower().endswith(images_ext_):
        (fhead, fn) = os.path.split(fp)
        fdir = os.path.basename(fhead)
        if not (fdir in list_of_gccodes_to_preserve or any( map(fn.startswith,  list_of_gccodes_to_preserve))):
          yield(fp)

def parprint(string, sep=' ', end='\n', output=sys.stdout):
  global print_lock_
  with print_lock_:
    try:
      print(string,sep=sep,end=end,file=output)
    except:
      pass

def downloadAndTag(imguri, filepath, latitude, longitude, altitude):
  global geotag_images_
  # if donefile is in use, we have already checked if (imguri, imgdesc) combination was previously downloaded
  # so if the filepath does indeed already exist, we can asume the image has changed and safely overwrite it
  if not done_file_ is None or not os.path.exists(filepath):
    filepath = downloadImage(imguri, filepath)
    parprint("  Downloaded %s" % filepath)
    if checkImageIsJPEGAndConvert(filepath):
      if geotag_images_:
        geotagImage(filepath, latitude, longitude, altitude)
  else:
    parprint("  Skipped %s (Reason: File exists)" % filepath)

def parseHTMLDescriptionDownloadAndTag(url, gccode, gcname, gchash, latitude, longitude, altitude, mp_pool=False):
  global re_imgnamefilter_, img_save_path_, images_ext_
  html_parser = etree.HTMLParser(encoding="utf-8")
  parprint("Processing: %s %s" %(gccode, gcname))
  try:
    fcp = urllib.request.urlopen(url)
    gcwebtree = etree.parse(fcp,html_parser).getroot()
    fcp.close()
  except (urllib.error.URLError, socket.gaierror) as e:
    parprint("ERROR accessing url of waypoint.\n\tURL: %s\n\tErrorMsg: %s" % (url,str(e)))
    return None
  except (etree.ParserError, etree.DocumentInvalid) as e:
    parprint("ERROR parsing html page of waypoint.\n\tURL: %s\n\tErrorMsg: %s" % (url,str(e)))
    return None
  imghashset = set()
  for imguri,imgdesc in getAttachedImages(gcwebtree,".//p[@class='NoPrint']/a[@class='lnk']"):
    if not re_imgnamefilter_ is None:
      m = re_imgnamefilter_.search(imgdesc)
      if m is None:
        parprint("  Skipped %s:%s (Reason: does not match --filter)" % (gccode, imgdesc))
        continue
    imghash = genImgHash(imguri, imgdesc)
    if checkPreviouslyDoneImg(gccode, imghash):
      parprint("  Skipped %s:%s (Reason: URI was downloaded previously)" % (gccode,imgdesc))
      continue
    imghashset.add(imghash)
    filepath = getFileSavePath(gccode, gcname, imgdesc)
    if mp_pool:
      mp_pool.apply_async(downloadAndTag,(imguri, filepath, latitude, longitude, altitude))
    else:
      downloadAndTag(imguri, filepath, latitude, longitude, altitude)
  return (gccode, gchash, imghashset)

def addToDone(gccode, hash=None, imghashset=set()):
  global done_dict_, done_dict_lock_
  if gccode is None or (hash is None and len(imghashset) == 0):
    return
  with done_dict_lock_:
    if not gccode in done_dict_:
      done_dict_[gccode] = GCDoneInfo(hash, imghashset)
    else:
      done_dict_[gccode].update(hash, imghashset)
        
def addTupleToDone(t):
  addToDone(*t)

## Note that checkPreviouslyDoneGC and checkPreviouslyDoneImg work an separate copies of the done_dict_ and only addToDone updates the list which will then be written do disk
def checkPreviouslyDoneGC(gccode, hash):
  global done_dict_, done_dict_lock_
  #with done_dict_lock_:  # lock unnecessary, unshared local memory copy
  if gccode in done_dict_:
    return done_dict_[gccode].gchash == hash
  else:
    return False

def checkPreviouslyDoneImg(gccode, imghash):
  global done_dict_, done_dict_lock_
  #with done_dict_lock_:  # lock unnecessary, unshared local memory copy
  if gccode in done_dict_:
    return imghash in done_dict_[gccode].imghashset
  else:
    return False  

def writeDoneFile():
  global done_file_, done_dict_, done_dict_lock_
  if not done_file_ is None:
    try:
      with open(done_file_,"wb") as dfh:
        dfh.truncate()
        with done_dict_lock_:
          pickle.dump(done_dict_, dfh, 2)
    except (OSError, IOError) as e:
      print("ERROR, could not write done file: " + str(e))

def genCacheDescriptionHash(cache_etree):
  #clear out elements that change even if cache description was not updated
  for elem in cache_etree.findall(".//groundspeak:logs", cache_etree.nsmap) + cache_etree.findall(".//groundspeak:travelbugs", cache_etree.nsmap):
    elem.clear()
  hash = md5()
  hash.update(etree.tostring(cache_etree, encoding="utf-8", method="xml"))
  return hash.hexdigest()

def genImgHash(imguri, imgdesc):
  hash = md5()
  hash.update(os.path.basename(imguri).encode("utf-8"))
  hash.update(imgdesc.encode("utf-8"))
  return hash.hexdigest()  

def reInitGlobalVars(var_dict):
  for varname in var_dict.keys():
    if globals()[varname] is None:
      globals()[varname] = var_dict[varname]

def terminateProcesses(pool):
  if not pool is None:
    pool.terminate()

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
  done_dict_= {}
  done_dict_lock_=Lock()
  gc_in_gpx_list_=[]
  images_ext_=".jpg".lower()
  print_lock_=RLock()
  allinonedir_=False

######### Parse Arguments ##########
  try:
    opts, files = getopt.gnu_getopt(sys.argv[1:], "fhsgxd:", ["help","delete_old","skip_present","done_file=","lat_offset=","lon_offset=","savedir=", "filter=","no_geotag","threads=","flat"])
  except getopt.GetoptError as e:
    print("ERROR: Invalid Option: " +str(e))
    usage()
    sys.exit(1)

  for o, a in opts:
    if o in ["-h","--help"]:
      usage()
      sys.exit()
    elif o in ["-f","--flat"]:
      allinonedir_=True
    elif o in ["--threads"]:
      num_threads_=abs(int(a))
    elif o in ["--lat_offset"]:
      lat_offset_=float(a)
    elif o in ["--lon_offset"]:
      lon_offset_=float(a)
    elif o in ["--savedir"]:
      img_save_path_=a
    elif o in ["--filter"]:
      re_imgnamefilter_=re.compile(a, re.IGNORECASE)
    elif o in ["-s", "--skip_present"]:
      look_for_gcjpg_files_and_skip_gc_=True
    elif o in ["-g", "--no_geotag"]:
      geotag_images_=False
    elif o in ["-x", "--delete_old"]:
      delete_old_images_=True
    elif o in ["-d", "--done_file"]:
      done_file_=a
      if os.path.exists(done_file_):
        try:
          with open(done_file_,"rb") as dfh:
            done_dict_ = pickle.load(dfh)
        except (EOFError, IOError, pickle.UnpicklingError):
          print("ERROR, could not load existing donefile")

######### Main Program ##########
  if len(files) <1:
    usage()
    sys.exit()

  if not img_save_path_[-1] == "/":
    img_save_path_ += "/"

  # Check Lockfile
  if os.path.exists(img_save_path_+dir_lock_filename_):
    print("ERROR: Images directory may be in use by another instance of this script !!")
    print("       If you are sure this is not the case: rm %s" % os.path.join(img_save_path_,dir_lock_filename_ ))
    sys.exit(1)

  # Touch Lockfile:
  open(os.path.join(img_save_path_,dir_lock_filename_ ), 'w').close()
  atexit.register(lambda: os.remove(os.path.join(img_save_path_,dir_lock_filename_ )))

  atexit.register(writeDoneFile)
  
  # Check ImageMagick convert available:
  imagemagick_available_ = checkImageMagick()
  if not imagemagick_available_:
    print("WARNING: ImageMagick convert utility not found, image conversion disabled !")

  # Check exiftool available
  if geotag_images_:
    geotag_images_=checkExifTool()
    if not geotag_images_:
      print("WARNING: exiftool not found, image geotagging disabled !")

  # start multiprocess pool
  mp_pool = False
  if not num_threads_ is 0:
    globals_for_processes = {"done_dict_":done_dict_,"done_file_":done_file_,"print_lock_":print_lock_, "geotag_images_":geotag_images_, "imagemagick_available_":imagemagick_available_, "re_imgnamefilter_":re_imgnamefilter_, "img_save_path_":img_save_path_, "images_ext_":images_ext_}
    mp_pool = Pool(processes=num_threads_, initializer=reInitGlobalVars, initargs=(globals_for_processes, ))
    atexit.register(terminateProcesses, mp_pool)
    parprint("multi-processing enabled")
  
  xml_parser = etree.XMLParser(encoding="utf-8")
  nsmap = {}
  for gpxfile in files:
    fgpx = open(gpxfile, encoding=guessEncodingFromBOM(gpxfile))
    try:
      gpxtree = etree.parse(fgpx,xml_parser).getroot()
      nsmap.update(gpxtree.nsmap)  #get namespace info from gpx files
    except (etree.XMLSyntaxError,etree.ParserError,etree.DocumentInvalid) as e:
      parprint("ERROR, could not parse %s" % (gpxfile))
      parprint("\tErrorMsg: %s" % (str(e)))
      continue
    fgpx.close()
    
    for wpt_elem in gpxtree:
      if wpt_elem.tag[-3:] == "wpt":
        latitude = float(wpt_elem.get("lat"))
        longitude = float(wpt_elem.get("lon"))
        altitude = 0
        gccode = None
        url = None
        gcname = None
        for cache_elem in wpt_elem:
          if cache_elem.tag[-7:] == "urlname":
            gcname = cache_elem.text.strip()
          elif cache_elem.tag[-4:] == "name":
            gccode = cache_elem.text.strip()
          elif cache_elem.tag[-3:] == "url":
            url = cache_elem.text.strip()
          elif cache_elem.tag[-5:] == "cache":
            gchash = genCacheDescriptionHash(cache_elem)
        
        gc_in_gpx_list_.append(gccode)
        
        gcimgdir = getFileSaveDir(gccode)
        if not allinonedir_:
          if not os.path.isdir(gcimgdir):
            os.makedirs(gcimgdir)
          for imgfile in getFilePatternInSaveDir(gccode+"*"+images_ext_):
            shutil.move(imgfile, gcimgdir)
        if checkPreviouslyDoneGC(gccode,gchash):
          parprint("Skipping: %s %s (Reason: Cache GPX description unchanged)" % (gccode, gcname))
          continue
        if look_for_gcjpg_files_and_skip_gc_ and checkExistsFilePatternInDir(gcimgdir, gccode+"*"+images_ext_):
          parprint("Skipping: %s %s (Reason: --skip_present given and at least one image for GC exists)" % (gccode, gcname))
          continue
        if url is None:
          continue
        if mp_pool:
          mp_pool.apply_async(parseHTMLDescriptionDownloadAndTag,(url, gccode, gcname, gchash, latitude + lat_offset_, longitude + lon_offset_, altitude), callback=addTupleToDone)
        else:
          addTupleToDone(parseHTMLDescriptionDownloadAndTag(url, gccode, gcname, gchash, latitude + lat_offset_, longitude + lon_offset_, altitude))
          
  if delete_old_images_:
    for fp in genListOfImagesNotStartingWithGCCodeInSaveDir(gc_in_gpx_list_):
      parprint("Deleting old image: %s" % fp)
      os.remove(fp)
#    with done_dict_lock_:
    for rgccode in set(done_dict_.keys()).difference(set(gc_in_gpx_list_)):
      del done_dict_[rgccode]

  if mp_pool:
    mp_pool.close()
    mp_pool.join()
    mp_pool = None

  print("removing empty directories..")
  rmdirEmptyDirs(img_save_path_)
  
  print("All Done! Now move contents of %s to %s on your garmin device" % (img_save_path_, os.path.join("/garmin","JPEG") if allinonedir_ else os.path.join("/garmin","GeocachePhotos")))

