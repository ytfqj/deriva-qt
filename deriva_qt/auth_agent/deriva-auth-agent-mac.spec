# -*- mode: python -*-

block_cipher = None

from os import environ as env
from deriva_qt import __version__

a = Analysis(['./__main__.py'],
             pathex=[''],
             binaries=None,
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Deriva Upload',
          strip=False,
          upx=False,
          debug=env.get("DEBUG", False),
          console=env.get("DEBUG", False),
          icon='./resources/images/keys.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='DERIVA-Auth')

app = BUNDLE(coll,
         name='DERIVA Authentication Agent.app',
         icon='./resources/images/keys.icns',
         bundle_identifier='org.qt-project.Qt.QtWebEngineCore',
         info_plist={
            'CFBundleDisplayName': 'DERIVA Authentication Agent',
            'CFBundleShortVersionString':__version__,
            'NSPrincipalClass':'NSApplication',
            'NSHighResolutionCapable': 'True'
         })