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

import json
import logging
import time

import requests
from appdirs import user_data_dir


__all__ = ('BASE_URL', 'REGULAR_BASE', 'VERSION')
logger = logging.getLogger(__name__)
data_dir = user_data_dir('SpotAlong', 'CriticalElement') + '\\'


try:
    if time.time() > 1722488400:
        try:
            text = requests.get('https://spotalong.github.io/url.json', timeout=5).text
            with open(f'{data_dir}url.json', 'w') as f:
                f.write(text)
        except Exception as exc:
            logger.warning('Arbitrary error occured when updating server url from lookup, reverting to defaults:',
                           exc_info=exc)

    with open(f'{data_dir}url.json', 'r') as f:
        urls = json.load(f)
        BASE_URL = urls['BASE_URL']
        REGULAR_BASE = urls['REGULAR_BASE']
except Exception as exc:
    logger.warning('Arbitrary error occurred when getting server url, reverting to defaults: ', exc_info=exc)
    BASE_URL = 'http://192.168.1.84:8800/api'
    REGULAR_BASE = 'http://192.168.1.84:8800/'

VERSION = '1.0.0'  # change this at your own risk (don't)
