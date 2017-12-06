# -*- coding: utf-8 -*-
# pylint:disable=invalid-name
"""
Controller handler for telstick net v1
"""
import socket
import signal
import logging
from sys import exit
from datetime import datetime, timedelta
from tellsticknet.protocol import encode_packet
from tellsticknet.controller import Controller as tsnController
# pylint:disable=unused-wildcard-import
from constants import *
class Controller(object):
    """
    A base class for a contoller.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, logger=None):
        """ init of Controller class """
        super(Controller, self).__init__()
        self._LOGGER = logger or logging.getLogger(__name__)
        self._id = 0
        self._ignored = None
        self._address = None
        self._devices = None
        self._name = None
        self._port = COMMAND_PORT
        self._stop = False
        self._last_registration = None
        self._iscontroller = True
        self._controller = None

    def id(self):
        """ returns controller id """
        return self._id

    def address(self):
        """ retruns address """
        return self._address
    def port(self):
        """ return controller port """
        return self._port

    def load(self, settings):
        """ loads settnigs from config to contoller object """
        if 'id' in settings:
            self._id = str(settings['id'])
        if 'name' in settings:
            self._name = settings['name']
        if 'port' in settings:
            self._port = str(settings['port'])
        if 'address' in settings:
            self._address = settings['address']
        self._controller = tsnController(self._address)
        self._LOGGER.debug("loaded controller: %s, id: %s, address: %s, port: %s",
                           self._name, self._id, self._address, self._port)



    def ignored(self):
        """ retrun ignored """
        return self._ignored

    def iscontroller(self):
        """
        Return True if this is a device.
        """
        return self._iscontroller

    def name(self):
        """ retruns name of controller """
        return self._name if self._name is not None else 'Controller %i' % self._id

    def packets(self):
        """Listen forever for network events, yield stream of packets"""
        return self._controller.packets()


