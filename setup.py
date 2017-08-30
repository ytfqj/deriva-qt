#
# Copyright 2017 University of Southern California
# Distributed under the GNU GPL 3.0 license. See LICENSE for more info.
#

""" Installation script for deriva_qt
"""

from setuptools import setup, find_packages

setup(
    name="deriva_qt",
    description="Graphical User Interface tools for DERIVA",
    url='https://github.com/informatics-isi-edu/deriva-qt',
    maintainer='USC Information Sciences Institute ISR Division',
    maintainer_email='misd-support@isi.edu',
    version="0.2.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'deriva-auth = deriva_qt.auth_agent.__main__:main'
        ]
    },
    requires=[
        'os',
        'sys',
        'logging',
        'requests',
        'deriva_io',
        'PyQt5'],
    license='GNU GPL 3.0',
    classifiers=[
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License',
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ]
)

