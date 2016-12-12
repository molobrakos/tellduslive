#!/usr/bin/python

from setuptools import setup

setup(name="tellduslive",
      version="0.1.11",
      description="Communicate with Telldus Live",
      url="https://github.com/molobrakos/tellduslive",
      license="",
      author="Erik",
      author_email="Erik",
      install_requires=['requests_oauthlib'],
      py_modules=["tellduslive"],
      provides=["tellduslive"],)
