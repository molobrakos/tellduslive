#!/usr/bin/python

from setuptools import setup

setup(name='tellduslive',
      version='0.10.4',
      description='Communicate with Telldus Live',
      url='https://github.com/molobrakos/tellduslive',
      license='',
      author='Erik',
      author_email='error.errorsson@gmail.com',
      install_requires=['requests',
                        'requests_oauthlib'],
      py_modules=['tellduslive'],
      provides=['tellduslive'],
      scripts=['tellduslive'],
      extras_require={
          'console':  ['docopt'],
      })
