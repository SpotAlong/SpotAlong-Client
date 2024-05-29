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
import time
import logging
import os

import keyring
import requests
from appdirs import user_data_dir

from utils.constants import *
from utils.utils import convert_from_utc_timestamp


""" 
This file provides an easy way to work with the SpotAlong login api.
"""

sep = os.path.sep

data_dir = user_data_dir('SpotAlong', 'CriticalElement') + sep

__all__ = ('login', 'refresh', 'create_user', 'redeem_code')

logger = logging.getLogger(__name__)


def login():
    """
        This is a helper function that will return the access and refresh tokens as well as the timeout if login is
        succesful, otherwise it will return False, prompting manual login.
    """
    if not keyring.get_password('SpotAlong', 'auth_token'):
        return False
    else:
        if not keyring.get_password('SpotAlong', 'cookie_len'):
            return False
    try:
        auth_token_dict = json.loads(keyring.get_password('SpotAlong', 'auth_token'))
        access_token = auth_token_dict['access_token']
        refresh_token = auth_token_dict['refresh_token']
        timeout = auth_token_dict['timeout']
    except (json.JSONDecodeError, KeyError):
        return False
    if timeout < time.time():
        try:
            refresh_response = refresh(access_token, refresh_token)
        except (requests.RequestException, requests.ConnectionError) as e:
            logger.error('Could not connect to the server', exc_info=e)
            return False
        if refresh_response:
            return refresh_response
    eligible_url = BASE_URL + '/login/eligible'
    try:
        resp = requests.get(eligible_url, headers={'authorization': access_token}, timeout=15)
    except (requests.RequestException, requests.ConnectionError) as e:
        logger.error('Could not connect to the server', exc_info=e)
        return False
    if resp.status_code == 401 and resp.json()['reason'] == 'Timed out.':
        refresh_response = refresh(access_token, refresh_token)
        if refresh_response:
            return refresh_response
    elif resp.ok:
        return access_token, refresh_token, timeout
    return False


def refresh(access_token, refresh_token):
    """
        Helper function that will attempt to refresh an access token, and return False if unsuccessful.
    """
    refresh_url = BASE_URL + '/login/refresh'
    logger.info('Refreshing token...')
    try:
        refresh_resp = requests.post(refresh_url, headers={'authorization': access_token},
                                     data={'refresh_token': refresh_token}, timeout=15)
    except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
        logger.error('Could not connect to the server', exc_info=e)
        return False
    if refresh_resp.status_code != 200:
        try:
            logger.error(f'Recieved non-200 status code when refreshing the token: {refresh_resp.json()}')
        except json.JSONDecodeError:
            logger.error(f'Recieved non-200 status code when refreshing the token: {refresh_resp.status_code}')
        return False
    else:
        response = refresh_resp.json()
        token_dict = {'access_token': response['token'], 'refresh_token': response['refresh_token'],
                      'timeout': response['timeout']}
        keyring.set_password('SpotAlong', 'auth_token', json.dumps(token_dict))
        return response['token'], response['refresh_token'], response['timeout']


def create_user(emitter):
    """
        Helper function that will attempt to obtain a url for authentication, returning False if unsuccessful.
    """
    login_info = login()
    if login_info:
        emitter.append(['Login', login_info])
        return login_info
    login_url = BASE_URL + '/login'
    try:
        login_response = requests.get(login_url)
    except (requests.RequestException, requests.ConnectionError) as e:
        logger.error('Could not connect to the server', exc_info=e)
        emitter.append(['Failed', 'Failed'])  # ?
        return False
    if login_response.status_code == 200:
        timestamp = login_response.json()['expiry_timestamp']
        auth_url = login_response.json()['auth_url']
        emitter.append((auth_url, timestamp))
        return auth_url, timestamp
    emitter.append(False)
    return False


def redeem_code(code):
    """
        Helper function that will return the tokens and timeout needed for login, provided a SpotAlong login code.
    """
    redeem_url = BASE_URL + '/login/redeem_code'
    try:
        redeem_response = requests.get(redeem_url, headers={'code': code})
    except (requests.RequestException, requests.ConnectionError) as e:
        logger.error('Could not connect to the server', exc_info=e)
        return 'Failed'
    if redeem_response.status_code == 200:
        response = redeem_response.json()
        token_dict = {'access_token': response['access_token'], 'refresh_token': response['refresh_token'],
                      'timeout': response['timeout']}
        keyring.set_password('SpotAlong', 'auth_token', json.dumps(token_dict))
        return response['access_token'], response['refresh_token'], response['timeout']
    return False
