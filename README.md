# SpotAlong-Client

### Listen along to your friends through Spotify
#### and discover new music tastes and interests through SpotAlong - all without needing premium.

<br/>This is the PyQt5 frontend for SpotAlong. 
Issues and pull requests are welcomed, but please note that most of the code was written 2+ years ago, when I had no clue about best practices with Python / PyQt5 and had mostly ~~spaghetti~~ horrendous code, and most of it is uncommented and relatively undocumented.


# Roadmap

## v1.0.0
Initial Release (windows only)

## v1.0.1
Performance enhancements (speculative)

## v1.0.2
Linux and MacOS builds

## v1.1.0
Add an embedded, ad-blocking version of Spotify

## v1.2.0
Add vote skips and song requests for group listening-along sessions


# Code Breakdown
## /
app.py: The entry point of the program, updates the ui with all the widgets and establishes update threads.
<br/>mainclient.py: Handles the websocket connection with the SpotAlong server. 
## utils/
constants.py: Defines constants useful for connecting to the SpotAlong server.<br/>
login.py: Provides utility functions used to login / authenticate with the SpotAlong api.<br/>
uiutils.py: Provides utility functions helpful to the ui (scaling, eliding text).<br/>
utils.py: Provides utility functions (color extraction, downloading images).
## ui/
browser.py: Defines the window used to log in to Spotify using QWebEngine.<br/>
customwidgets.py: Houses almost all of the widgets that are displayed throughout the app, and various update threads.<br/>
loginwidgets.py: Houses the widgets pertaining to the login / loading part of the app.<br/>
mainui.py: The autogenerated file from QtDesigner that represents the barebones main ui of the app.
## spotifyclient/
spotifyclient.py: Provides a class that contains info about the specified user.<br/>
spotifylistener.py: Contains the class used to handle listening along sessions.<br/>
spotifyplayer.py: Contains the class used to connect to the unofficial Spotify api, in order to modify user playback.<br/>
spotifysong.py: Contains a helper class that abstracts a users' listening / online / offline state.


# Special Thanks
A special thanks goes to Wanderson and his amazing PyQt interfaces, one of which was the inspiration for the ui of SpotAlong:
https://github.com/Wanderson-Magalhaes/Simple_PySide_Base
https://www.youtube.com/watch?v=iaIooM9FlRI
