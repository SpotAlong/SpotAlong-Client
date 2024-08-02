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
import os

from platformdirs import user_data_dir

sep = os.path.sep

__all__ = ('BASE_URL', 'REGULAR_BASE', 'VERSION')
logger = logging.getLogger(__name__)
data_dir = user_data_dir('SpotAlong', 'CriticalElement') + sep


try:
    edit = False
    with open(f'{data_dir}url.json', 'r') as f:
        urls = json.load(f)
        BASE_URL = urls['BASE_URL']
        REGULAR_BASE = urls['REGULAR_BASE']
        if BASE_URL == 'https://spotalong-tj6cy.ondigitalocean.app/api':
            BASE_URL = 'https://spotalong.herokuapp.com/api'
            REGULAR_BASE = 'https://spotalong.herokuapp.com/'
            urls['BASE_URL'] = BASE_URL
            urls['REGULAR_BASE'] = REGULAR_BASE
            edit = True
    if edit:
        with open(f'{data_dir}url.json', 'w') as f:
            json.dump(urls, f)
except Exception as exc:
    logger.warning('Arbitrary error occurred when getting server url, reverting to defaults: ', exc_info=exc)
    BASE_URL = 'https://spotalong.herokuapp.com/api'
    REGULAR_BASE = 'https://spotalong.herokuapp.com/'

VERSION = '1.0.2'  # change this at your own risk (don't)
