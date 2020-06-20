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

1. You create a GPS track file (optional) and series of timelapse photos (geotagges if no gps track)
2. If GPS track used, you define any timestamp offsets ([similar functionality to Image / Video timestamper](https://github.com/trek-view/image-video-timestamper))
3. You define any discard and / or normalisation requirements
4. The script compares timestamps between track and photo
5. The script embeds the GPS track data into the EXIF of the image and orders images in ascending time order
6. Based on normalisation or discard values entered, the script writes new GPS data or discards images
7. The script outputs a new panoramic photo with GPS metadata in the output directory defined


### Limitations / Considerations

**Estimations**





## Requirements

### OS Requirements

Works on Windows, Linux and MacOS.

### Software Requirements

* Python version 3.6+
* [exiftool](https://exiftool.org/)

### Image requirements

* Must have a `DateTimeOriginal` value.

### GPS Track Requirements

Currently supported GPS track log file formats:

* GPX
* [ExifTool .CSV file](https://exiftool.org/geotag.html#CSVFormat)

## Quick start guide

### Arguments

**About modes**

* -m mode
	- Overwrite: Will overwrite any existing geotags in image photo files with data from GPS log
	- Missing: Will only add GPS tags to any photos in series that do no contain any geotags, and ignore photos with any existing geotags
* -d discard
	- value in meters: the script will order the files into GPSDateTime order and calculate distance (horizontal) between photos. If distance calculated is greater than discard value set between photos, these photos will be considered corrupt and discarded
* -n normalise: 
	- value in meters. The script will order the files into GPSDateTime order and calculate distance (horizontal) between photos. If value greater than normalise value the script will find the midpoint between two photos either side in order and assign the midpoint as correct gps. Note for first and last photo it is impossible to calculate midpoint, hence if first / last connection exceeds normalise value set, these photos will be discarded.
* -o offset gps track times
	- value in seconds to offset each gps track timestamp. Can be either positive of negative.

**About discard and normalise**

There can also be issues around accuracy of geotagged images regardless of whether a separate track file is used. In this case, the user might wants to 1) discard gps / images that are clearly corrupt (significantly off the standard deviation of path) or 2) normalise the points so they form a more linear line.

![Discard photos](/readme-images/discard-viz.jpg)

In the case of discard, the first 3 connections (photo time 0 to photo time 1 to photo time 2) will be analysed against the -d value. If both connection distance values are greater than -d (p1 to p2, and p2 to p3), then the middle photo is discarded. If only one distance value is grater than -d, then middle photo remains.

The script then considers then next trio of images. In Example 1 this would be P3, P4 and P5 (because P2 was discarded). In example 2 this would be P2, P3 and P4 (because P2 not discarded)

![Normalise photos](/readme-images/normalisation-viz.jpg)

Normalise works in a similar was to discard where the first 3 connections (photo time 0 to photo time 1 to photo time 2) will be analysed against the -n value

Note, you can use -d or -n arguments, but not both. If both connection distance values are greater than -n (p1 to p2, and p2 to p3), then the middle photo is normalised.  If only one distance value is grater than -n, then middle photo remains untouched.

Normalisation essentially finds the midpoint between first and last connections in a trio (p1 to p3) and then assigns the returned lat / lon values to the middle photo (p2). The altitude for the normalised photo is also adjusted to the vertical midpoint of p1 and p3 ((alt p1 + alt p2) / 2 = alt p3).

The script then considers then next trio of images. In both examples this would be P2, P3 and P4.

**About time offset**

Sometimes the time on your GPS logger might be incorrect. If you know by how far (number of seconds) the GPS logger is incorrect you can correct it using a time offset.

Image Geotagger requires the time of the image file to be within 1 second of any time reported in the GPS track otherwise it will not geotag an image. Image Geotagger will always match the closest time to that reported in image against GPS track.

If the datetimeoriginal value of your photos is incorrect, you should use [Image / Video timestamper to fix](https://github.com/trek-view/image-video-timestamper).

You can use an offset time (in seconds) to correct any bad times in clocks for GPS timestamping.

Offset should be specified in seconds. For example, if the time on the GPS is incorrect by +1 hour (value reported is actually 1 hour ahead of actual capture time) the offset would be -3600. If it was 1 hour behind, the offset would be +3600.

### Format

```
python image-geotagger.py [IMAGE OR DIRECTORY OF IMAGES] [GPS TRACK] -o [OPTIONAL TIME OFFSET] -m [MODE] -n [METERS FOR NORMLISATION TO HAPPEN] [OUTPUT PHOTO DIRECTORY]
```

### Examples



## Support 

We offer community support for all our software on our Campfire forum. [Ask a question or make a suggestion here](https://campfire.trekview.org/c/support/8).

## License

Image Geotagger is licensed under a [GNU AGPLv3 License](https://github.com/trek-view/image-geotagger/blob/master/LICENSE.txt).