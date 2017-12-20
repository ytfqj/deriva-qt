# deriva-qt
Graphical User Interface tools for DERIVA using PyQt
* Authentication Agent
* File Uploader

## Installation
### Fedora 
1. Install dependency packages

`dnf install python3-qt5 python3-qt5-webengine`

2. clone deriva-py and deriva-qt

```
git clone https://github.com/informatics-isi-edu/deriva-py 
git clone https://github.com/informatics-isi-edu/deriva-qt
```

3. install deriva-py and deriva-qt

```
cd ~/git/deriva-py
pip3 install –upgrade . 

cd ~/git/deriva-qt
pip3 install –upgrade . 
```

## User Instructions 
### deriva-auth

At the command-line, execute deriva-auth to set up credentials with deriva server

`deriva-auth`


Links:
* [Build status](http://buildbot.isrd.isi.edu/)
* [Downloads](http://buildbot.isrd.isi.edu/~buildbot/deriva-qt/)
