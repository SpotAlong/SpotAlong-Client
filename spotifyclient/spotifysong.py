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

import typing
import datetime


class SpotifySong:
    def __init__(self,
                 songname: typing.Optional[str] = '',
                 songid: typing.Optional[str] = None,
                 songlink: typing.Optional[str] = None,
                 contexttype: typing.Optional[str] = None,
                 contextdata: typing.Optional[str] = None,
                 contexturl: typing.Optional[str] = None,
                 progress: typing.Optional[float] = None,
                 duration: typing.Optional[int] = None,
                 albumname: typing.Optional[str] = '',
                 albumlink: typing.Optional[str] = None,
                 albumimagelink: typing.Optional[str] = None,
                 song_authors_urls: typing.Optional[list] = None,
                 song_authors: typing.Optional[list] = None,
                 is_playing: typing.Optional[bool] = False,
                 playing_type: typing.Optional[str] = False,
                 clientusername: typing.Optional[str] = None,
                 clientavatar: typing.Optional[str] = None,
                 client_id: typing.Optional[str] = None,
                 friend_code: typing.Optional[str] = None,
                 playing_status: typing.Optional[str] = None,
                 last_song: typing.Optional[dict] = None):
        """
            A class that represents the user's playing track, plus data about the user.

            Parameters:
                songname (str) (optional): The song name.
                songlink (str) (optional): The song link.
                songid (str) (optional): The song id.
                contexttype (str) (optional): The type of context playing.
                contextdata (str) (optional): The api link to the context.
                contexturl (str) (optional): The context url - this can lead to an artist, an album, or a playlist.
                progress (float) (optional): The user's progress through the song (seconds).
                duration (int) (optional): The duration of the song (milliseconds).
                albumname (str) (optional): The album name.
                albumlink (str) (optional): The album link.
                albumimagelink (str) (optional): The album's image link.
                song_authors_urls (list) (optional): A list containing the urls to the song authors.
                song_authors (list) (optional): A list containing the names of the song authors.
                is_playing (bool) (optional): A boolean that indicates whether or not the user is actually playing.
                playing_type (str) (optional): A string that contains the type of song the user is playing.
                clientusername (str) (optional): The user's username.
                clientavatar (str) (optional): The user's avatar url.
                client_id (str) (optional): The user's user id.
                friend_code (str) (optional): The user's friend code.
                playing_status (str) (optional): The user's playing status.
                last_song (dict) (optional): The last track that the user played.
        """
        self.songname = songname
        self.songid = songid
        self.songlink = songlink
        self.contexttype = contexttype
        self.contextdata = contextdata
        self.contexturl = contexturl
        self.progress = progress
        self.duration = duration
        self.albumname = albumname
        self.albumnlink = albumlink
        self.albumimagelink = albumimagelink
        self.song_authors_urls = song_authors_urls
        self.song_authors = song_authors if song_authors else []
        self.is_playing = is_playing
        self.playing_type = playing_type
        self.clientusername = clientusername
        self.clientavatar = clientavatar
        self.client_id = client_id
        self.friend_code = friend_code
        self.playing_status = playing_status
        self.last_song = None
        self.last_song_timestamp = None

        if type(self.song_authors) == str:
            self.song_authors = [self.song_authors]

        if last_song:
            if last_song.get('context'):
                href = last_song['context'].get('href')
                type_ = last_song['context'].get('type')
            else:
                href = None
                type_ = None
            self.last_song = SpotifySong(last_song['track']['name'],
                                         song_authors=[artist['name'] for artist in last_song['track']['artists']],
                                         albumname=last_song['album']['name'],
                                         contextdata=href, contexttype=type_,
                                         songid=last_song['track']['id'],
                                         friend_code=friend_code, client_id=client_id, clientusername=clientusername)
            if last_song.get('played_at'):
                self.last_song_timestamp = datetime.datetime.strptime(last_song['played_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                self.last_song_timestamp = self.last_song_timestamp.replace(tzinfo=datetime.timezone.utc)
                self.last_song_timestamp = self.last_song_timestamp.astimezone(datetime.datetime.now().astimezone().
                                                                               tzinfo)
            else:
                self.last_song_timestamp = None

    def __repr__(self):
        return '<' + ', '.join([f'{attr}={self.__dict__[attr]}' for attr in list(self.__dict__.keys())]) + '>'
