# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Author: hq@trekview.org
# Created: 2020-06-10
# Copyright: Trek View
# Licence: GNU AGPLv3
# -------------------------------------------------------------------------------

import os
import argparse
import sys
import math
from pathlib import Path
import xml.sax
import csv
import datetime
import ntpath

import pandas as pd
import gpxpy
from exiftool_custom import exiftool


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    https://github.com/trek-view/tourer/blob/latest/utils.py#L134
    """
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371

    distance = (c * r) * 1000

    return distance


def get_files(path):
    """
    Return a list of files, or directories.
    """
    list_of_files = []

    for p, r, files in os.walk(path):
        for file in files:
            list_of_files.append(os.path.join(p, file))

    return list_of_files


def clean_up_new_files(output_photo_directory, list_of_files):
    """
    As Exiftool creates a copy of the original image when processing,
    the new files are copied to the output directory,
    original files are renamed to original filename.
    """

    print('Cleaning up old and new files...')
    if not os.path.isdir(os.path.abspath(output_photo_directory)):
        os.mkdir(os.path.abspath(output_photo_directory))

    for image in list_of_files:
        image_head, image_name = ntpath.split(image)
        try:
            os.rename(image, os.path.join(os.path.abspath(output_photo_directory),
                                          '{0}.{1}'.format(image_name.split('.')[0], image.split('.')[-1])))
            os.rename(os.path.join(os.path.abspath(image_head), '{0}_original'.format(image_name)), image)
        except PermissionError:
            print("Image {0} is still in use by Exiftool's process or being moved'."
                  " Waiting before moving it...".format(image_name))

    print('Output files saved to {0}'.format(os.path.abspath(output_photo_directory)))


def filter_metadata(metadata, keys):
    """
    If metadata contains certain key values then return false
    """
    dict_metadata = metadata['METADATA']
    for key in keys:
        try:
            if dict_metadata[key]:
                return False
        except KeyError:
            pass
    return True


def parse_metadata(dfrow, keys):
    """
    get values in a metadata object
    """
    dict_metadata = dfrow['METADATA']
    values = []
    for key in keys:
        try:
            data = dict_metadata[key]
            values.append(data)
        except KeyError:
            print('\n\nAn image was encountered that did not have the required metadata.')
            print('Image: {0}'.format(dfrow['IMAGE_NAME']))
            print('Missing metadata key: {0}\n\n'.format(key.split(':')[-1]))
            input('Press any key to quit')
            quit()
    return values


def validate_file_type(path):
    """
    Check the file type is csv or xml.
    """
    with open(path, 'rb') as fh:
        try:
            xml.sax.parse(fh, xml.sax.ContentHandler())
            return 'xml'
        except:  # SAX' exceptions are not public
            pass

    try:
        reader = csv.reader(open(path, 'rb'))
        return 'csv'
    except csv.Error:
        pass

    return 'file type is not correct'


def load_gps_track_log(log_path):
    """
    load gps track log.
    support kml, gpx and exif csv file.
    """
    file_type = validate_file_type(log_path)
    track_logs = []
    loaded_points = 0
    removed_points = 0

    if file_type == 'file type is not correct':
        return False
    elif file_type == 'csv':
        # Parse exif csv file to dict list
        with open(log_path, 'r', encoding='utf8') as log_file:
            reader = csv.DictReader(log_file)
            for i in reader:
                date_time = i.get('GPSDateTime')
                latitude = i.get('GPSLatitude')
                longitude = i.get('GPSLongitude')
                altitude = i.get('GPSAltitude')
                if date_time and latitude and longitude:
                    new_date_time = datetime.datetime.strptime(date_time, '%Y:%m:%d %H:%M:%SZ')
                    i.update({
                        'GPS_DATETIME': new_date_time,
                        'Latitude': float(latitude),
                        'Longitude': float(longitude),
                        'Altitude': float(altitude) if altitude else None
                    })
                    track_logs.append(i)
                    loaded_points += 1
                else:
                    removed_points += 1
    else:
        with open(log_path, 'r') as gpxfile:
            gpxfile.seek(0)
            try:
                gpx = gpxpy.parse(gpxfile)
                for track in gpx.tracks:
                    for segment in track.segments:
                        for point in segment.points:
                            if point.time:
                                track_data = {
                                    'GPS_DATETIME': point.time,
                                    'Latitude': point.latitude,
                                    'Longitude': point.longitude,
                                    'Altitude': point.elevation
                                }
                                track_logs.append(track_data)
                                loaded_points += 1
                            else:
                                removed_points += 1
                            
            except Exception as e:
                return False
    print('Loaded Points : {} \n\nRemoved Points: {}'.format(loaded_points, removed_points))
    track_logs = sorted(track_logs, key=lambda t_log: t_log['GPS_DATETIME'])
    return track_logs


def get_geo_data_from_log(df_row, track_logs):
    """
    Find match geo data from log
    """
    if track_logs:
        track_idx = df_row.name
        if len(track_logs) > track_idx:
            current_track = track_logs[track_idx]
            altitude = current_track.get('Altitude')
            result = {
                'GPS_DATETIME': current_track.get('GPS_DATETIME'),
                'Latitude': current_track.get('Latitude'),
                'Longitude': current_track.get('Longitude'),
                'Altitude': altitude if altitude else df_row['METADATA'].get('Composite:GPSAltitude')
            }
            print("Image Original Date time is {0} and the Log time is {1}".format(
                df_row['ORIGINAL_DATETIME'], result['GPS_DATETIME'].strftime("%Y:%m:%d %H:%M:%S")))
        else:
            result = {
                'GPS_DATETIME': None,
                'Latitude': None,
                'Longitude': None,
                'Altitude': None
            }
            print("Can not set image: {} as track log are not enough to update.".format(df_row['IMAGE_NAME']))
    else:
        result = {
            'GPS_DATETIME': 0,
            'Latitude': df_row['METADATA'].get('Composite:GPSLatitude'),
            'Longitude': df_row['METADATA'].get('Composite:GPSLongitude'),
            'Altitude': df_row['METADATA'].get('Composite:GPSAltitude')
        }

    return result


def generate_new_fields(df_images):
    """
    Add new fields for calculate
    """
    df_images['LATITUDE_PREV'] = df_images['LATITUDE'].shift(1, fill_value=df_images['LATITUDE'].iloc[0])
    df_images['LONGITUDE_PREV'] = df_images['LONGITUDE'].shift(1, fill_value=df_images['LONGITUDE'].iloc[0])
    df_images['ALTITUDE_PREV'] = df_images['ALTITUDE'].shift(1, fill_value=df_images['ALTITUDE'].iloc[0])

    df_images['DISTANCE'] = df_images.apply(
        lambda x: haversine(x['LONGITUDE'], x['LATITUDE'], x['LONGITUDE_PREV'], x['LATITUDE_PREV']), axis=1)
    df_images.iat[0, df_images.columns.get_loc('DISTANCE')] = 0

    df_images['NEXT_DISTANCE'] = df_images['DISTANCE'].shift(-1, fill_value=0)
    return df_images


def discard_track_logs(df_images, discard_distance):
    """
    Discard next images which distance is less than discard setting values
    """
    df_images = generate_new_fields(df_images)

    df_filtered_images = df_images[(df_images['DISTANCE'] <= discard_distance) | (df_images['NEXT_DISTANCE'] <= discard_distance)]

    return df_filtered_images


def get_middle_point(df_row, normalise_distance):
    if df_row['DISTANCE'] > normalise_distance and df_row['NEXT_DISTANCE'] > normalise_distance:
        res = [
            (df_row[('{}_next'.format(key)).upper()] + df_row[('{}_prev'.format(key)).upper()]) / 2
            for key in ['LATITUDE', 'LONGITUDE']
        ]
        if df_row['ALTITUDE_PREV'] and df_row['ALTITUDE_NEXT']:
            res.append((df_row['ALTITUDE_NEXT'] + df_row['ALTITUDE_PREV']) / 2)
        else:
            res.append(None)
    else:
        res = [
            df_row[key]
            for key in ['LATITUDE', 'LONGITUDE', 'ALTITUDE']
        ]
    return pd.Series(res)


def normalise_track_logs(df_images, normalise_distance):
    """
    normalise images geo position which distance is less than normalise setting values
    """
    df_images = generate_new_fields(df_images)
    df_images_len = len(df_images.index) - 1
    df_images['LATITUDE_NEXT'] = df_images['LATITUDE'].shift(-1, fill_value=df_images['LATITUDE'][df_images_len])
    df_images['LONGITUDE_NEXT'] = df_images['LONGITUDE'].shift(-1, fill_value=df_images['LONGITUDE'][df_images_len])
    df_images['ALTITUDE_NEXT'] = df_images['ALTITUDE'].shift(-1, fill_value=df_images['ALTITUDE'][df_images_len])

    df_images[['LATITUDE', 'LONGITUDE', 'ALTITUDE']] = df_images.apply(lambda x: get_middle_point(x, normalise_distance), axis=1)

    return df_images


def geo_tagger(args):
    path = Path(__file__)
    input_photo_directory = os.path.abspath(args.input_path)
    log_path = os.path.abspath(args.track_log) if args.track_log else None
    output_photo_directory = os.path.abspath(args.output_directory)
    mode = args.mode.lower()
    discard = int(args.discard)
    normalise = int(args.normalise)

    is_win_shell = True

    # Validate input paths
    if not os.path.isdir(input_photo_directory):
        if os.path.isdir(os.path.join(path.parent.resolve(), input_photo_directory)):
            input_photo_directory = os.path.join(path.parent.resolve(), input_photo_directory)
            if not os.path.isdir(output_photo_directory):
                output_photo_directory = os.path.join(path.parent.resolve(), output_photo_directory)
        else:
            input('No valid input folder is given!\nInput folder {0} or {1} does not exist!'.format(
                os.path.abspath(input_photo_directory),
                os.path.abspath(os.path.join(path.parent.resolve(), input_photo_directory))))
            input('Press any key to continue')
            quit()

    print('The following input folder will be used:\n{0}'.format(input_photo_directory))
    print('The following output folder will be used:\n{0}'.format(output_photo_directory))

    # Often the exiftool.exe will not be in Windows's PATH
    if args.executable_path == 'No path specified':
        if 'win' in sys.platform and not 'darwin' in sys.platform:
            if os.path.isfile(os.path.join(path.parent.resolve(), 'exiftool.exe')):
                exiftool.executable = os.path.join(path.parent.resolve(), 'exiftool.exe')
            else:
                input("""Executing this script on Windows requires either the "-e" option
                        or store the exiftool.exe file in the working directory.\n\nPress any key to quit...""")
                quit()
        else:
            is_win_shell = False

    else:
        exiftool.executable = args.executable_path

    # Get files in directory
    list_of_files = get_files(input_photo_directory)
    print('{0} file(s) have been found in input directory'.format(len(list_of_files)))

    # Get metadata of each file in list_of_images
    print('Fetching metadata from all images....\n')
    with exiftool.ExifTool(win_shell=is_win_shell) as et:
        list_of_metadata = [{'IMAGE_NAME': image, 'METADATA': et.get_metadata(image)} for image in list_of_files]

    # filter the images based on mode setting.
    if mode == 'missing':
        keys = ['Composite:GPSDateTime', 'Composite:GPSLatitude', 'Composite:GPSLongitude', 'Composite:GPSAltitude',
                'EXIF:GPSDateStamp', 'EXIF:GPSTimeStamp']
        list_of_metadata = [metadata for metadata in list_of_metadata if filter_metadata(metadata, keys)]

        if len(list_of_metadata) == 0:
            input("""There isn't any missing tag file for geotagging.\n\nPress any key to quit...""")
            quit()

    # Create dataframe from list_of_metadata with image name in column and metadata in other column
    df_images = pd.DataFrame(list_of_metadata)
    keys = ['EXIF:DateTimeOriginal']
    df_images[['ORIGINAL_DATETIME']] = df_images.apply(
        lambda x: parse_metadata(x, keys), axis=1, result_type='expand')

    # Sort images
    df_images.sort_values('ORIGINAL_DATETIME', axis=0, ascending=True, inplace=True)
    df_images = df_images.reset_index(drop=True)

    track_logs = []
    if log_path:
        # Work with the resulting image dataframe to filter by time discard or normalise
        track_logs = load_gps_track_log(log_path)

    if not track_logs:
        print("""Track Logs are empty. So using geo values from image.""")

    df_images[['GPS_DATETIME', 'LATITUDE', 'LONGITUDE', 'ALTITUDE']] = \
        df_images.apply(lambda x: get_geo_data_from_log(x, track_logs), axis=1, result_type='expand')

    df_images = df_images.query('LATITUDE.notnull() or LONGITUDE.notnull()', engine='python')

    if not track_logs and len(df_images.index) == 0:
        input("""Latitude and longitude of all images are empty.\n\nPress any key to quit...""")
        quit()

    if discard > 0:
        df_images = discard_track_logs(df_images, discard)
        if len(df_images) == 0:
            input("""All images has been discarded.\n\nPress any key to quit...""")
            quit()

    elif normalise > 0:
        df_images = normalise_track_logs(df_images, normalise)

    # For each image, write the GEO TAGS into EXIF
    print('Writing metadata to EXIF of qualified images...\n')
    with exiftool.ExifTool(win_shell=is_win_shell) as et:
        for row in df_images.iterrows():
            if row[1]['GPS_DATETIME']:
                et.execute(bytes('-GPSTimeStamp={0}'.format(row[1]['GPS_DATETIME'].strftime("%H:%M:%S")), 'utf-8'),
                           bytes("{0}".format(row[1]['IMAGE_NAME']), 'utf-8'))
                et.execute(bytes('-GPSDateStamp={0}'.format(row[1]['GPS_DATETIME'].strftime("%Y:%m:%d")), 'utf-8'),
                           bytes("{0}".format(row[1]['IMAGE_NAME']), 'utf-8'))
            et.execute(bytes('-GPSLatitude={0}'.format(row[1]['LATITUDE']), 'utf-8'),
                       bytes("{0}".format(row[1]['IMAGE_NAME']), 'utf-8'))
            et.execute(bytes('-GPSLongitude={0}'.format(row[1]['LONGITUDE']), 'utf-8'),
                       bytes("{0}".format(row[1]['IMAGE_NAME']), 'utf-8'))

            if row[1]['ALTITUDE']:
                et.execute(bytes('-GPSAltitude={0}'.format(row[1]['ALTITUDE']), 'utf-8'),
                           bytes("{0}".format(row[1]['IMAGE_NAME']), 'utf-8'))

    clean_up_new_files(output_photo_directory, [image for image in df_images['IMAGE_NAME'].values])

    input('\nMetadata successfully added to images.\n\nPress any key to quit')
    quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Image GeoTagger metadata setter')

    parser.add_argument('input_path',
                        action='store',
                        help='Path to input image or directory of images.')

    parser.add_argument('-t', '--track-log',
                        action='store',
                        default=None,
                        help='Path to GPS track log file.')

    parser.add_argument('-m', '--mode',
                        action='store',
                        default='missing',
                        dest='mode',
                        help='Image GeoTagger Mode')

    parser.add_argument('-d', '--discard',
                        action='store',
                        dest='discard',
                        default=0,
                        help='Discard images which distance in meter is more than parameter')

    parser.add_argument('-n', '--normalise',
                        action='store',
                        dest='normalise',
                        default=0,
                        help='Normalise images which distance in meter is more than parameter')

    parser.add_argument('-e', '--exiftool-exec-path',
                        action='store',
                        default='No path specified',
                        dest='executable_path',
                        help='Optional: path to Exiftool executable.')

    parser.add_argument('output_directory',
                        action="store",
                        default="",
                        help='Path to output folder.')

    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s 1.0')

    input_args = parser.parse_args()

    if input_args.discard and input_args.normalise:
        input("""You can't use discard(-d) and normalise(-n) argument in same time.\n\nPress any key to quit...""")
        quit()

    geo_tagger(input_args)
