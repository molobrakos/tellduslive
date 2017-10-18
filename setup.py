#!/usr/bin/python

from setuptools import setup

setup(name="tellduslive",
      version='0.4.0',
      description="Communicate with Telldus Live",
      url="https://github.com/molobrakos/tellduslive",
      license="",
      author="Erik",
      author_email="error.errorsson@gmail.com",
      install_requires=['requests',
                        'requests_oauthlib'],
      py_modules=["tellduslive"],
      provides=["tellduslive"],)
