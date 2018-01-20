#!/usr/bin/python3
"""Setup
"""
from setuptools import find_packages
from distutils.core import setup

version = "0.0.4"

with open('README.rst') as f:
    long_description = f.read()

setup(name='ofxstatement-airbankcz',
      version=version,
      author="Milan Knížek",
      author_email="milankni@gmail.com",
      url="https://github.com/milankni/ofxstatement-airbankcz",
      description=("Ofxstatement plugin for Air Bank a.s. (CZ) - current and saving accounts history"),
      long_description=long_description,
      license="GPLv3",
      keywords=["ofx", "banking", "statement"],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Programming Language :: Python :: 3',
          'Natural Language :: English',
          'Topic :: Office/Business :: Financial :: Accounting',
          'Topic :: Utilities',
          'Environment :: Console',
          'Operating System :: OS Independent',
          'License :: OSI Approved :: GNU General Public License v3'],
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=["ofxstatement", "ofxstatement.plugins"],
      entry_points={
          'ofxstatement':
          ['airbankcz = ofxstatement.plugins.airbankcz:AirBankCZPlugin']
          },
      install_requires=['ofxstatement'],
      include_package_data=True,
      zip_safe=True
      )
