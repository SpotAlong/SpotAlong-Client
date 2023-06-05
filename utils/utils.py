"""
Copyright (C) 2020-Present CriticalElement

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program at LICENSE.txt at the root of the source tree.
    If not, see <https://www.gnu.org/licenses/>.
"""

import os
import logging
import shutil
import time
import typing
import functools
import json
import datetime
from pathlib import Path
from threading import Thread

import requests
import numpy as np
from PIL.PyAccess import PyAccess
from colorthief import ColorThief
from appdirs import user_data_dir
from PIL import Image

from .constants import BASE_URL  # noqa

if typing.TYPE_CHECKING:
    from app import MainUI
    ui: typing.Optional[MainUI] = None


__all__ = ('extract_color', 'feather_image', 'download_album', 'clean_album_image_cache', 'convert_from_utc_timestamp')


data_dir = user_data_dir('SpotAlongTesting', 'CriticalElement') + '\\'
logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=None)
def extract_color(url):
    """
        Helper function that takes in url for album art and extracts the colors from the image.
    """
    if not url:
        return (40, 40, 40), (10, 10, 10), (255, 255, 255)
    album_id = url.split("/image/")[1]
    colors_cache = {}
    try:
        with open(data_dir + 'color_cache.json', 'r') as imagefile:
            colors_cache = json.load(imagefile)
    except json.JSONDecodeError:
        logger.warning('JSON color cache lookup failed, attempting to hit SpotAlong server cache...')
    if not colors_cache or album_id not in colors_cache:
        try:
            album_url = f'{BASE_URL}/cache/colors/{album_id}'
            resp = requests.get(album_url)
            assert resp.ok
            colors_cache = {album_url: resp.json()}
        except (Exception, AssertionError):
            logger.warning('SpotAlong server cache failed, extracting color manually...')
    if album_id in colors_cache:
        logger.info(f'Color extraction cache for {album_id} hit')
        return tuple(colors_cache[album_id][0]), tuple(colors_cache[album_id][1]), tuple(colors_cache[album_id][2])
    start = time.perf_counter()
    image = ColorThief(data_dir + f'partialalbum{url.split("/image/")[1]}.png')
    start2 = time.perf_counter()
    colors = image.get_palette(color_count=8)
    end2 = time.perf_counter()
    logger.info(f'Sub-color extraction 1: {end2 - start2}')
    brightness = np.mean([np.mean(items) for items in [np.mean(item) for item in colors]])
    if 122 < brightness < 133 or brightness < 110:
        dark = True
        dominant_color = [np.mean(items) for items in [np.mean(item) for item in colors]]
        dominant_color = colors[dominant_color.index(min(dominant_color))]
    elif brightness < 122:
        dark = True
        dominant_color = image.get_color()
    else:
        dark = False
        dominant_color = image.get_color()
    palette = colors
    dark_color = [color - 30 if not (color - 30) < 0 else 0 for color in dominant_color]
    if not dark and brightness < 140:
        text_color = [np.mean(items) for items in [np.mean(item) for item in palette]]
        text_color = palette[text_color.index(min(text_color))]
    else:
        text_color = max([max(color) - min(color) for color in palette])
        for color in palette:
            if max(color) - min(color) == text_color:
                text_color = color
    average = []
    for index, color in enumerate(text_color):
        average.append(abs(color - dominant_color[index]))
    if np.mean(average) < 40:
        text_color = [np.mean(items) for items in [np.mean(item) for item in colors]]
        text_color = colors[text_color.index(min(text_color))]
    average = []
    for index, color in enumerate(text_color):
        average.append(abs(color - dominant_color[index]))
    if np.mean(average) < 40:
        text_color = (255, 255, 255)
    end = time.perf_counter()
    logger.info(f'Color extraction time: {end - start}')
    colors_cache.update({album_id: [list(dominant_color), list(dark_color), list(text_color)]})
    with open(data_dir + 'color_cache.json', 'w') as imagefile:
        json.dump(colors_cache, imagefile, indent=4)
    return dominant_color, tuple(dark_color), text_color


def feather_image(url):
    """
        Helper function that feathers an image given the url.
    """
    if not url:
        url = 'None/image/None'
    if os.path.exists(data_dir + f'album{url.split("/image/")[1]}.png'):
        return
    start = time.perf_counter()
    RADIUS = 35

    im = Image.open(data_dir + f'partialalbum{url.split("/image/")[1]}.png')
    im = im.convert('RGBA')

    data: typing.Optional[PyAccess] = im.load()
    newdata = []
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            if x < RADIUS:
                newdata = list(data[x, y])
                newdata[3] = int(255 / RADIUS * x)
                data[x, y] = tuple(newdata)
            if im.size[0] - RADIUS < x:
                newdata = list(data[x, y])
                newdata[3] = int(255 / RADIUS * (abs(x - (im.size[0] - RADIUS) - RADIUS)))
                data[x, y] = tuple(newdata)
            if y < RADIUS:
                if newdata:
                    newdata[3] = int(min(255 / RADIUS * y, newdata[3]))
                    data[x, y] = tuple(newdata)
                else:
                    newdata = list(data[x, y])
                    newdata[3] = int(255 / RADIUS * y)
                    data[x, y] = tuple(newdata)
            if im.size[1] - RADIUS < y:
                if newdata:
                    newdata[3] = int(min(255 / RADIUS * (abs(y - (im.size[1] - RADIUS) - RADIUS)), newdata[3]))
                    data[x, y] = tuple(newdata)
                else:
                    newdata = list(data[x, y])
                    newdata[3] = int(255 / RADIUS * (abs(y - (im.size[1] - RADIUS) - RADIUS)))
                    data[x, y] = tuple(newdata)
            newdata = []

    im.save(data_dir + f'album{url.split("/image/")[1]}.png')
    end = time.perf_counter()
    logger.info(f'Feathering time {end - start}')


def download_album(url):
    """
        Helper function that downloads an album image given the url, and looks at the SpotAlong server cache for speed.
    """
    if url:
        id_ = url.split("/image/")[1]
        if not list(Path(data_dir).glob(f'partialalbum{id_}.png')):
            img_data = requests.get(url, timeout=5).content
            with open(data_dir + f'partialalbum{id_}.png', 'wb') as handler:
                handler.write(img_data)
            try:
                if os.path.exists(f'{data_dir}album{id_}.png'):
                    return
                album_url = f'{BASE_URL}/cache/album/{id_}'
                start = time.perf_counter()
                img_data = requests.get(album_url, timeout=5).content
                with open(data_dir + f'album{id_}.png', 'wb') as f:
                    f.write(img_data)
                    logger.info(f'Downloaded feathered image {id_}')
                    logger.info(time.perf_counter() - start)
                Thread(target=clean_album_image_cache, args=(url,)).start()
            except requests.exceptions.ConnectionError:
                logger.warning(f'Downloading of feathered image {id_} failed, feathering locally')
                return
    else:
        if not os.path.exists(data_dir + 'partialalbumNone.png'):
            shutil.copy(data_dir + 'unknown_album.png', data_dir + 'partialalbumNone.png')  # what the actual heck


def clean_album_image_cache(url=None):
    """
        This function will attempt to remove the oldest album images in order to stay under the album cache limit.
    """
    if not url:
        url = 'None/image/None'
    album_images = [file.stat().st_size for file in Path(data_dir).glob('*album*') if file.is_file()]
    album_images_size = sum(album_images) / 1000000
    while album_images_size > ui.albumcachelimit:
        album_images_created = [file for file in Path(data_dir).glob('*album*') if file.is_file()]
        created_time = sorted(album_images_created, key=lambda file: file.stat().st_ctime)
        created_time = sorted(created_time, key=lambda file: file.name, reverse=True)
        if len(created_time) > 1:
            if created_time[0].name == f'partialalbum{url.split("/image/")[1]}.png':
                delete_image = created_time[1]
            else:
                delete_image = created_time[0]
            logger.info(f'Album image {delete_image.name} has been deleted')
            delete_image_size = delete_image.stat().st_size / 1000000
            delete_image.unlink()
            if album_images_size - delete_image_size <= ui.albumcachelimit:
                return
        album_images = [file.stat().st_size for file in Path(data_dir).glob('*album*') if file.is_file()]
        album_images_size = sum(album_images) / 1000000


def convert_from_utc_timestamp(ts):
    """
        This function will take in a UTC timestamp and convert it to a local timestamp with the users' tz offset.
    """
    dt = datetime.datetime.fromtimestamp(ts)
    dt = dt.replace(tzinfo=datetime.timezone.utc)
    dt = dt.astimezone()
    return dt.timestamp()
