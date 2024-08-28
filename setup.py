#!/usr/bin/python

from setuptools import setup

setup(
    name="tellduslive",
    version="0.10.12",
    description="Communicate with Telldus Live",
    url="https://github.com/molobrakos/tellduslive",
    author="Erik",
    author_email="error.errorsson@gmail.com",
    install_requires=["requests", "requests_oauthlib"],
    py_modules=["tellduslive"],
    provides=["tellduslive"],
    scripts=["tellduslive"],
    extras_require={"console": ["docopt"]},
    classifiers=[
        "License :: OSI Approved :: The Unlicense (Unlicense)"
    ],
)
