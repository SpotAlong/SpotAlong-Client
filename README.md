# SpotAlong-Client

<img width="1137" alt="Group 1" src="https://spotalong.github.io/static/Group%201.png">

### Listen along to your friends through Spotify
#### and discover new music tastes and interests through SpotAlong - all without needing premium.

<br/>This is the PyQt5 frontend for SpotAlong. 
Issues and pull requests are welcomed, but please note that most of the code was written 2+ years ago, when I had no clue about best practices with Python / PyQt5 and had mostly ~~spaghetti~~ horrendous code, and most of it is uncommented and relatively undocumented.

# Installation
Simply head over to the releases tab, and download and run the installer for the latest version. 

# Manual Installation
To manually install SpotAlong-Client, clone the repository to a folder of your choosing, then run the following commands according to your operating system. Please note that SpotAlong has only been tested on Python 3.8, and older or newer versions may not work.

### Windows
```
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```
Note that `python` (line 1 only) may be replaced with `py -3` depending on your installation.<br/>
You can also provide any of the `-d`, `-v`, `--debug`, or `--verbose` flags to `app.py` to set the logging level to `logging.DEBUG`.

### MacOS / Linux
```
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

## Compile Installer
A helper script has been included at `build.py` that can automatically create the executable file, zip all dependencies, and compile the installer using makensis. Simply run the file and the installer will be created at `./SpotAlong-Installer.exe`. Please note that NSIS must be installed and makensis.exe must be added to PATH. Aditionally, the [nsisunz](https://nsis.sourceforge.io/Nsisunz_plug-in) and [ApplicationID](https://nsis.sourceforge.io/ApplicationID_plug-in) plugins must be installed.

# Roadmap

## v1.0.X
Initial Release (windows only)

## v1.1.X
Performance enhancements (speculative)

## v1.2.X
Linux and MacOS builds

## v2.0.X
Add an embedded, ad-blocking version of Spotify

## v3.0.X
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
