# Image Geotagger

## In one sentence

Command line Python script that 1) takes a series of timestamped geotagged images (or a timestamped GPS track log if no geotags), 2) uses linear interpolation to determine the GPS position at the time of the image (if gps track), 3) removes or smooths outliers based on user defined value, and 4) writes upated geo meta tags to the image, if required, and outputs to a new directory.

## Why we built this

Often GPS tags produced by 360 cameras can become corrupt in places, especially where line-of-sight to the sky is impeded (e.g. in a canyon).

GPS chips / software in cameras often does not have access to the same positioning data as other dedicated GPS devices (including smartphones where Google and Apple have access to mapping / location services). It is often the case a GPS track recorded by a phone will deliver significanly increased positioning accuracy in certain areas when compared to 360 cameras.

Finally, some cameras do not even offer GPS chips (or charge an added premium to users for a seperate product or subscription)/

As such, it is often advantageous to capture a secondary GPS track using a dedicated GPS logger (usually a phone) and then embed this date into the EXIF data of the captured images (by matching times in photo and GPS track).

[Exiftool already offers the ability to do basic geotagging](https://exiftool.org/geotag.html). The ExifTool geotagging feature adds GPS tags to images based on data from a GPS track track file. The GPS track track file is loaded, and linear interpolation is used to determine the GPS position at the time of the image.

The problem is, exiftool does not account for accuracy of GPS and simply stitches gps points into photos based on matching times between gps track log and images.

To solve the problem of corrupted GPS points, Image Geotagger is a wrapper around exiftool functionality with additional features we use to normalise GPS paths where corruption has occured.

## How it works

1. You create a GPS track file (optional) and series of timelapse photos (geotagged if no gps track)
	- If GPS track:
	- The script compares timestamps between track and photos
	- The script embeds the GPS track data into the EXIF of the photos
2. The script orders images in ascending time order
3. You define any discard and / or normalisation requirements
4. Based on normalisation or discard values entered, the script writes new GPS data or discards images
4. The script outputs photos with new GPS metadata (if modified) and original photos (if unmodified) in the output directory defined

## Requirements

### OS Requirements

Works on Windows, Linux and MacOS.

### Software Requirements

* Python version 3.6+
* [Pandas](https://pandas.pydata.org/docs/): python -m pip install pandas
* [gpxpy](https://pypi.org/project/gpxpy/): python -m pip install gpxpy
* [exiftool](https://exiftool.org/)

### Image requirements

* Must have a `DateTimeOriginal` value.

### GPS Track Requirements

Currently supported GPS track track file formats:

* GPX
* [ExifTool .CSV file](https://exiftool.org/geotag.html#CSVFormat)
	- Essentially this is any `.csv` file that has `GPSDateTime`, `GPSAltitude` , `GPSLatitude` and `GPSLongitude` headers with corresponding column values.

## Quick start guide

### Arguments

* discard (`-d`)
	- value in meters: the script will order the files into `GPSDateTime` order and calculate distance (horizontal) between photos. If distance calculated is greater than discard value set between photos, these photos will be considered corrupt and discarded
* normalise (`-n`): 
	- value in meters. The script will order the files into `GPSDateTime` order and calculate distance (horizontal) between photos. If value greater than normalise value the script will find the midpoint between two photos either side in order and assign the midpoint as correct gps. Note for first and last photo it is impossible to calculate midpoint, hence if first / last connection exceeds normalise value set, these photos will be discarded.
* track log (`-t`) 
    - path of track file (can be csv, gpx).  
* mode (`-m`) 
	- `overwrite`: Will overwrite any existing geotags in image photo files with data from GPS log. If you are trying to rewrite gps tags that already exist in photos you must explicitly use this mode.
	- `missing` (default): Will only add GPS tags to any photos in series that do no contain any geotags, and ignore photos with any existing geotags

**About discard and normalise**

There can also be issues around accuracy of geotagged images regardless of whether a separate track file is used.

In this case, the user might wants to 1) discard gps / images that are clearly corrupt (significantly off the standard deviation of path) or 2) normalise the points so they form a more linear line (more accurate to real path).

![Discard photos](/readme-images/discard-viz.jpg)

In the case of discard, the first 3 connections (photo time 0 to photo time 1 to photo time 2) will be analysed against the `-d` value (meters). If both connection distance values are greater than `-d` (p1 to p2, and p2 to p3), then the middle photo is discarded. If only one distance value is grater than `-d`, then middle photo remains.

The script then considers then next trio of images. In Example 1 this would be P3, P4 and P5 (because P2 was discarded). In example 2 this would be P2, P3 and P4 (because P2 not discarded).

![Normalise photos](/readme-images/normalisation-viz.jpg)

Normalise works in a similar was to discard where the first 3 connections (photo time 0 to photo time 1 to photo time 2) will be analysed against the `-n` value

If both connection distance values are greater than `-n` (p1 to p2, and p2 to p3), then the middle photo is normalised. If only one distance value is greater than `-n`, then middle photo remains untouched.

Normalisation essentially finds the midpoint between first and last connections in a trio (p1 to p3) and then assigns the returned lat / lon values to the middle photo (p2). The altitude for the normalised photo is also adjusted to the vertical midpoint of p1 and p3 ((alt p1 + alt p2) / 2 = alt p3).

The script then considers then next trio of images. In both examples this would be P2, P3 and P4.

The script will copy any modified files with updated GPS and original files (which were not normalised) to the output folder.

Note, you can use `-d` OR `-n` arguments, but not both.

The limitation of both these methods means that if the first and last photos are corrupted they will not be discarded due to the fact the function only ever considers the middle point.

**About track log linear interpolation**

The script allows for significant time drift when stitching GPS track points into images.

By default, [exiftool will merge gps track to closest photo by time as long as track point and photo are withing 1800 seconds](https://exiftool.org/geotag.htm).

Generally it's better to ensure either your image times or GPS track log times are correct before using this script.

You can use either [Image Timestamper (image times)](https://github.com/trek-view/image-timestamper) or [GPS track timestamper (gps times)](https://github.com/trek-view/gps-track-timestamper) to fix before using Image Geotagger.

## Quick start

_Note for Windows users_

It is recommended you place `exiftool.exe` in the script directory. To do this, [download exiftool](https://exiftool.org/), extract the `.zip` file, and place `exiftool(-k).exe` in script directory.

If you want to run an existing exiftool install from outside the directory you can also add the path to the exiftool executable on the machine using either `--exiftool-exec-path` or `-e`.

_Note for MacOS / Unix users_

Remove the double quotes (`"`) around any directory path shown in the examples. For example `"OUTPUT_1"` becomes `OUTPUT_1`.

**Take a directory of images (`INPUT`) and discard (`-d`) any photos 5 meters from the track then output remaining images (to directory `OUTPUT_1`)**

```
python image-geotagger.py -m overwrite -d 5 "INPUT" "OUTPUT_1"
````

**Take a directory of images (`INPUT`) and normalise (`-n`) any photos 10 meters from the track then output (to directory `OUTPUT_2`)**

```
python image-geotagger.py -m overwrite -n 10 "INPUT" "OUTPUT_2"
```

**Take a directory of images (`INPUT`) and gpx track file (`GPS/track.gpx`) and stitch GPS points into images, overwriting (`-m overwrite`) any existing geodata then output (to directory `OUTPUT_3`)**

```
python image-geotagger.py -m overwrite "INPUT" "GPS/track.gpx" "OUTPUT_3"
```

**Take a directory of images (`INPUT`) and gpx track file (`GPS/track.gpx`) and stitch GPS points into images, only updating images with no exiting gps points (`-m missing`) then output (to directory `OUTPUT_4`)**

```
python image-geotagger.py -m missing "INPUT" "GPS/track.gpx" "OUTPUT_4"
```

**Take a directory of images (`INPUT`) and csv track file (`GPS/track.csv`) and stitch GPS points into images, overwriting (`-m overwrite`) any existing geodata and normalise (`-n`) any photos 10 meters from the track then output (to directory `OUTPUT_5`)**

```
python image-geotagger.py -m overwrite -n 5 "INPUT" "GPS/track.csv" "OUTPUT_5"
```

## Support 

We offer community support for all our software on our Campfire forum. [Ask a question or make a suggestion here](https://campfire.trekview.org/c/support/8).

## License

Image Geotagger is licensed under a [GNU AGPLv3 License](/LICENSE.txt).