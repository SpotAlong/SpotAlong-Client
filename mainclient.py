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
import random
import typing
import requests
import time
import gc
from io import StringIO
from inspect import signature

import keyring
import numpy as np
import socketio.exceptions
from colorthief import ColorThief
from socketio import Client
from appdirs import user_data_dir
from PyQt5 import QtWidgets, QtCore
from PIL import Image, ImageOps

from spotifyclient.spotifyclient import SpotifyClient
from spotifyclient.spotifyplayer import SpotifyPlayer
from spotifyclient.spotifysong import SpotifySong
from utils.constants import *
from utils.login import *
from utils.utils import clean_album_image_cache

logger = logging.getLogger(__name__)
stream_io = StringIO()
watcher = logging.StreamHandler(stream=stream_io)
watcher.setFormatter(logging.Formatter('%(message)s'))
watcher.setLevel(logging.INFO)

sep = os.path.sep

data_dir = user_data_dir('SpotAlong', 'CriticalElement') + sep


class MainClient:
    def __init__(self, access_token, refresh_token, timeout, progress_bar) -> None:
        """
            A class that represents a user's connection to Spotify and all the user's friends. This is the main
            class that drives the program.

            Parameters:
                access_token: The access token for the SpotAlong API.
                refresh_token: The refresh token for the SpotAlong API.
                timeout: The timeout for the SpotAlong API.
                progress_bar: The progress bar of the loading screen.

        """
        self.initialized = False
        self.initialized_friends = 0
        self.disconnected = False
        self.id = ''
        self.friends = {}
        self.friend_requests = {}
        self.outbound_friend_requests = {}
        self.friendstatus = {}
        self.spotifyclient: typing.Optional[SpotifyClient] = None
        self.mainstatus = None
        self.friendListener = False
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._timeout = timeout
        self.ui = None
        self.listening_friends = []
        self.listening_friends_time = {}
        self._next_in_queue = ''
        self._last_time_of_state = time.time()
        self._is_refreshing = False  # don't try to refresh the token twice simultaneously
        with open(data_dir + 'color_cache.json', 'r') as fp:
            self.album_cache = json.load(fp)
        with open(data_dir + 'profile_cache.json', 'r') as fp:
            self.profile_cache = json.load(fp)
        self.client = Client(reconnection=False)

        def connected():
            self.disconnected = False
            logger.info('Websocket connection established')

        def authorized(data=None):
            logger.info('Authorization successful')
            data['ex_data'] = {'status': data['status']}
            data.update({'ex_data': data})
            self.friend_code = data['friend_code']
            self.id = data['id']
            self.spotifyclient = SpotifyClient(self.id, self.friend_code, data)
            self.spotifyclient.last_song = data['ex_data']['last_track']
            self.spotifyclient.user_data = data['ex_data']
            self.spotifyclient.user_data.update({'status': data['ex_data']['status']})
            progress_bar.setValue(40)

        def disconnected():
            logger.error('Websocket has been disconnected')
            self.disconnected = True
            self.client.disconnect()

        def connect_error(message=None):
            if message.get('message', None) != 'Invalid credentials':
                logger.error(f'The websocket connection was terminated for the following reason: '
                             f'{message.get("message", None)}')
                if self.initialized and message.get('message') == 'Duplicate session detected':
                    self.disconnected = False
                    disconnect()
                else:
                    self.client.disconnect()
                    self.disconnected = message.get("message", None)
            elif message.get('message', None) == 'Invalid credentials':
                logger.error(f'The websocket connection was terminated for the following reason: '
                             f'{message.get("message", None)}')
                self.client.disconnect()
                refresh_resp = refresh(self._access_token, self._refresh_token)
                if refresh_resp:
                    self._access_token, self._refresh_token, self._timeout = refresh_resp
                    self.client.connect(REGULAR_BASE, headers={'authorization': self._access_token, 'version': VERSION},
                                        namespaces=['/api/authorization'])
                    self.client.start_background_task(self.client.wait)
                    self.client.start_background_task(self.check_logs)
                    logger.info('Websocket reconnection successful')
                    return
                else:
                    self.disconnected = message.get('message', None)

        def disconnect():
            if self.disconnected:
                return
            self.disconnected = True
            try:
                if self.ui.listentofriends.spotifylistener:
                    self.ui.listentofriends.spotifylistener.end(no_log=True)
            except socketio.exceptions.SocketIOError as _exc:
                logger.error('An error occured while trying to end the listening along session: ', exc_info=_exc)
            self.client.disconnect()
            self.listening_friends = []
            self.listening_friends_time = {}
            QtCore.QTimer.singleShot(0, self.ui.worker2.update_friend_statuses)
            if self.ui.active_dialog:
                if self.ui.active_dialog.error and "playback controller" in self.ui.active_dialog.label_2.text():
                    self.ui.active_dialog.pushButton_2.click()
            logger.error('A connection error has occured')
            if self.initialized:
                self.client.sleep(2)
                logger.info('Reconnecting...')
                while self.disconnected:
                    try:
                        self.client.disconnect()
                        QtCore.QTimer.singleShot(0, self.ui.disconnect_overlay.show)
                        self.client = Client(False, logger=True)
                        add_event_listeners()
                        self.client.connect(REGULAR_BASE, headers={'authorization': self._access_token,
                                                                   'version': VERSION},
                                            namespaces=['/api/authorization'])
                        logger.info('Websocket reconnection successful')
                        self.spotifyplayer.attempt_reconnect_time = 0
                        self.client.start_background_task(self.client.wait)
                        self.client.start_background_task(self.check_logs)
                        QtCore.QTimer.singleShot(0, self.ui.disconnect_overlay.hide)
                        return
                    except socketio.exceptions.ConnectionError as ex:
                        logger.error('A connection error occured while the websocket connection was reconnecting, '
                                     'retrying in 5 seconds: ', exc_info=ex)
                        self.client.disconnect()
                        self.client.sleep(5)

        def get_friends(data=None):
            if data:
                for friend in data:
                    friend.update({'ex_data': friend})
                    self.friends.update({friend['id']: SpotifyClient(friend['id'], friend['friend_code'], friend)})
            progress_bar.setValue(45)

        def friend_requests(data=None):
            for request_id in data:
                self.friend_requests.update({request_id: data[request_id]})
            progress_bar.setValue(50)

        def outbound_friend_requests(data=None):
            for request_id in data:
                self.outbound_friend_requests.update({request_id: data[request_id]})

        def song_update(data=None):

            def cache_album(data_):
                if data_.get('album_colors', None):
                    url = data_['item']['album']['images'][0]['url']
                    id_ = url.split('/image/')[1]
                    if id_ not in self.album_cache:
                        self.album_cache.update({id_: data_['album_colors']})
                        with open(data_dir + 'color_cache.json', 'r') as cachef:
                            cache = json.load(cachef)
                            cache.update({id_: data_['album_colors']})
                        with open(data_dir + 'color_cache.json', 'w') as cachef:
                            json.dump(cache, cachef, indent=4)
                        if not os.path.exists(data_dir + f'album{id_}.png'):
                            try:
                                img = requests.get(data_['album_img_url'], timeout=5)
                            except requests.exceptions.ConnectionError:
                                logger.warning(f'Downloading of feathered image '
                                               f'{data_["album_img_url"].split("/album/")[1]} failed, '
                                               f'feathering locally')
                                return
                            if img.status_code == 200:
                                with open(data_dir + f'album{id_}.png', 'wb') as f:
                                    f.write(img.content)
                                    logger.info(f'Downloaded feathered image {id_}')
                                    clean_album_image_cache(url)
                    elif id_ in self.album_cache and data_['album_colors'] != self.album_cache[id_]:
                        self.album_cache.pop(id_)
                        with open(data_dir + 'color_cache.json', 'w') as cachef:
                            json.dump(self.album_cache, cachef, indent=4)

            while not self.spotifyclient:
                time.sleep(0.1)
            if data:
                if data['ex_data']['id'] == self.id:
                    actual_data = None if data.get('none') else data
                    cache_album(data)
                    self.spotifyclient.song_data = actual_data
                    self.spotifyclient.last_song = data['ex_data']['last_track']
                    self.spotifyclient.user_data = data['ex_data']
                    self.spotifyclient.user_data.update({'status': data['ex_data']['status']})
                else:
                    actual_data = None if data.get('none') else data
                    self.friends[data['ex_data']['id']].song_data = actual_data
                    cache_album(data)
                    self.friends[data['ex_data']['id']].last_song = data['ex_data']['last_track']
                    self.friends[data['ex_data']['id']].user_data = data['ex_data']
                    self.friends[data['ex_data']['id']].user_data.update({'status': data['ex_data']['status']})

        def cache_profile(data_):
            if data_.get('profile_colors', None):
                id_ = data_['id']
                if self.profile_cache.get(id_, None) != data_['profile_colors']:
                    self.profile_cache.update({id_: data_['profile_colors']})
                    with open(data_dir + 'profile_cache.json', 'r') as cachef:
                        cache = json.load(cachef)
                        cache.update({id_: data_['profile_colors']})
                    with open(data_dir + 'profile_cache.json', 'w') as cachef:
                        json.dump(cache, cachef, indent=4)
                    if not os.path.exists(data_dir + f'icon{id_}.png'):
                        img = requests.get(data_['profile_img_url'], timeout=5)
                        if img.status_code == 200:
                            with open(data_dir + f'icon{id_}.png', 'wb') as f:
                                f.write(img.content)
                    return
                return
            try:
                id_ = data_['id']
                rand = random.randint(0, 10000)
                if data_.get('images', None):
                    url = data_['images'][-1]['url']
                    img_data = requests.get(url, timeout=5).content
                    with open(data_dir + f'tempicon{rand}{id_}.png', 'wb') as handler:
                        handler.write(img_data)
                else:
                    image = Image.open(data_dir + 'default_user.png').resize((200, 200))
                    image.save(data_dir + f'tempicon{rand}{id_}.png')
                mask = Image.open(data_dir + 'mask.png').convert('L')
                mask = mask.resize((200, 200))
                im = Image.open(data_dir + f'tempicon{rand}{id_}.png').convert('RGBA')
                output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
                output.putalpha(mask)
                output.resize((200, 200))
                try:
                    os.remove(data_dir + f'tempicon{rand}{id_}.png')
                except (FileNotFoundError, OSError, PermissionError):
                    pass
                output.save(data_dir + f'icon{id_}.png')
                with open(data_dir + 'profile_cache.json') as imagefile:
                    self.profile_cache = json.load(imagefile)
                image = ColorThief(data_dir + f'icon{id_}.png')
                dominant_color = image.get_color(quality=1)
                dark_color = [color - 30 if not (color - 30) < 0 else 0 for color in dominant_color]
                if np.average(dominant_color) > 200:
                    text_color = [0, 0, 0]
                else:
                    text_color = [255, 255, 255]
                with open(data_dir + 'profile_cache.json', 'w') as imagefile:
                    self.profile_cache.update({id_: [list(dominant_color), dark_color, text_color]})
                    json.dump(self.profile_cache, imagefile, indent=4)
            except (FileNotFoundError, OSError, PermissionError):
                pass

        def user_update(data=None):
            if data:
                if data['ex_data']['id'] == self.id:
                    cache_profile(data['ex_data'])
                    self.spotifyclient.user_data = data
                    self.spotifyclient.user_data['status'] = data['ex_data']['status']
                    self.spotifyclient.user_update()
                else:
                    cache_profile(data['ex_data'])
                    self.friends[data['ex_data']['id']].user_data = data
                    self.friends[data['ex_data']['id']].user_update()
                    self.initialized_friends += 1
                if self.initialized_friends == len(self.friends):
                    self.initialized = True

        def new_request(data):
            self.friend_requests.update(data)

        def remove_request(data):
            self.friend_requests.pop(data, None)
            self.outbound_friend_requests.pop(data, None)

        def new_outbound_request(data):
            self.outbound_friend_requests.update(data)

        def new_friend(data):
            self.friends.update({data['id']: SpotifyClient(data['id'], data['friend_code'], data)})
            text = f'{data["display_name"]} is now your friend.'
            self.ui.show_snack_bar_threadsafe(text, fallback_title='New Friend', fallback_text=text)

        def remove_friend(data):
            self.friends.pop(data['id'], None)

        def settings(data):
            self.song_broadcast = int(not data['privacy'])

        def start_listening(data):
            if data not in self.listening_friends:
                self.listening_friends.append(data)
                if len(self.listening_friends) == 1:
                    QtCore.QTimer.singleShot(0, self.ui.timer.start)
                self.listening_friends_time[data] = time.time()
                QtCore.QTimer.singleShot(0, self.ui.worker2.update_friend_statuses)
                text = f'{self.friendstatus[data].clientusername} started listening along to you.'
                self.ui.show_snack_bar_threadsafe(text, fallback_title='Listening Along', fallback_text=text)
                self.send_next_for_listening(force=True)

        def end_listening(data):
            try:
                self.listening_friends.pop(self.listening_friends.index(data))
                self.listening_friends_time.pop(data)
                if data in self.friendstatus:
                    text = f'{self.friendstatus[data].clientusername} stopped listening along to you.'
                    self.ui.show_snack_bar_threadsafe(text, fallback_title='Listening Along', fallback_text=text)
            except ValueError:
                pass
            if len(self.listening_friends) == 0:
                QtCore.QTimer.singleShot(0, self.ui.timer.stop)
            QtCore.QTimer.singleShot(0, self.ui.worker2.update_friend_statuses)

        def add_to_queue(data):
            if self.spotifyplayer.queue and self.spotifyplayer.queue[0]['uri'] == data:
                return
            try:
                assert self.mainstatus.duration / 1000 - self.mainstatus.progress < 3
                time.sleep(3)
            except (AssertionError, TypeError):
                pass
            self.spotifyplayer.command(self.spotifyplayer.clear_queue())
            try:
                self.spotifyplayer.command(self.spotifyplayer.add_to_queue(data.split(':')[2]))
            except IndexError:
                pass  # an invalid uri was attempted to be added to the queue, ignore

        def recieve_state(data):
            try:
                recieve_state_cmd(data)
            except Exception as ex:
                logger.warning('An error occured while trying to change the player state: ', exc_info=ex)
            finally:
                self.ui.listentofriends.spotifylistener.external_handle -= 1

        def recieve_state_cmd(data):
            self.ui.listentofriends.spotifylistener.external_handle += 1
            if self.spotifyplayer.playing != data['is_playing']:
                if self.spotifyplayer.playing:
                    self.spotifyplayer.command(self.spotifyplayer.pause)
                else:
                    self.spotifyplayer.command(self.spotifyplayer.resume)
            if self.spotifyplayer.looping != data['looping']:
                lookup = {'track': self.spotifyplayer.repeating_track, 'context': self.spotifyplayer.repeating_context,
                          'off': self.spotifyplayer.no_repeat}
                self.spotifyplayer.command(lookup[data['looping']])
            song_id = ''
            if self.spotifyplayer.player_state:
                if self.spotifyplayer.player_state.get('track'):
                    if 'track' in self.spotifyplayer.player_state['track']['uri']:
                        song_id = self.spotifyplayer.player_state['track']['uri'].split(':')[-1]
            if not song_id:
                song_id = self.mainstatus.songid
            if song_id == data['songid']:
                if abs(self.spotifyplayer.get_position() - data['progress']) > 3:
                    self.spotifyplayer.command(self.spotifyplayer.seek_to(data['progress'] * 1000))
            else:
                duration = self.mainstatus.duration if self.mainstatus.duration else 10 ** 8
                progress = self.mainstatus.progress if self.mainstatus.progress else 0
                if duration / 1000 - progress < 3:
                    try:
                        assert self.spotifyplayer.queue[0]['uri'].split(':')[2] == data['songid']
                        time.sleep(3)
                    except (AssertionError, IndexError):
                        self.spotifyplayer.command(self.spotifyplayer.play(data['songid']))
                else:
                    self.spotifyplayer.command(self.spotifyplayer.play(data['songid']))
            time.sleep(2)

        def add_event_listeners():
            self.client.on('connect', connected, namespace='/api/authorization')
            self.client.on('Authorized', authorized, namespace='/api/authorization')
            self.client.on('disconnect_user', disconnected, namespace='/api/authorization')
            self.client.on('connect_error', connect_error, namespace='/api/authorization')
            self.client.on('disconnect', disconnect, namespace='/api/authorization')
            self.client.on('friend_list', get_friends, namespace='/api/authorization')
            self.client.on('friend_requests', friend_requests, namespace='/api/authorization')
            self.client.on('outbound_friend_requests', outbound_friend_requests, namespace='/api/authorization')
            self.client.on('song_update', song_update, namespace='/api/authorization')
            self.client.on('user_update', user_update, namespace='/api/authorization')
            self.client.on('new_request', new_request, namespace='/api/authorization')
            self.client.on('remove_request', remove_request, namespace='/api/authorization')
            self.client.on('new_outbound_request', new_outbound_request, namespace='/api/authorization')
            self.client.on('new_friend', new_friend, namespace='/api/authorization')
            self.client.on('remove_friend', remove_friend, namespace='/api/authorization')
            self.client.on('settings', settings, namespace='/api/authorization')
            self.client.on('start_listening_from_user', start_listening, namespace='/api/authorization')
            self.client.on('end_listening_from_user', end_listening, namespace='/api/authorization')
            self.client.on('add_to_queue', add_to_queue, namespace='/api/authorization')
            self.client.on('listening_state', recieve_state, namespace='/api/authorization')

        try:
            cookie_num = int(keyring.get_password('SpotAlong', 'cookie_len'))
            cookie = ''.join([keyring.get_password('SpotAlong', 'cookie' + str(i)) for i in range(cookie_num)])
            self.spotifyplayer = SpotifyPlayer(cookie_str=cookie)
            self.spotifyplayer.add_event_reciever(self.send_next_for_listening)
            self.spotifyplayer.add_event_reciever(self.send_state_for_listening)
        except Exception as e:
            logger.error('SpotifyPlayer failed to create: ', exc_info=e)
            self.spotifyplayer = None
        progress_bar.setValue(10)
        add_event_listeners()
        try:
            self.client.connect(REGULAR_BASE, headers={'authorization': access_token, 'version': VERSION},
                                namespaces=['/api/authorization'])
            self.client.start_background_task(self.client.wait)
            self.client.start_background_task(self.check_logs)
        except Exception as exc:
            logger.error('An error occured during the websocket connection process: ', exc_info=exc)
            # this gets handled elsewhere better
        progress_bar.setValue(30)

    def invoke_request(self, url, data, request_type='GET', callback=lambda _=None: None, failed=lambda: None,
                       timeout=5):
        try:
            while self._is_refreshing:
                time.sleep(0.1)
            if request_type in ['GET', 'POST', 'DELETE']:
                if time.time() > self._timeout:
                    self._is_refreshing = True
                    refresh_resp = refresh(self._access_token, self._refresh_token)
                    self._is_refreshing = False
                    if refresh_resp:
                        self._access_token, self._refresh_token, self._timeout = refresh_resp
                    else:
                        logger.critical('An error occured while trying to refresh the authorization token, exiting.')
                        self.quit(401)
                request_type = request_type.lower()
                resp = getattr(requests, request_type)(url, data=data, headers={'authorization': self._access_token},
                                                       timeout=timeout)
                if resp.status_code == 401 and resp.json()['reason'] == 'Unauthorized':
                    resp = requests.get(BASE_URL + '/login/eligible', headers={'authorization': self._access_token},
                                        timeout=timeout)
                    if resp.status_code == 401 and resp.json()['reason'] == 'Timed out.':
                        while self._is_refreshing:
                            time.sleep(0.1)
                        self._is_refreshing = True
                        refresh_resp = refresh(self._access_token, self._refresh_token)
                        self._is_refreshing = False
                        if refresh_resp:
                            self._access_token, self._refresh_token, self._timeout = refresh_resp
                        else:
                            logger.critical(
                                'An error occured while trying to refresh the authorization token, exiting.')
                            self.quit(401)
                    else:
                        logger.critical(f'A critical error occured with authorization, exiting: {resp.json()}')
                        self.quit(401)
                    resp = getattr(requests, request_type)(url, data=data,
                                                           headers={'authorization': self._access_token},
                                                           timeout=timeout)
                    func = signature(callback)
                    if len(func.parameters) > 0:
                        callback(resp)
                    else:
                        callback()
                    return resp
                elif not resp.ok:
                    logger.error(f'An error occured while invoking request to {url}: {resp.json()}')
                    failed()
                else:
                    func = signature(callback)
                    if len(func.parameters) > 0:
                        callback(resp)
                    else:
                        callback()
                    return resp
        except requests.RequestException as req_exc:
            logger.error(f'An error occured while invoking request to {url}: ', exc_info=req_exc)
            failed()

    def quit(self, code):
        try:
            if self.ui:
                if code == 0:
                    self.ui.stop_all_fast()
                else:
                    self.ui.stop_all()
        except Exception as exc:
            logger.error('An error occured while trying to quit: ', exc_info=exc)
        if self.spotifyplayer:
            self.spotifyplayer.disconnect()
        self.disconnected = True
        self.client.disconnect()
        QtWidgets.QApplication.setQuitOnLastWindowClosed(True)
        QtWidgets.QApplication.exit(code)
        gc.collect()
        if code < 0:
            os._exit(code)  # noqa

    def send_queue_for_caching(self):
        try:
            if not self.spotifyplayer or self.spotifyplayer.disconnected:
                return
            queue = {'queue': json.dumps(self.spotifyplayer.queue)}
            self.invoke_request(BASE_URL + '/cache/precache', queue, request_type='POST', timeout=15)
        except Exception as exc:
            logger.warning('An error occured while uploading the queue to cache, continuing normally: ',
                           exc_info=exc)

    def send_next_for_listening(self, force=False):
        if not self.listening_friends:
            return
        try:
            if not self.spotifyplayer or self.spotifyplayer.disconnected:
                return
            song_uri = ''
            for song_dict in self.spotifyplayer.queue:
                if 'track' in song_dict['uri']:
                    song_uri = song_dict['uri']
                    break
            if not song_uri:
                return
            if self._next_in_queue == song_uri and not force:
                return
            self._next_in_queue = song_uri
            self.client.emit('upload_precache', song_uri, namespace='/api/authorization')
        except Exception as exc:
            logger.warning('An error occured while uploading the queue for the song listening cache, continuing: ',
                           exc_info=exc)

    def send_state_for_listening(self):
        if not self.listening_friends or not self.spotifyplayer:
            return
        try:
            if self.spotifyplayer.disconnected or time.time() - self._last_time_of_state < 0.2:
                return
            self._last_time_of_state = time.time()
            songid = self.spotifyplayer.player_state['track']['uri'].split(':')[2]
            state = {'songid': songid, 'progress': self.spotifyplayer.get_position(),
                     'is_playing': self.spotifyplayer.playing, 'looping': self.spotifyplayer.looping}
            self.client.emit('send_current_state', state, namespace='/api/authorization')
        except Exception as exc:
            logger.warning('An error occured while uploading the listening state, continuing: ',
                           exc_info=exc)

    def check_logs(self):
        while True:
            time.sleep(1)
            value = stream_io.getvalue().splitlines()
            if value and value[-1] == 'packet queue is empty, aborting':
                self.client.disconnect()
                return

    def __getattribute__(self, item):
        if item == 'mainstatus':
            song = self.spotifyclient.spotifysong()
            return song if song else SpotifySong()
        elif item == 'friendstatus':
            songs = {id_: val.spotifysong() for id_, val in self.friends.items()}
            return {id_: val if val else SpotifySong() for id_, val in songs.items()}
        else:
            return super().__getattribute__(item)
