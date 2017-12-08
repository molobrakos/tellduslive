# -*- coding: utf-8 -*-
"""
Moduele interfaces with tellstick net v1
"""
# pylint:disable=invalid-name
import logging
from json import JSONEncoder
from tellsticknet import devicemanager
# pylint:disable=unused-wildcard-import
TELLDUS_LOCAL_URL = 'http://tellstick/'
TURNON = 1
TURNOFF = 2
BELL = 4
TOGGLE = 8
DIM = 16
LEARN = 32
UP = 128
DOWN = 256
STOP = 512
RGBW = 1024
THERMOSTAT = 2048


class Localnet(object):
    """ Main object for tellstick net local iterface"""
    TELLSTICK_SUCCESS = 0
    TELLSTICK_ERROR_DEVICE_NOT_FOUND = -3
    TELLSTICK_ERROR_UNKNOWN = -99

    def __init__(self, config_file=None, logger=None):
        self._request = None
        self._LOGGER = logger or logging.getLogger(__name__)
        self.config_path = config_file or "/etc/tellsticknet.yml"
        self.devicemanager = devicemanager.Tellstick(self.config_path, logger=self._LOGGER)
        self.response = None
        self._exception = None
        self.status_code = None
        self.headers = {}
        self._json = None
        self.url = TELLDUS_LOCAL_URL 

    def __str__(self):
        return self.response

    def devices(self, *args, params=None, timeout=None):
        """ creates device json """
        if args[0] == "list":
            devices = {"device" :self.devicemanager.listdevices()}
            self._LOGGER.debug("Devices: %s: ", devices)
            self._json = devices
            return self.TELLSTICK_SUCCESS
        else:
            self._json = {"error": "Internal server error"}
            raise AttributeError

    def sensors(self, *args, params=None, timeout=None):
        """ creates sensor json """
        if args[0] == "list":
            sensor = {"sensor" : self.devicemanager.listsensors()}
            self._LOGGER.debug("Sensor: %s: ", sensor)
            self._json = sensor
            return self.TELLSTICK_SUCCESS
        else:
            self._json = {"error": "Internal server error"}
            raise AttributeError

    def device(self, *args, params=None, timeout=None):
        """ runnns command on device """
        self._LOGGER.debug("Device id: %s ", params['id'])
        d = self.devicemanager.device(params['id'])
        self._LOGGER.debug("Got device: %s ", d)
        if d.isDevice():
            if args[0] == "turnOn":
                d.command(TURNON)
                self._json = {"status":"success"}
                return self.TELLSTICK_SUCCESS

            elif args[0] == "turnOff":
                d.command(TURNOFF)
                self._json = {"status":"success"}
                return self.TELLSTICK_SUCCESS
            else:
                self._json = {"error": "Internal server error"}
                raise AttributeError
        else:
            self._json = {"error": "Internal server error"}
            raise AttributeError



    def get(self, url, params=None, timeout=None):
        """ request get faker """
        self._LOGGER.debug("url: %s: ", url)
        self._request = url[len(TELLDUS_LOCAL_URL):].split('/')
        self._LOGGER.debug("get() _request[0]: %s: ", self._request[0])
        self._LOGGER.debug("get() _request[1:]: %s: ", self._request[1:])
        self._LOGGER.debug("get() params: %s: ", params)
        self.headers['content-type'] = "application/json; charset=utf-8"
        try:
            self.response = getattr(self,
                                    "%s" % self._request[0])(*self._request[1:],
                                                             params=params, timeout=timeout)
        except AttributeError:
            self._exception = "500 Internal server error %s"% self._request
            self.status_code = 500
            self._json = {"error": "Internal server error"}
            return self
        self.status_code = 200
        return self

    @staticmethod
    def raise_for_status():
        """ pass status exception """
        pass

    def json(self):
        """ returns json """
        return self._json

    @staticmethod
    def maybe_refresh_token():
        """Refresh access_token if expired."""
        pass

