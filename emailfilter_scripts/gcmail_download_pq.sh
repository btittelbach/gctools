#!/bin/zsh
local GCUSER=""
local GCPASS=""
local GPX_DIR=""
local GCTOOLS_GRAB_SCRIPT=~/gctools/gc_grab_gpx.py
PQROOTDIR=/data/https/share/GeoCachePocketQuery/

setopt extendedglob
TMPF=$(mktemp)
TMPD=$(mktemp -d)
trap "rm -f $TMPF; rm -Rf $TMPD" EXIT
1>>| $TMPF
local subject="$(egrep "^Subject: \[GEO\] Pocket Query: " $TMPF)"
[[ -z $subject ]] && exit 1
local PQNAME="${subject[30,-1]}"
uudeview -q -i -o +e .zip -p $TMPD $TMPF || exit 2
zipfiles=( "${TMPF}"*.zip(.N) )
if ((#zipfiles == 0)) ; then
  # we could not decode e-mail attachments, let's download stuff
  [[ -x $GCTOOLS_GRAB_SCRIPT ]] && { $GCTOOLS_GRAB_SCRIPT -u "$GCUSER" -p "$GCPASS" -d "$TMPD" "$PQNAME" &>/dev/null || exit 0 }
  zipfiles=( "${TMPD}"*.zip(.N) )
  ((#zipfiles == 0)) && exit 0
fi
for zip in "$zipfiles[@]"; do
  unzip -o -qq -d "$GPX_DIR" "$zip" && rm "$zip" &>/dev/null
done

#delete any GC*.gpx files that are already contained in a PQ gpx file
for newgpx in "${GPX_DIR}"/GC([A-Z0-9])##.gpx(.N) ; do
  grep -q -i "<name>${newgpx:t:r}</name>" "${GPX_DIR}"/*.gpx~"${GPX_DIR}"/GC([A-Z0-9])##.gpx && rm "$newgpx"
done

#now# update_spoilerpics.sh &>/dev/null </dev/null # don't BG ! or subprocess will die when mailfilter closes stdin

exit 0
