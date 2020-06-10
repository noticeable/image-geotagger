# Image Geotagger

## In one sentence

Command line Python script that 1) takes a series of timestamped images, 2) a timestamped GPS track log, 3) uses linear interpolation is used to determine the GPS position at the time of the image, 4) then writes geo meta tags are written to the image.

## Why we built this

Often GPS tags produced by 360 cameras can become corrupt in places, especially where line-of-sight to the sky is impeded (e.g. in a canyon).

GPS chips / software in cameras often does not have access to the same positioning data as other dedicated GPS devices (including smartphones where Google and Apple have access to mapping / location services). It is often the case a GPS track recorded by a phone will deliver significanly increased positioning accuracy in certain areas when compared to 360 cameras.

Finally, some cameras do not even offer GPS chips (or charge an added premium to users for a seperate product or subscription)/

As such, it is often advantageous to capture a secondary GPS track using a dedicated GPS logger (usually a phone) and then embed this date into the EXIF data of the captured images (by matching times in photo and GPS track).

[Exiftool already offers the ability to do basic geotagging](https://exiftool.org/geotag.html).

Image Geotagger is a wrapper around this functionality with additional features we find useful during the geotagging process (e.g time corrections)

## How it works

1. You create a GPS track and series of timelapse photos
2. You define any timestamp offsets and how the script should write date
3. The script compares timestamps between track and photo
4. The script emberd the GPS track data into the EXIF of the image
5. The script outputs a new panoramic photo with GPS metadata in the output directory defined

## Requirements

### OS Requirements

Works on Windows, Linux and MacOS.

### Software Requirements

* Python version 3.6+
* [exiftool](https://exiftool.org/)

### Image requirements

* Must have a `DateTimeOriginal` value.

_Note: this does not need to be accurate, as an offset can be defined when running the script._

### GPS Track Requirements

Currently supported GPS track log file formats:

* GPX
* NMEA (RMC, GGA, GLL and GSA sentences)
* KML
* IGC (glider format)
* Garmin XML and TCX
* Magellan eXplorist PMGNTRK
* Honeywell PTNTHPR
* Bramor gEO log
* Winplus Beacon .TXT
* GPS/IMU .CSV
* [ExifTool .CSV file](https://exiftool.org/geotag.html#CSVFormat)

## Quick start guide

### Aguements

**About modes**

* Overwrite: Will overwrite any existing geotags in image photo files with data from GPS log
* Missing: Will only add GPS tags to any photos in series that do no contain any geotags, and ignore photos with any existing geotags

**About time offset**

Sometimes the time on your GPS logger OR the camera itself might be incorrect. If you know by how far (number of seconds) the camera or GPS logger is incorrect.

Image Geotagger requires the time of the image file to be within 1 second of any time reported in the GPS track otherwise it will not geotag an image. Image Geotagger will always match the closest time to that reported in image against GPS track.

You can use an offset time (in seconds) to correct any bad times in clocks.

Offset should be specified in seconds. For example, if the time on the camera is incorrect by +1 hour (value reported is actually 1 hour ahead of actual capture time) the offset would be -3600. If it was 1 hour behind, the offset would be +3600.

### Format

```
python image-geotagger.py [IMAGE OR DIRECTORY OF IMAGES] [OPTIONAL TIME OFFSET] [GPS TRACK] [OPTIONAL TIME OFFSET] -mode [MODE] [OUTPUT PHOTO DIRECTORY]
```

### Examples



## Support 

We offer community support for all our software on our Campfire forum. [Ask a question or make a suggestion here](https://campfire.trekview.org/c/support/8).

## License

Image Geotagger is licensed under a [GNU AGPLv3 License](https://github.com/trek-view/image-geotagger/blob/master/LICENSE.txt).