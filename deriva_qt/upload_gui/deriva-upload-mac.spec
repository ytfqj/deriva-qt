# -*- mode: python -*-

block_cipher = None

from os import environ as env
from deriva_io.generic_uploader import GenericUploader

a = Analysis(['./upload_app.py'],
             pathex=[''],
             binaries=None,
             datas=[('conf/config.json', 'conf')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='DERIVA-Upload',
          strip=False,
          upx=False,
          debug=env.get("DEBUG", False),
          console=env.get("DEBUG", False),
          icon='./resources/images/upload.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='DERIVA-Auth-%s' % GenericUploader.getVersion())

app = BUNDLE(coll,
         name='DERIVA-Auth-%s.app' % __version__,
         icon='./resources/images/upload.icns',
         bundle_identifier='org.qt-project.Qt.QtWebEngineCore',
         info_plist={
            'CFBundleDisplayName': 'Deriva Upload Utility',
            'CFBundleShortVersionString':GenericUploader.getVersion(),
            'NSPrincipalClass':'NSApplication',
            'NSHighResolutionCapable': 'True'
         })