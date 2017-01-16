#!/usr/bin/python

from setuptools import setup
from tellduslive import __version__

setup(name="tellduslive",
      version=__version__,
      description="Communicate with Telldus Live",
      url="https://github.com/molobrakos/tellduslive",
      license="",
      author="Erik",
      author_email="Erik",
      install_requires=['requests_oauthlib'],
      py_modules=["tellduslive"],
      provides=["tellduslive"],
      install_requires=[
          'requests_oauthlib'
      ],
)
