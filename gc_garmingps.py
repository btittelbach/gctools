#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) Bernhard Tittelbach <xro@gmx.net>
# License: GPLv3, attribution is appreciated

from __future__ import print_function
import sys,os
import getopt
from lxml import etree
import codecs
import geocachingsitelib as gc
from collections import namedtuple

def usage():
    print("gc_garmingps - A tool to dump garmin-gps fieldnotes/fieldlogs")
    print(" and use that information to delete obsolete waypoints from gpx")
    print(" files or possible delete the gpx files all together")
    print("\nSytax:")
    print("       %s [action] <path to Garmin/ directory>" % (sys.argv[0]))
    print("\nActions:")
    print("       -h           | --help        Show Help")
    print("       -f           | --found       Print found GCCodes")
    print("       -d           | --delete      Delete GC*.gpx files from Garmin/GPX if")
    print("                                     the filename starts with a found GCCode")
    print("       -p           | --purge       Read all files in Garmin/GPX and cut out")
    print("                                     found waypoints. Delete if empty afterwards.")
    print("       -p           | --purge       Purge found wtps from gpx files")
    print("       -s           | --scriptmode  Just print deleted files")
    print("       -n           | --dryrun      Don't really write or delete")


def printLogs(logs):
    print("\n".join(map(lambda l: "%7s: %-12ls %s %s%s" % (l.gccode, l.type, l.date, l.time, " (%s)" % l.comment if l.comment else ""),logs)))

def filterReallyFoundLogs(logs):
    last_gccode=None
    fl=[]
    for log in logs:
        if log.type == "found it":
            last_gccode = log.gccode
            fl.append(log)
        elif log.type == "did not find" and log.gccode == last_gccode:
            fl.pop()
    return fl

def deleteAndPrintGPXFilesNamedAfterFoundGCCodes(logs, gpx_dir, dryrun=True, verbose=True):
    gpx_on_garmin=filter(lambda f: f.startswith("GC") and f.endswith(".gpx") and os.path.isfile(os.path.join(gpx_dir,f)),os.listdir(gpx_dir))
    last_gccode=None
    obsolete_mystery_gpx=[]
    fl=[]
    for log in logs:
        if log.type == "found it":
            last_gccode = log.gccode
            fl = filter(lambda f: f.startswith(log.gccode), gpx_on_garmin)
            obsolete_mystery_gpx+=fl
        elif log.type == "did not find" and log.gccode == last_gccode:
            map(obsolete_mystery_gpx.pop(),fl)
    if obsolete_mystery_gpx:
        if verbose:
            print("\n".join(map(lambda s: "Deleting %s 'cause its filename starts with a found gccode." % s, obsolete_mystery_gpx)))
        if not dryrun:
            map(os.unlink,map(lambda f: os.path.join(gpx_dir, f), obsolete_mystery_gpx))
    return obsolete_mystery_gpx

def grepFile(filename, stringlist):
    #~ assert fh.mode.find("r") != -1
    #~ fh.seek(0)
    with open(filename,"r") as fh:
        return any( [ x in (fh.seek(0), fh.read())[1] for x in (stringlist if isinstance(stringlist,list) else [stringlist]) ] )
    #~ fh.seek(0)
    #~ return pos >= 0

def guessEncodingFromBOM(filename):
    with open(filename,"rb") as fh:
        sample = fh.read(4)
    for (bom,codec) in [(codecs.BOM_UTF32_LE,"utf_32_le"),(codecs.BOM_UTF32_BE,"utf_32_be"),(codecs.BOM_UTF16_LE,"utf_16_le"),(codecs.BOM_UTF16_BE,"utf_16_be"),(codecs.BOM_UTF8,"utf_8_sig")]:
        if sample.startswith(bom):
            return codec
    return "utf_8"

def removeWPTfromGPX(gccodes, gpxfile, verbose=True, dryrun=True):
    removed_files = []
    xml_parser = etree.XMLParser(encoding="utf-8")
    try:
        gpxtree = etree.parse(gpxfile, xml_parser).getroot()
    except (etree.ParserError,etree.DocumentInvalid,etree.XMLSyntaxError) as e:
        print("Warning: could not parse %s" % (gpxfile), file=sys.stderr)
        print("\tErrorMsg: %s" % (str(e)), file=sys.stderr)
        return removed_files
    num_wpts = 0
    ourwpts = []
    for wpt in gpxtree.iterfind("{http://www.topografix.com/GPX/1/0}wpt",namespaces=gpxtree.nsmap):
        num_wpts += 1
        if wpt.findtext("{http://www.topografix.com/GPX/1/0}name",namespaces=gpxtree.nsmap) in gccodes:
            ourwpts.append(wpt)
    if ourwpts and num_wpts > 0:
        if num_wpts == len(ourwpts):
            removed_files.append(os.path.basename(gpxfile))
            if verbose:
                print("%s contains only already found waypoints. Deleting it." % (gpxfile))
            if not dryrun:
                os.unlink(gpxfile)
        else:
            if verbose:
                print("Removing already found waypoints from %s." % (gpxfile))
            for wpt in ourwpts:
                wpt.getparent().remove(wpt)
            if not dryrun:
                etree.ElementTree(gpxtree).write(gpxfile, pretty_print=True,method="xml", xml_declaration=True, encoding="utf-8",inclusive_ns_prefixes=gpxtree.nsmap)
    return removed_files


try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], "hfpdsn", ["help","purge","found","delete","debug","scriptmode","dryrun"])
except getopt.GetoptError, e:
    print("ERROR: Invalid Option: " +str(e), file=sys.stderr)
    usage()
    sys.exit(1)

gcgg_action_ = "print"
script_mode_ = False
dry_mode_ = False

for o, a in opts:
    if o in ["-h","--help"]:
        usage()
        sys.exit()
    elif o in ["-d","--delete"]:
        gcgg_action_ = "delete"
    elif o in ["-s","--scriptmode"]:
        script_mode_ = True
    elif o in ["-p","--purge"]:
        gcgg_action_ = "purgefromgpx"
    elif o in ["-f","--found"]:
        gcgg_action_ = "printfound"
    elif o in ["-n","--dryrun"]:
        dry_mode_ = True
    elif o in ["--debug"]:
        gc.gc_debug = True

if args == []:
        usage()
        sys.exit(1)

gc_logs_xml_filename_="geocache_logs.xml"
garmin_dir_=args[0]
geocache_logs_=os.path.join(garmin_dir_,gc_logs_xml_filename_)
gpx_dir_=os.path.join(garmin_dir_,"GPX")

if not os.path.isfile(geocache_logs_):
    print("ERROR:Could not find %s in %s, aborting...\n\n" % (gc_logs_xml_filename_, garmin_dir_), file=sys.stderr)
    usage()
    sys.exit(2)

logs = gc.read_garmin_fieldnotes_xml(geocache_logs_)
deleted_files = []

if dry_mode_:
    print("Dry-Run, no write or delete will be performed\n")

if gcgg_action_ == "delete":
    deleted_files = deleteAndPrintGPXFilesNamedAfterFoundGCCodes(logs, gpx_dir_,dryrun=dry_mode_, verbose=not script_mode_)
elif gcgg_action_ == "printfound":
    truly_found_gccodes = map(lambda l: l.gccode, filterReallyFoundLogs(logs))
    print("\n".join(truly_found_gccodes))
elif gcgg_action_ == "purgefromgpx":
    truly_found_gccodes = map(lambda l: l.gccode, filterReallyFoundLogs(logs))
    gpx_on_garmin=filter(lambda f: f.endswith(".gpx") and os.path.isfile(f),map(lambda f: os.path.join(gpx_dir_,f), os.listdir(gpx_dir_)))
    possible_obsolete_gpx=filter(lambda f: grepFile(f, truly_found_gccodes), gpx_on_garmin)
    for gpxfile in possible_obsolete_gpx:
        deleted_files += removeWPTfromGPX(truly_found_gccodes, gpxfile, dryrun=dry_mode_, verbose=not script_mode_)
else:
    printLogs(logs)

if script_mode_:
    print("\n".join(deleted_files))
