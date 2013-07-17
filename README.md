gctools - a collection of useful Geocaching scripts
===================================================

These scripts have been written and tested on GNU/Linux.
Your experience on other operation systems may vary.
Feedback and patches are welcome.

See Installation Notes at end of file.

gc_get_spoiler_pics.py
----------------------
Takes a geocaching.com pocket-query .gpx-file and trawls the geocaching.com homepage for garmin/GeocachePhotos.
The downloaded images can be geotagged with the geocache's coordinates and/or sorted into directories compatible with the Garmin GeocachePhoto feature on newer Garmin handheld GPS devices.  (e.g. Oregon x50, Montana, etc with newest Firmware)

Once the images are downloaded you can either put them into the ``Garmin/GeocachePhotos/`` folder on your Garmin handheld gps in which case a "Show Photos" menu-entry will appear on your device on Geocaches with images.

Or you can put them into your gps handhelds image folder where they will appear as Photo waypoints on your Map if your GPS handheld supports geotagged photos. e.g. ``Garmin/JPEG/`` on Garmin devices. In this case the ``--flat`` option may be helpful.

### Requirements

* python3
* python3-lxml
* imagemagick
* exiftool (libimage-exiftool-perl)


### Usage

    Syntax:
      ./gc_get_spoiler_pics.py [options] <pq-gpx-file> [pq-gpx-file2 [GCCODE*.jpg [...]]]

    Options:
      --lat_offset <degrees>      Latitude Offset for Images Geotag
      --lon_offset <degrees>      Longitude Offset for Images Geotag
      --savedir <dir>             Directory to save images in
      --filter </regex/>          Regex that needs to match the Image Description
      --threads <num>             use <num> threads, 0 disables threading, default is number of CPUs
      --flat               put all photos in one directory instead of sorting them into GeocachePhotos
      -s | --skip_present         skip GC if at least one picture of GC present in savedir
      -d | --done_file <filename> use and update list of previously downloaded data
      -g | --no_geotag            don't geotag images
      -x | --delete_old           delete images of gc not found in given gpx
      -h | --help                 Show this Help

* ``--lat/lon_offset``   
  when geotagging images with the geocaches's coordinates, per default a slight offset is added so when viewing the Map on your GPS handheld, the image icon won't hide the geocache icon.
  this option allows you to specify a different or 0 offset

* ``--filter``   
  if specified, only images which's description matches the given regular expression are downloaded.  
  e.g.: ``--filter "cache|stage|hinweis|spoiler|hint|area|gegend|karte|wichtig|weg|map|beschreibung|description|blick|view|park|blick|hier|waypoint|track|hiding|place|nah|doserl"``

* ``--threads``  
  Number of parallel threads to use. ``--threads 18`` seems to work well and really speeds things up.

* ``--flat``  
  per default, images are sorted into directories suitable for the ``Garmin/GeocachePhotos/ folder.``    
  You may want to read the corresponding [Garmin Blog Entry](http://garmin.blogs.com/softwareupdates/2012/01/geocaching-with-photos.html).
  
  ``--flat<`` disables this behaviour. E.g. when you intend to copy the downloaed images into your ``Garmin/JPEG/`` folder instead of ``Garmin/GeocachePhotos/`` folder.

* ``--done_file <donefile>``  
  the script will use the specified file to remember which images from which GeoCaches were previously downloaded and the geocaching.com homepage need not be checked again.
  This is done using a hash of the gpx file's GC description, so the cache is checked for new images if the cache description has changed.

* ``--delete_old``  
  Delete all images that don't belong to any geocache in any of the given gpx-files.

### Example
This checks all caches in pocket-query 123.gpx for attached pictures that have
either cache, stage or spoiler in their name and downloads them to
``./garmin/GeocachePhotos/`` unless ''done.store'' say's they've already been checked:

    ./gc_get_spoiler_pics.py -x --savedir ./garmin/GeocachePhotos/  \
      -d ./garmin/GeocachePhotos/done.store --filter "cache|stage|spoiler" 123.gpx

This sorts images named after their GCCODE into the ``./garmin/GeocachePhotos/`` directory:

    ./gc_get_spoiler_pics.py --savedir ./garmin/GeocachePhotos/ GC12345_geochech_spoiler.jpg GC12ABC_other_spoiler.jpg

### Full HowTo for Ubuntu/Debian Linux, bash and Garmin devices
* install required software:  
  ``sudo apt-get install python3 python3-lxml imagemagick libimage-exiftool-perl``
* Create the folder on your garmin gps handheld:  
  ``mkdir /media/GARMIN/garmin/GeocachePhotos/``
* Create a pocketquery and save into ``/media/GARMIN/Garmin/GPX/``
* use the script:

        shopt -s extglob
        ~/gctools/gc_get_spoiler_pics.py --lat_offset 0 --lon_offset 0  \
          --savedir /media/GARMIN/Garmin/GeocachePhotos/      \
          --done_file /media/GARMIN/Garmin/GeocachePhotos/done.store   \
          --delete_old --threads 18 /media/GARMIN/Garmin/GPX/!(*-wpts).gpx



gc_bulklog_fieldnotes.py
------------------------

Log multiple fieldnotes at once with the same text. 

Useful for logging powertrails.
Textsubstituion of date and time with %D and %T are supported.

### Requirements

* python  	(i.e. python2)
* python-lxml	(i.e. python2-lxml)
* wxwidgets  (python-wxgtk2.8 or higher)


### Usage

just launch it, it has a GUI.

    Sytax:
           ./gc_bulklog_fieldnotes.py [-u <user> -p <pass>]
    Options:
           -h           | --help             Show Help
           -u username  | --username=gc_user 
           -p password  | --password=gc_pass 
           -i           | --noninteractive   Never prompt for pwd, just fail


chngwaypoint.py
---------------
Change the Coordinates and or Description of a given geocaching.com .gpx-file.

I use this to change the coordinates of mystery-caches I've solved and download only those solved mysteries onto my handheld gps. Thus is can collect solved Mysteries like Traditionals on the road and have the the original hint or any solved description right there on my GPS with me.

### Requirements

* python  	(i.e. python2)
* python-lxml	(i.e. python2-lxml)
* wxwidgets  (python-wxgtk2.8 or higher)


### Usage

Just call it with one or several gpx-file(s) as argument and a dialog will pop up where you can make changes.
Instead of running it from the command-line, you could also DnD files onto the chngwaypoint.py scriptfile.

    Sytax:
           ./chngwaypoint.py [options] <gpx-file> [more gpx files ...]
    Options:
      -c <coords>           | --coord <coords> Change Coordinates
                              --lat <latitude> Change Latitude
                              --lon <longitud> Change Longitude
      -k <shortdesc>        | --shortdesc <tx> Change Short-Description
      -d <desc>             | --desc <desc>    Change Description
      -t [multi|tradi|myst] | --type <type>    Change Type
      -s <dir>              | --savedir <dir>  Save to directory
      -r                    | --rename         Rename to GCCODE_name.gpx
      -g                    | --gui           Display GUI (default if no option given)
      -h                    | --help          Show Help


gpx_merge.py
------------

Merge two or more gpx-files (e.g. pocket-queries) into one, filtering out any duplicates.

Suppose you generate multiple overlapping pocket-queries, you put them onto your GPS including the ``*-wpts.gpx`` waypoint files. The fact that some waypoints from those additional waypoint files pop up multiple times (once for each ``*-wpts.gpx``) annoys you.
No more !!
Use gpx_merge.py to merge all ``*-wpts.gpx`` into one ``waypoints.gpx`` and: problem solved!

Your waypoint files is larger than the maximum number of waypoints supported by your GPS ?
Use the limit option ``-l`` to set a maximum number of waypoints to write into the output file.

### Requirements
* python3
* python3-lxml

### Usage

    Options:
      -o <output-gpx-file>
      -l <maximum number of waypoints in output-gpx-file>

    Syntax:
      ./gpx_merge.py -o <output-gpx-file> <gpx-file1> [gpx-file2 [...]]

    Example:
      ./gpx_merge.py -o london-wpts.gpx london1-wpts.gpx london2-wpts.gpx london3-wpts.gpx

to merge (and strip duplicate gccodes) serveral PQs into two files using zsh shell syntax:

    ~/gctools/gpx_merge.py -o merge.gpx **/(<->*.gpx~*-wpts.gpx)(.)
    ~/gctools/gpx_merge.py -o merge-wpts.gpx **/<->*-wpts.gpx(.)


gc_grab_gpx.py
--------------

Fetch one or more single-cache GPX files or precompiled pocketqueries from the geocaching.com website.

### Requirements

* geocaching.com premium membership login
* python  	(i.e. python2)
* python-lxml	(i.e. python2-lxml)
* python-requests

### Usage
    Sytax:
           ./gc_grab_gpx.py [options] <gccode|pquid|pqname> [...]
    Options:
           -h           | --help             Show Help
           -d dir       | --gpxdir=dir       Write gpx to this dir
           -l           | --listpq           List PocketQueries
           -a           | --allpq            Download all PocketQueries
           -c           | --createpqdir      Create dir for PQ
           -u username  | --username=gc_user 
           -p password  | --password=gc_pass 
           -i           | --noninteractive   Never prompt for pwd, just fail
    If username and password are not provided, we interactively
    ask for them the first time and store a session cookie. Unless -i is given

    Examples:
      ./gc_grab_gpx.py GC3APJW GC3BFT3 "Events in Graz" 148faed7-c780-4293-aeb9-a8e02356c5f6
      ./gc_grab_gpx.py -a
      ./gc_grab_gpx.py -l
      ./gc_grab_gpx.py -u besserverstecker -p wonderwhytheyhateme -l


gc_add_gcvote_to_pq.py
----------------------

Inserts GCVote data into the short_description of one or more groundspeak pocketquery GPX files

Note that it's a bad idea to change the description of a GPX file with ``gc_add_gcvote_to_pq.py`` and then download spoilerpics with ``gc_get_spoiler_pics.py``, since the later depends on unchanged GC descriptions to figure out if it needs to redownload a spoiler image or not.

Also note, that for now, calling ``gc_add_gcvote_to_pq.py`` on a file repeatedly will not change the GC-Vote Information, but just add new lines of GC-Vote text additionally to the old ones. (Of course, this might be what you want to include both --mean and median information)

### Requirements

* python  	(i.e. python2)
* python-lxml	(i.e. python2-lxml)
* python-requests

### Usage
    Sytax:
        ./gc_add_gcvote_to_pq.py [options] <pocketquery.gpx> [...]
    Options:
        -h          | --help
        -u username | --username=gcvote_user
        -p password | --password=gcvote_pass
        -m          | --mean     Use mean instead of median


gc_upload_fieldnotes.py
-----------------------

Uploads fieldnote files from geocaching.com compatible GPS devices to the website.

### Requirements

* python  	(i.e. python2)
* python-lxml	(i.e. python2-lxml)
* python-requests

### Usage
    Sytax:
           [./gc_upload_fieldnotes.py -u <user> -p <pass>] geocache_visits.txt
    Options:
           -h           | --help             Show Help
           -u username  | --username=gc_user 
           -p password  | --password=gc_pass 
           -i           | --noninteractive   Never prompt for pwd, just fail
    If username and password are not provided, we interactively
    ask for them the first time and store a session cookie. Unless -i is given

    Examples:
      ./gc_upload_fieldnotes.py /media/GARMIN/Garmin/geocache_visits.txt
      ./gc_upload_fieldnotes.py /media/MAGELLAN/Geocaches/newlogs.txt


CustomSymbols
-------------

copy the folder ``CustomSymbols`` to into the subfolder ``/Garmin/`` on your Oregon/Dakto/Montana/eTrex30 
to change the geocache-waypoint icon from the blue flag to smaller unobtrusive symbols:

* Question of Answer of a Multicache  
  becomes an orange dot

* Stages of a Multicache  
  becomes an orange dot with one green quarter
  
* Final Location of a Multicache    
  becomes an orange dot with a crosshair


Older Stuff
-----------

### Send2GPS
Nautilus script (copy to ``~/.gnome2/nautilus-scripts/``) that uses [gpsbabel](http://www.gpsbabel.org/) to transfer a selected GPX file to an older usb-connected Garmin GPS (i.e. 60CSx)

### mkwaypoint.pl
Old perl CL script to create create a .gpx and/or .lmx file from given coordinates and description.

### gc_gpx_garmin.sed
Use with Garmin 60CSx or older before transferring the pocket query to your gps. Changes the icon of multi-caches from ``Geocache`` to ``Stadion`` (the one with the 3 flags), so you can differentiate between multis and tradis on the go

    sed -r -f ~/gc_gpx_garmin.sed <pocketquery-gpx-file>


gctools - Installation Notes
===================================================

Debian/Ubuntu GNU/Linux
-----------------------

run the following on the CL and your are done:

    apt-get install python-requests python-lxml python-wxgtk2.8 python3-requests python3-lxml libimage-exiftool-perl


Windows
-------

Installing all the requirements on windows seems to be a bit more involved,
but for the Python2 scripts these are the required steps:

* Consult http://docs.python-guide.org/en/latest/starting/install/win.html
* Install the lastest Python2 from http://python.org/download/
* Add Python to your path (see link above).
  Best done by running the following command in PowerShell:
  ``[Environment]::SetEnvironmentVariable("Path", "$env:Path;C:\Python27\;C:\Python27\Scripts\", "User")``
* Download and run http://python-distribute.org/distribute_setup.py
* Install WXPython from http://wxpython.org/download.php
* Install lxml from http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml
* Install requests by running cmd.exe 
  and then type ``pip install requests``


For Python3:
* Install Virtualenv by running ``pip install virtualenv`` in cmd
* Install latest Python 3.x from http://python.org/download/
* Setup a Python3 virtual environment