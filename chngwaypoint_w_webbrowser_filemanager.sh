#!/bin/bash
# Associate this script with *.gpx files in your webbrowser (or filemanager)
# and you can directly edit (or not) any downloaded gpx unknown cache file
# which will then get automatically saved to your GPX collection folder

GCTOOLS_PATH=~/gctools
GPX_SAVE_PATH=~/AllMyGPXFiles/
[ -x ${GCTOOLS_PATH}/chngwaypoint.py ] || exit 1
[ -d "$GPX_SAVE_PATH" ] || mkdir -p "$GPX_SAVE_PATH"
${GCTOOLS_PATH}/chngwaypoint.py --gui --rename --savedir "$GPX_SAVE_PATH" "$@"
