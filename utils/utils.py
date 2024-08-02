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

import math
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
from platformdirs import user_data_dir
from PIL import Image, ImageStat

from .constants import BASE_URL  # noqa

if typing.TYPE_CHECKING:
    from app import MainUI
    ui: typing.Optional[MainUI] = None


__all__ = ('extract_color', 'feather_image', 'download_album', 'clean_album_image_cache', 'convert_from_utc_timestamp')


data_dir = user_data_dir('SpotAlong', 'CriticalElement') + os.path.sep
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
            colors_cache.update({album_id: resp.json()})
            with open(data_dir + 'color_cache.json', 'w') as imagefile:
                json.dump(colors_cache, imagefile, indent=4)
        except (Exception, AssertionError):
            logger.warning('SpotAlong server cache failed, extracting color manually...')
    if album_id in colors_cache:
        logger.info(f'Color extraction cache for {album_id} hit')
        return tuple(colors_cache[album_id][0]), tuple(colors_cache[album_id][1]), tuple(colors_cache[album_id][2])
    start = time.perf_counter()
    filename = data_dir + f'partialalbum{url.split("/image/")[1]}.png'
    image = ColorThief(filename)
    colors = image.get_palette(8, 5)
    old_colors = colors.copy()
    srcimage = Image.open(filename)
    try:
        r, g, b = ImageStat.Stat(srcimage).rms
    except ValueError:
        r, g, b = 127, 127, 127
    brightness = math.sqrt(0.299 * r ** 2 + 0.587 * g ** 2 + 0.114 * b ** 2)
    dominant_color = colors[0]
    colors = colors[1:]
    nextavg = np.mean(colors[0])
    if nextavg < 20 or nextavg > 220:
        text_color = colors[0]
    else:
        color_vividness = [max(color) - min(color) for color in colors]
        mult_fact = 1.6
        for i in range(len(color_vividness)):
            color_vividness[i] *= mult_fact
            color_vividness[i] *= mult_fact
            mult_fact -= 0.2
        text_color = colors[color_vividness.index(max(color_vividness))]
    if brightness < 107 or (brightness < 121 and np.mean(dominant_color) > 140):
        if np.mean(dominant_color) - np.mean(text_color) > 20 or np.mean(dominant_color) > 140:
            if np.mean(text_color) < 50:
                dominant_color, text_color = text_color, dominant_color
            else:
                averages = [np.mean(c) for c in colors]
                index = averages.index(min(averages))
                dominant_color = colors[index]
    if brightness > 169:
        if np.mean(text_color) - np.mean(dominant_color) > 20:
            if np.mean(text_color) > 220:
                dominant_color, text_color = text_color, dominant_color
            else:
                averages = [np.mean(c) for c in colors]
                index = averages.index(max(averages))
                dominant_color = colors[index]
    dark_color = tuple([max(0, c - 30) for c in dominant_color])
    all_averages = [np.mean(c) for c in old_colors]

    def check_closeness(dominant, text):
        # returns True if the difference in rgb values is less than or equal to 20 for at least two color channels
        if sum([int(abs(dominant[col] - text[col]) <= 20) for col in range(3)]) >= 2:
            # checks that the other color channel is similar by 75
            return max([abs(dominant[col] - text[col]) for col in range(3)]) < 75
        return False

    if check_closeness(dominant_color, text_color):
        text_color = old_colors[all_averages.index(max(all_averages))]
    if check_closeness(dominant_color, text_color):
        text_color = old_colors[all_averages.index(min(all_averages))]
    if check_closeness(dominant_color, text_color):
        text_color = (255, 255, 255)
    if check_closeness(dominant_color, text_color):
        text_color = (0, 0, 0)
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
                req = requests.get(album_url, timeout=5)
                assert req.ok
                img_data = req.content
                with open(data_dir + f'album{id_}.png', 'wb') as f:
                    f.write(img_data)
                    logger.info(f'Downloaded feathered image {id_}')
                    logger.info(time.perf_counter() - start)
                Thread(target=clean_album_image_cache, args=(url,)).start()
            except (requests.exceptions.ConnectionError, AssertionError):
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
        dont_delete = ['unknown_album.png', 'albumNone.png', 'partialalbumNone.png']
        album_images_created = [file for file in Path(data_dir).glob('*album*') if file.is_file()
                                and file.name not in dont_delete]
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
