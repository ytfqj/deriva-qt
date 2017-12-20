# deriva-qt
Graphical User Interface tools for DERIVA using PyQt
* Authentication Agent
* File Uploader

## Installation
### Fedora
### Install from source

1. Install dependency packages 

```
dnf install python3-qt5 python3-qt5-webengine pyhon3-devel 
```

2. install deriva-py and deriva-qt from source

```
cd ~/git/deriva-py
pip3 install --upgrade git+https://github.com/informatics-isi-edu/deriva-py.git

cd ~/git/deriva-qt
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
