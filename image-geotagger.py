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
from xml.etree import ElementTree
import xml.sax
import csv
import datetime
import dateutil.parser as dt_parser
import ntpath
import time

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


def get_files(path, isdir):
    """
    Return a list of files, or directories.
    """
    list_of_files = []

    for item in os.listdir(path):
        item_path = os.path.abspath(os.path.join(path, item))

        if isdir:
            if os.path.isdir(item_path):
                list_of_files.append(item_path)
        else:
            if os.path.isfile(item_path):
                list_of_files.append(item_path)

    return list_of_files


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
        fh.seek(0)

        try:
            reader = csv.reader(fh)
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

    if file_type == 'file type is not correct':
        return False
    elif file_type == 'csv':
        # Parse exif csv file to dict list
        with open(log_path, 'rb') as log_file:
            reader = csv.DictReader(log_file)
            track_logs = list(reader)
            return track_logs
    else:
        with open(log_path, 'r') as gpxfile:
            gpxfile.seek(0)
            track_logs = []
            try:
                gpx = gpxpy.parse(gpxfile)
                for track in gpx.tracks:
                    for segment in track.segments:
                        for point in segment.points:
                            track_data = {
                                'GPS_DATETIME': point.time,
                                'Latitude': point.latitude,
                                'Longitude': point.longitude,
                            }
                            track_logs.append(track_data)
                return track_logs
            except Exception as e:
                return False


def get_geo_data_from_log(df_row, track_logs):
    """
    Find match geo data from log
    """
    origin_date = datetime.datetime.strptime(df_row['ORIGINAL_DATETIME'], '%Y:%m:%d %H:%M:%S')
    result = min(track_logs, key=lambda log: abs(log["GPS_DATETIME"].replace(tzinfo=None) - origin_date))
    return result


def discard_track_logs(df_images, discard_distance):
    """
    Discard next images which distance is less than discard setting values
    """
    df_images['LATITUDE_PREV'] = df_images['LATITUDE'].shift(1)
    df_images['LONGITUDE_PREV'] = df_images['LONGITUDE'].shift(1)
    df_images['DISTANCE'] = df_images.apply(
        lambda x: haversine(x['LONGITUDE'], x['LATITUDE'], x['LONGITUDE_PREV'], x['LATITUDE_PREV']), axis=1)
    df_images.iat[0, df_images.columns.get_loc('DISTANCE')] = 0

    df_images['NEXT_DISTANCE'] = df_images['DISTANCE'].shift(-1)
    df_images.iat[-1, df_images.columns.get_loc('NEXT_DISTANCE')] = 0

    df_filtered_images = df_images.query('DISTANCE <= {0} or NEXT_DISTANCE <= {1}'
                                         .format(discard_distance, discard_distance))

    return df_filtered_images


def normalise_track_logs(df_images, normalise_distance):
    """
    normalise images geo position which distance is less than normalise setting values
    """
    df_images['LATITUDE_PREV'] = df_images['LATITUDE'].shift(1)
    df_images['LONGITUDE_PREV'] = df_images['LONGITUDE'].shift(1)
    df_images['LATITUDE_NEXT'] = df_images['LATITUDE'].shift(-1)
    df_images['LONGITUDE_NEXT'] = df_images['LONGITUDE'].shift(-1)

    df_images['DISTANCE'] = df_images.apply(
        lambda x: haversine(x['LONGITUDE'], x['LATITUDE'], x['LONGITUDE_PREV'], x['LATITUDE_PREV']), axis=1)
    df_images.iat[0, df_images.columns.get_loc('DISTANCE')] = 0

    df_images['NEXT_DISTANCE'] = df_images['DISTANCE'].shift(-1)
    df_images.iat[-1, df_images.columns.get_loc('NEXT_DISTANCE')] = 0

    df_images['LATITUDE'] = df_images.apply(lambda x:
                                            (x['LATITUDE_PREV'] + x['LATITUDE_NEXT']) / 2
                                            if x['DISTANCE'] > normalise_distance and
                                               x['NEXT_DISTANCE'] > normalise_distance
                                            else x['LATITUDE'], axis=1)
    df_images['LONGITUDE'] = df_images.apply(lambda x:
                                            (x['LONGITUDE_PREV'] + x['LONGITUDE_NEXT']) / 2
                                            if x['DISTANCE'] > normalise_distance and
                                               x['NEXT_DISTANCE'] > normalise_distance
                                            else x['LONGITUDE'], axis=1)

    return df_images


def clean_up_new_files(output_photo_directory, list_of_files):
    '''
    As Exiftool creates a copy of the original image when processing,
    the new files are copied to the output directory,
    original files are renamed to original filename.
    '''

    print('Cleaning up old and new files...')
    if not os.path.isdir(os.path.abspath(output_photo_directory)):
        os.mkdir(os.path.abspath(output_photo_directory))

    for image in list_of_files:
        image_head, image_name = ntpath.split(image)
        try:
            os.rename(image, os.path.join(os.path.abspath(output_photo_directory),
                                          '{0}_calculated.{1}'.format(image_name.split('.')[0], image.split('.')[-1])))
            os.rename(os.path.join(os.path.abspath(image_head), '{0}_original'.format(image_name)), image)
        except PermissionError:
            print("Image {0} is still in use by Exiftool's process or being moved'."
                  " Waiting before moving it...".format(image_name))
            time.sleep(3)
            os.rename(image, os.path.join(os.path.abspath(output_photo_directory),
                                          '{0}_calculated.{1}'.format(image_name.split('.')[0], image.split('.')[-1])))
            os.rename(os.path.join(os.path.abspath(image_head), '{0}_original'.format(image_name)), image)

    print('Output files saved to {0}'.format(os.path.abspath(output_photo_directory)))


def geo_tagger(args):
    path = Path(__file__)
    input_photo_directory = os.path.abspath(args.input_path)
    log_path = os.path.abspath(args.gps_track_path)
    output_photo_directory = os.path.abspath(args.output_directory)
    mode = args.mode
    discard = int(args.discard)
    normalise = int(args.normalise)
    offset = int(args.offset)

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

    # Validate log file exist
    if not os.path.isfile(log_path):
        if os.path.isfile(os.path.join(path.parent.resolve(), log_path)):
            log_path = os.path.join(path.parent.resolve(), log_path)
        else:
            input('No valid input folder is given!\nInput folder {0} or {1} does not exist!'.format(
                os.path.abspath(log_path),
                os.path.abspath(os.path.join(path.parent.resolve(), log_path))))
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
    list_of_files = get_files(input_photo_directory, False)
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

    #########################
    # Work with the resulting image dataframe to filter by time discard or normalise
    track_logs = load_gps_track_log(log_path)

    if not track_logs:
        input("""GPS track log file is not correct or unsupported file.\n\nPress any key to quit...""")
        quit()

    # Apply offset to GPS DateTime
    if offset != 0:
        for track_log in track_logs:
            track_log['GPS_DATETIME'] = track_log['GPS_DATETIME'] + datetime.timedelta(0, offset)

    df_images[['GPS_DATETIME', 'LATITUDE', 'LONGITUDE']] = \
        df_images.apply(lambda x: get_geo_data_from_log(x, track_logs), axis=1, result_type='expand')

    if discard > 0:
        df_images = discard_track_logs(df_images, discard)
        if len(df_images) == 0:
            input("""All images has been discarded.\n\nPress any key to quit...""")
            quit()

    if normalise > 0:
        df_images = normalise_track_logs(df_images, normalise)           

    # For each image, write the GEO TAGS into EXIF
    print('Writing metadata to EXIF of qualified images...\n')
    with exiftool.ExifTool(win_shell=is_win_shell) as et:
        for row in df_images.iterrows():
            et.execute(bytes('-GPSTimeStamp={0}'.format(row[1]['GPS_DATETIME'].strftime("%H:%M:%S")), 'utf-8'),
                       bytes("{0}".format(row[1]['IMAGE_NAME']), 'utf-8'))
            et.execute(bytes('-GPSDateStamp={0}'.format(row[1]['GPS_DATETIME'].strftime("%Y:%m:%d")), 'utf-8'),
                       bytes("{0}".format(row[1]['IMAGE_NAME']), 'utf-8'))
            et.execute(bytes('-GPSLatitude={0}'.format(row[1]['LATITUDE']), 'utf-8'),
                       bytes("{0}".format(row[1]['IMAGE_NAME']), 'utf-8'))
            et.execute(bytes('-GPSLongitude={0}'.format(row[1]['LONGITUDE']), 'utf-8'),
                       bytes("{0}".format(row[1]['IMAGE_NAME']), 'utf-8'))

    clean_up_new_files(output_photo_directory, [image for image in df_images['IMAGE_NAME'].values])

    input('\nMetadata successfully added to images.\n\nPress any key to quit')
    quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Image GeoTagger metadata setter')

    parser.add_argument('input_path',
                        action='store',
                        help='Path to input image or directory of images.')

    parser.add_argument('gps_track_path',
                        action='store',
                        help='Path to GPS track log file.')

    parser.add_argument('-o', '--offset',
                        action='store',
                        dest='offset',
                        default=0,
                        help='Offset gps track times')

    parser.add_argument('-m', '--mode',
                        action='store',
                        default='missing',
                        dest='mode',
                        help='Image GeoTagger Mode')

    parser.add_argument('-d', '--discard',
                        action='store',
                        dest='discard',
                        default=0,
                        help='Discard images which distance in meter is less than parameter')

    parser.add_argument('-n', '--normalise',
                        action='store',
                        dest='normalise',
                        default=0,
                        help='')

    parser.add_argument('-e', '--exiftool-exec-path',
                        action='store',
                        default='No path specified',
                        dest='executable_path',
                        help='Optional: path to Exiftool executable.')

    parser.add_argument('output_directory',
                        action="store",
                        help='Path to output folder.')

    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s 1.0')

    args = parser.parse_args()

    if args.discard and args.normalise:
        input("""You can't use discard(-d) and normalise(-n) argument in same time.\n\nPress any key to quit...""")
        quit()

    geo_tagger(args)
