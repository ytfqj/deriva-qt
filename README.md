# deriva-qt
Graphical User Interface tools for DERIVA using PyQt
* Authentication Agent
* File Uploader

## Installation
### Windows / MacOS
Windows and MacOS users can download prebuilt bundles which include all dependencies [here](https://github.com/informatics-isi-edu/deriva-qt/releases).  Download the appropriate file for your OS and extract the archive. Windows users can run the extracted `exe` file directly, while Mac users can copy the extracted application folder and then context (right) click and select `Open`.

### Fedora
### Install from source

1. Install dependency packages 

```
dnf install python3-qt5 python3-qt5-webengine python3-devel 
```

2. install deriva-py and deriva-qt from source

```
pip3 install --upgrade git+https://github.com/informatics-isi-edu/deriva-py.git
pip3 install --upgrade git+https://github.com/informatics-isi-edu/deriva-qt.git
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
