#!/usr/bin/python2
# -*- coding: utf-8 -*-

import sys
import getopt
from lxml import etree
import requests
#import re

show_vote_string_="GCVote: %s (%s votes)"
gcvote_getvote_uri_='http://gcvote.com/getVotes.php'
gc_guid_uri_='http://www.geocaching.com/seek/cache_details.aspx?guid='
xml_parser_ = etree.XMLParser(encoding="utf-8")
use_median_=True

def usage():
  print "Sytax:"
  print "       %s [options] <pocketquery.gpx> [...]" % (sys.argv[0])
  print "Options:"
  print "       -h          | --help"
  print "       -u username | --username=gcvote_user"
  print "       -p password | --password=gcvote_pass"
  print "       -m          | --mean     Use mean instead of median"

def splitList(lst,n):
  i=0
  while i < len(lst):
    yield lst[i:i+n]
    i+=n

def getGCVotes(usr, pwd, gcids_list, use_median=True, request_limit=10):
  global gcvote_getvote_uri_
  rdict = {}
  if not gcids_list:
    raise Exception("got empty list")
  for gcids in splitList(gcids_list, request_limit):
    post_data={"version":"2.4e","userName":usr, "password":pwd,"cacheIds":",".join(gcids)}
    r = requests.post(gcvote_getvote_uri_, data=post_data, allow_redirects=False)
    if r.error is None and r.content.find('<votes userName=\'%s\'' % usr) >= 0:
      try:
        tree = etree.fromstring(r.content, xml_parser_)
        for vote in tree.findall(".//vote[@voteMedian]"):
          rdict[vote.get("waypoint")] = (  vote.get("voteMedian") if use_median else vote.get("voteAvg")[0:4]   , vote.get("voteCnt"))
          #print vote.get("cacheId"), vote.get("waypoint"), vote.get("voteMedian"), vote.get("voteAvg"), vote.get("voteCnt"), vote.get("voteUser")
      except (etree.ParserError,etree.DocumentInvalid) as e:
        print e
        continue
    else:
      raise Exception("GC-Vote download error")
  return rdict

if __name__ == '__main__':
  gcvote_username_ = None
  gcvote_password_ = None
  try:
    opts, files = getopt.gnu_getopt(sys.argv[1:], "mhu:p:", ["user=","pass=","help","mean"])
  except getopt.GetoptError as e:
    print "ERROR: Invalid Option: " +str(e)
    usage()
    sys.exit(1)

  if len(files) < 1:
    print "ERROR: no gpx file given\n"
    usage()
    sys.exit()

  for o, a in opts:
    if o in ["-h","--help"]:
      usage()
      sys.exit()
    elif o in ["-u","--user"]:
      gcvote_username_ = a
    elif o in ["-p","--pass"]:
      gcvote_password_ = a
    elif o in ["-m","--mean"]:
      use_median_=False

  for gpxfile in files:
    tree = None
    gccode = None
    gcids = []
    try:
      with open(gpxfile, mode="rb") as f:
        tree = etree.parse(f,xml_parser_).getroot()
    except (etree.ParserError,etree.DocumentInvalid) as e:
      print "ERROR, could not parse %s" % (gpxfile)
      print "\tErrorMsg: %s" % (str(e))
      continue
    urls = [ url.text for url in tree.iterfind(".//{http://www.topografix.com/GPX/1/0}url",namespaces=tree.nsmap) ]
    gcids += map(lambda x: x[len(gc_guid_uri_):], filter(lambda x: x.startswith(gc_guid_uri_), urls))
    votes_dict = getGCVotes(gcvote_username_, gcvote_password_, gcids, use_median=use_median_)
    for wpt_elem in tree.iterfind("{http://www.topografix.com/GPX/1/0}wpt",namespaces=tree.nsmap):
      gccode = wpt_elem.find("{http://www.topografix.com/GPX/1/0}name",namespaces=tree.nsmap).text
      sdesc_elem = wpt_elem.find(".//{http://www.groundspeak.com/cache/1/0}short_description",namespaces=tree.nsmap)
      if sdesc_elem is not None and gccode in votes_dict:
        vote_info = show_vote_string_ % votes_dict[gccode]
        sdesc_elem.set("html","True")
        sdesc_elem.text = vote_info+"<br/>\n"+sdesc_elem.text
    with open(gpxfile, mode="wb") as f:
      f.truncate()
      f.write(etree.tostring(tree,method="xml",xml_declaration=True,encoding="utf-8"))
