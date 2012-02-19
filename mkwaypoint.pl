#!/usr/bin/perl -w
#(c) Bernhard Tittelbach, 2007-2010
use utf8;
use Getopt::Long;
use Pod::Usage;
use POSIX qw(strftime);

#Defaults
my $desc="";
my $name="Geocache";
my $city="Graz";
my $state="Steiermark";
my $country="Austria";
my $lat=0;
my $long=0;

GetOptions(
            "mkgpx!"=>\$mkgpx,
            "mklmx!"=>\$mklmx,
            "tfgpx!"=>\$transfer_gpx,
            "overwrite!"=>\$overwriteflag,
            "help!"=>\$helpflag,
            "latitude:s"=>\$latitudearg,
            "longitude:s"=>\$longitudearg,
            "coordinates:s"=> \$latitudelongitudearg,
            "description:s"=> \$desc,
            "city:s"=> \$city,
            "state:s"=> \$state,
            "country:s"=> \$country) or pod2usage(1);


$name = join(" ",@ARGV);
$name =~ s/\//_/g;
my $lmx_file = $name.".lmx";
my $gpx_file = $name.".gpx";

if (defined $helpflag)
{
  pod2usage(-verbose => 2, -exitval => 0, -message => "--------HELP--------\n");
}

sub convert_single
{
  my $c=uc(shift(@_));
  $c=~s/,/./;
  if ($c=~/(N|S|W|E|O)?\s*(\d{2,3})\D*(\d{1,2}\.\d{3})/) {
    my $nv = ($2+($3/60));
    $nv = 0.0-$nv if ($1 eq "S" or $1 eq "W");
    return $nv;
  }
  else
  {
    return $c;
  }
}

sub convert_both
{
  my $c = shift(@_);
  if ($c =~ /((?:N|S).+)\s+((?:W|E|O).+)/i)
  {
    return (convert_single($1),convert_single($2));
  }
  elsif ($c =~ /((?:W|E|O).+)\s+((?:N|S).+)/i)
  {
    return (convert_single($2),convert_single($1));
  }
  else
  {
    print "Error, couldn't parse Coordinates\n\n";
    exit 2;
  }
}


if (defined $latitudelongitudearg)
{
  ($lat,$long) = convert_both($latitudelongitudearg);
}
elsif (defined $latitudearg and defined $longitudearg)
{
  $lat=convert_single($latitudearg);
  $long=convert_single($longitudearg);
}
else
{
  print "Error, you must define --latitude and --longitude or --coordinates\n\n";
  exit 1;
}


#define lmx string with known variables
my $lmx_contents = <<END
<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<lm:lmx xmlns:lm=\"http://www.nokia.com/schemas/location/landmarks/1/0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.nokia.com/schemas/location/landmarks/1/0/ lmx.xsd\">
	<lm:landmarkCollection>
		<lm:landmark>
			<lm:name>$name</lm:name>
			<lm:description>$desc</lm:description>
			<lm:coordinates>
				<lm:latitude>$lat</lm:latitude>
				<lm:longitude>$long</lm:longitude>
			</lm:coordinates>
			<lm:addressInfo>
				<lm:street></lm:street>
				<lm:postalCode></lm:postalCode>
				<lm:city>$city</lm:city>
				<lm:state>$state</lm:state>
				<lm:country>$country</lm:country>
				<lm:phoneNumber></lm:phoneNumber>
			</lm:addressInfo>
			<lm:category>
				<lm:name>Geocache Punkt</lm:name>
			</lm:category>
		</lm:landmark>
	</lm:landmarkCollection>
</lm:lmx>
END
;

$currtime=strftime("%Y-%m-%dT%TZ",localtime());
#define gpx string with known variables
my $gpx_contents = <<END
<?xml version="1.0" encoding="UTF-8"?>
<gpx
  version="1.0"
  creator="mkwaypoint Perl Script"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns="http://www.topografix.com/GPX/1/0"
  xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">
<time>$currtime</time>
<bounds minlat="$lat" minlon="$long" maxlat="$lat" maxlon="$long"/>
<wpt lat="$lat" lon="$long">
  <ele>0.000000</ele>
  <name>$name</name>
  <cmt>$desc</cmt>
  <desc>$desc</desc>
  <sym>Geocache</sym>
</wpt>
</gpx>
END
;


print "Lat: $lat\nLong: $long\n";

sub write_file
{
  $filename=shift;
  $contents=shift;
  $overwriteflag=shift;
  if (not -e $filename or $overwriteflag)
  {
    open($fh, ">$filename") or die("error: couldn't open file $filename");
    print $fh $contents;
    close $fh ;
    print "$filename written\n";
  }
  else
  {
    print "$filename exists, not overwriting unless you specify --overwrite\n";
  }
}

sub gpsbabel_transfer_file
{
  $contents=shift;
  open($fh, "| gpsbabel -i gpx -f - -o garmin -F usb:") or die("error: couldn't run gpsbabel");
  print $fh $contents;
  close $fh ;
  print "GPX transfered to GPS\n";
}

write_file($lmx_file, $lmx_contents, $overwriteflag) if $mklmx;
write_file($gpx_file, $gpx_contents, $overwriteflag) if $mkgpx;
gpsbabel_transfer_file($gpx_contents) if $transfer_gpx;


__END__

=head1 NAME 

mknokiawaypoint.pl

=head1 SYNOPSIS

Supply name, longitute and latitude as arguments and the script will create a .lmx Nokia-compatible WayPoint File which you can then send to your phone via bluetooth, usb or infrared.

You can abbreviate the options down to one char as long as they not ambigious

mknokiawaypoint.pl --coordinates "<coordinates>" "<Waypoint Name>"

=head1 OPTIONS

=over

=item B<--help>

    Displays Help Man Page
    
=item B<--mklmx>

    Create Nokia LMX Waypoint File

=item B<--mkgpx>

    Create GPX Waypoint File

=item B<--tfgpx>

    Transfer GPX to connected Garmin GPS

=item B<--latitude>

    Give Latitude in WGS84

=item B<--longitude>

    Give Longitude in WGS84

=item B<--coordinates>

    Give both Longitude and Latitude in one String in WGS84
    Degrees or Degrees and Minutes are accepted

=item B<--city>
    
    City Field of Waypoint

=item B<--state>

    State Field of Waypoint

=item B<--country>

    Country Field of Waypoint

=item B<--description>

    Description of WayPoint

=item B<--overwrite>

    Overwrite Waypoint File if it already exists

=back

=head1 EXAMPLES

    mknokiawaypoint.pl "Graz Top" --country Austria --city Graz  \
       --coord "N 47° 05.344 E 015° 23.120"   \
       --desc "Regular, D:2 T:2.5" --mkgpx --mklmx --tfgpx

    mknokiawaypoint.pl -o --country Germany --city Paderborn --state ""  \
        --coord "N 51° 42.538 E 008° 46569"  \
	"Unter Dampf No. #3 - Die alte UHSe" \
	--desc  "Das Eckige muss ins Runde." --tfgpx

    mknokiawaypoint.pl --coordinates "N 51° 43.212 E 008° 45.339" \ 
        --country Germany --city Paderborn --region "" \
	"The springs of Paderborn" --mklmx

=cut


