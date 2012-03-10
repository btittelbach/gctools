#!/bin/zsh
local GCUSER=""
local GCPASS=""
local GPX_DIR=""
local GCTOOLS_GRAB_SCRIPT=~/gctools/gc_grab_gpx.py
[[ -z $GCUSER || -z $GCPASS ]] && { print "Error: please set GCUSER and GCPASS"; exit 1}
[[ -d $GPX_DIR ]] || { print "Error: please set GPX_DIR to an existing directory"; exit 1}
[[ -x $GCTOOLS_GRAB_SCRIPT ]] || { print "Error: gc_grab_gpx.py not found or not executable"; exit 1}
setopt extendedglob
local -a decfiles
local tmpdir=$(mktemp -d)
trap "rm -Rf $tmpdir" EXIT
uudeview -q +o -t -p "$tmpdir" - || exit 0
decfiles=( "${tmpdir}"/*(.N) )
((#decfiles == 0)) && exit 0
local GCTXT="$(egrep "For GC.....: .* \(.* Cache\)" "${decfiles[@]}")"
if [[ -n $GCTXT  && "$GCTXT" != *"(Unknown Cache)"* && "$GCTXT" == *(#b)(GC([A-Z0-9])##):\ * ]]; then
  $GCTOOLS_GRAB_SCRIPT -u "$GCUSER" -p "$GCPASS" -d "$GPX_DIR" "$match[1]" &>/dev/null
fi
exit 0
