# -*- mode: python -*-

block_cipher = None

from os import environ as env
from deriva_io.generic_uploader import GenericUploader

a = Analysis(['./__main__.py'],
             pathex=[],
             binaries=[],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          name='DERIVA-Upload-%s' % GenericUploader.getVersion(),
          strip=False,
          upx=False,
          debug=env.get("DEBUG", False),
          console=env.get("DEBUG", False),
          icon='./resources/images/upload.ico')
