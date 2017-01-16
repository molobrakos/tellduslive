#!/usr/bin/python

from setuptools import setup
from tellduslive import __version__

setup(name="tellduslive",
      version='0.2.6',
      description="Communicate with Telldus Live",
      url="https://github.com/molobrakos/tellduslive",
      license="",
      author="Erik",
      author_email="Erik",
      install_requires=['requests',
                        'requests_oauthlib'],
      py_modules=["tellduslive"],
      provides=["tellduslive"],
)
