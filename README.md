# deriva-qt
Graphical User Interface tools for DERIVA using PyQt
* Authentication Agent
* File Uploader

## Installation
### Windows / MacOS
Windows and MacOS users can download prebuilt bundles which include all dependencies [here](https://github.com/informatics-isi-edu/deriva-qt/releases). Download the appropriate file for your OS and extract the archive. Windows users can run the extracted `exe` file directly, while Mac users can copy the extracted application folder and then context (right) click and select `Open`.

## Install from source
### Fedora

1. Install dependency packages 

```
dnf install python3-qt5 python3-qt5-webengine python3-devel 
```

2. install deriva-py and deriva-qt from source

```
pip3 install --upgrade git+https://github.com/informatics-isi-edu/deriva-py.git
pip3 install --upgrade git+https://github.com/informatics-isi-edu/deriva-qt.git
```

### Windows 10 
1. Install qt5
 first download qt5, then exptract the zip file and install following the install wizard

  here is a url for qt5 download, https://sourceforge.net/projects/pyqt/files/PyQt5/PyQt-5.10.1/PyQt5_gpl-5.10.1.zip/download

2. install deriva-py and deriva-qt from source

```
pip install --upgrade git+https://github.com/informatics-isi-edu/deriva-py.git
pip install --upgrade git+https://github.com/informatics-isi-edu/deriva-qt.git
```

## User Instructions 
### deriva-auth

At the command-line, execute deriva-auth to set up credentials with deriva server

```
deriva-auth
```


Links:
* [Build status](http://buildbot.isrd.isi.edu/)
* [Downloads](http://buildbot.isrd.isi.edu/~buildbot/deriva-qt/)
