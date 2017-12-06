#
# Copyright 2017 University of Southern California
# Distributed under the GNU GPL 3.0 license. See LICENSE for more info.
#

""" Installation script for deriva.qt
"""

from setuptools import setup, find_packages
import re
import io

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    io.open('deriva/qt/__init__.py', encoding='utf_8_sig').read()
    ).group(1)

setup(
    name="deriva.qt",
    description="Graphical User Interface tools for DERIVA",
    url='https://github.com/informatics-isi-edu/deriva-qt',
    maintainer='USC Information Sciences Institute ISR Division',
    maintainer_email='misd-support@isi.edu',
    version=__version__,
    packages=find_packages(),
    package_data={'deriva.qt': ['upload_gui/conf/config.json']},
    namespace_packages=["deriva"],
    entry_points={
        'console_scripts': [
            'deriva-auth = deriva.qt.auth_agent.__main__:main',
            'deriva-upload = deriva.qt.upload_gui.__main__:main'
        ]
    },
    requires=[
        'os',
        'sys',
        'logging',
        'requests',
        'deriva.core',
        'deriva.transfer',
        'PyQt5'
    ],
    license='GNU GPL 3.0',
    classifiers=[
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License',
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5'
    ]
)

