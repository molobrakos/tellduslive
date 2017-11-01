#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Communicate with Telldus Live server."""

import logging
from datetime import datetime, timedelta

from requests import Session
from requests.compat import urljoin
from requests_oauthlib import OAuth1Session

__version__ = '0.8.0'

_LOGGER = logging.getLogger(__name__)

TELLDUS_LIVE_API_URL = 'https://api.telldus.com/json/'
TELLDUS_LIVE_REQUEST_TOKEN_URL = 'https://api.telldus.com/oauth/requestToken'
TELLDUS_LIVE_AUTHORIZE_URL = 'https://api.telldus.com/oauth/authorize'
TELLDUS_LIVE_ACCESS_TOKEN_URL = 'https://api.telldus.com/oauth/accessToken'

TELLDUS_LOCAL_API_URL = 'http://{host}/api/'
TELLDUS_LOCAL_REQUEST_TOKEN_URL = 'http://{host}/api/token'
TELLDUS_LOCAL_REFRESH_TOKEN_URL = 'http://{host}/api/refreshToken'

TIMEOUT = timedelta(seconds=10)

UNNAMED_DEVICE = 'NO NAME'

# Tellstick methods
# pylint:disable=invalid-name
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

SUPPORTED_METHODS = (
    TURNON |
    TURNOFF |
    DIM |
    UP |
    DOWN |
    STOP)

METHODS = {
    TURNON: 'turnOn',
    TURNOFF: 'turnOff',
    BELL: 'bell',
    TOGGLE: 'toggle',
    DIM: 'dim',
    LEARN: 'learn',
    UP: 'up',
    DOWN: 'down',
    STOP: 'stop',
    RGBW: 'rgbw',
    THERMOSTAT: 'thermostat'
}

# Sensor types
TEMPERATURE = 'temperature',
HUMIDITY = 'humidity',
RAINRATE = 'rrate',
RAINTOTAL = 'rtot',
WINDDIRECTION = 'wdir',
WINDAVERAGE = 'wavg',
WINDGUST = 'wgust',
UV = 'uv',
WATT = 'watt',
LUMINANCE = 'lum',
DEW_POINT = 'dew',  # ?
BAROMETRIC_PRESSURE = '?',


SUPPORTS_LOCAL_API = ['TellstickZnet', 'TellstickNetV2']


def supports_local_api(device):
    """Return true if the device supports local access."""
    return any(dev in device
               for dev in SUPPORTS_LOCAL_API)


class LocalAPISession(Session):
    """Connect directly to the device."""

    def __init__(self, host, application, access_token=None):
        super().__init__()
        self.url = TELLDUS_LOCAL_API_URL.format(host=host)
        self._host = host
        self._application = application
        self.request_token = None
        self.token_timestamp = None
        self.access_token = access_token
        if access_token:
            self.headers.update(
                {'Authorization': 'Bearer {}'.format(self.access_token)})
            self.refresh_access_token()

    @property
    def authorize_url(self):
        """Retrieve URL for authorization."""
        try:
            response = self.put(
                TELLDUS_LOCAL_REQUEST_TOKEN_URL.format(host=self._host),
                data={'app': self._application},
                timeout=TIMEOUT.seconds)
            response.raise_for_status()
            result = response.json()
            self.request_token = result.get('token')
            return result.get('authUrl')
        except (OSError, ValueError) as e:
            _LOGGER.error('Failed to retrieve authorization URL: %s', e)

    def authorize(self):
        """Perform authorization."""
        try:
            response = self.get(
                TELLDUS_LOCAL_REQUEST_TOKEN_URL.format(host=self._host),
                params=dict(token=self.request_token),
                timeout=TIMEOUT.seconds)
            response.raise_for_status()
            result = response.json()
            if 'token' in result:
                self.access_token = result['token']
                self.headers.update(
                    {'Authorization': 'Bearer {}'.format(self.access_token)})
                self.token_timestamp = datetime.now()
                token_expiry = datetime.fromtimestamp(result.get('expires'))
                _LOGGER.debug('Token expires %s', token_expiry)
                return True
        except OSError as e:
            _LOGGER.error('Failed to authorize: %s', e)

    def refresh_access_token(self):
        """Refresh api token"""
        try:
            response = self.get(
                TELLDUS_LOCAL_REFRESH_TOKEN_URL.format(host=self._host))
            response.raise_for_status()
            result = response.json()
            self.access_token = result.get('token')
            self.token_timestamp = datetime.now()
            token_expiry = datetime.fromtimestamp(result.get('expires'))
            _LOGGER.debug('Token expires %s', token_expiry)
            return True
        except OSError as e:
            _LOGGER.error('Failed to refresh access token: %s', e)

    def authorized(self):
        """Return true if successfully authorized."""
        return self.access_token

    def maybe_refresh_token(self):
        """Refresh access_token if expired."""
        if self.token_timestamp:
            age = datetime.now() - self.token_timestamp
            if age > timedelta(seconds=(12 * 60 * 60)):  # 12 hours
                self.refresh_access_token()


class LiveAPISession(OAuth1Session):
    """Connection to the cloud service."""

    # pylint: disable=too-many-arguments
    def __init__(self,
                 public_key,
                 private_key,
                 token=None,
                 token_secret=None,
                 application=None):
        super().__init__(public_key, private_key, token, token_secret)
        self.url = TELLDUS_LIVE_API_URL
        self.access_token = None
        self.access_token_secret = None
        if application:
            self.headers.update({'X-Application': application})

    @property
    def authorize_url(self):
        """Retrieve URL for authorization."""
        _LOGGER.debug('Fetching request token')
        try:
            self.fetch_request_token(
                TELLDUS_LIVE_REQUEST_TOKEN_URL, timeout=TIMEOUT.seconds)
            _LOGGER.debug('Got request token')
            return self.authorization_url(TELLDUS_LIVE_AUTHORIZE_URL)
        except (OSError, ValueError) as e:
            _LOGGER.error('Failed to retrieve authorization URL: %s', e)

    def authorize(self):
        """Perform authorization."""
        try:
            _LOGGER.debug('Fetching access token')
            token = self._fetch_token(
                TELLDUS_LIVE_ACCESS_TOKEN_URL, timeout=TIMEOUT.seconds)
            _LOGGER.debug('Got access token')
            self.access_token = token['oauth_token']
            self.access_token_secret = token['oauth_token_secret']
            _LOGGER.debug('Authorized: %s', self.authorized)
            return self.authorized
        except (OSError, ValueError) as e:
            _LOGGER.error('Failed to authorize: %s', e)

    def maybe_refresh_token(self):
        """Refresh access_token if expired."""
        pass


class Client:
    """Tellduslive client."""

    # pylint: disable=too-many-arguments
    def __init__(self,
                 public_key=None,
                 private_key=None,
                 token=None,
                 token_secret=None,
                 host=None,
                 application=None):
        self._state = {}
        self._session = (
            LocalAPISession(host, application, token) if host else
            LiveAPISession(public_key,
                           private_key,
                           token,
                           token_secret,
                           application))

    @property
    def authorize_url(self):
        """Retrieve URL for authorization."""
        return self._session.authorize_url

    def authorize(self):
        """Perform authorization."""
        return self._session.authorize()

    @property
    def access_token(self):
        """Return access token."""
        return self._session.access_token

    @property
    def is_authorized(self):
        """Return true if successfully authorized."""
        return self._session.authorized

    @property
    def access_token_secret(self):
        """Return the token secret."""
        return self._session.access_token_secret

    def _device(self, device_id):
        """Return the raw representaion of a device."""
        return self._state.get(device_id)

    def request(self, path, **params):
        """Send a request to the Tellstick Live API."""
        try:
            self._session.maybe_refresh_token()
            url = urljoin(self._session.url, path)
            _LOGGER.debug('Request %s %s', url, params)
            response = self._session.get(url,
                                         params=params,
                                         timeout=TIMEOUT.seconds)
            response.raise_for_status()
            _LOGGER.debug('Response %s %s',
                          response.status_code,
                          response.json())
            response = response.json()
            if 'error' in response:
                raise OSError(response['error'])
            return response
        except OSError as error:
            _LOGGER.warning('Failed request: %s', error)

    def execute(self, method, **params):
        """Make request, check result if successful."""
        response = self.request(method, **params)
        return response and response.get('status') == 'success'

    def request_devices(self):
        """Request list of devices from server."""
        res = self.request('devices/list',
                           supportedMethods=SUPPORTED_METHODS,
                           includeIgnored=0)
        return res.get('device') if res else None

    def request_sensors(self):
        """Request list of sensors from server."""
        res = self.request('sensors/list',
                           includeValues=1,
                           includeScale=1,
                           includeIgnored=0)
        return res.get('sensor') if res else None

    def update(self):
        """Updates all devices and sensors from server."""
        self._state = {}

        def collect(devices):
            """Update local state."""
            self._state.update({device['id']: device
                                for device in devices or {}
                                if device['name']})

        devices = self.request_devices()
        collect(devices)

        sensors = self.request_sensors()
        collect(sensors)

        return (devices is not None and
                sensors is not None)

    def device(self, device_id):
        """Return a device object."""
        return Device(self, device_id)

    @property
    def devices(self):
        """Request representations of all devices."""
        return (self.device(device_id) for device_id in self.device_ids)

    @property
    def device_ids(self):
        """List of known device ids."""
        return self._state.keys()


class Device:
    """Tellduslive device."""

    def __init__(self, client, device_id):
        self._client = client
        self._device_id = device_id

    def __str__(self):
        if self.is_sensor:
            items = ', '.join(str(item) for item in self.items)
            return 'Sensor #{id:>08} {name:<20} ({items})'.format(
                id=self.device_id,
                name=self.name or UNNAMED_DEVICE,
                items=items)
        else:
            return ('Device #{id} \'{name}\' '
                    '({state}:{value}) [{methods}]').format(
                        id=self.device_id,
                        name=self.name or UNNAMED_DEVICE,
                        state=self._str_methods(self.state),
                        value=self.statevalue,
                        methods=self._str_methods(self.methods))

    def __getattr__(self, name):
        if (self.device and
                name in ['name', 'state', 'battery',
                         'lastUpdated', 'methods', 'data']):
            return self.device.get(name)

    @property
    def device(self):
        """Return the raw representation of the device."""
        # pylint: disable=protected-access
        return self._client._device(self.device_id)

    @property
    def device_id(self):
        """Id of device."""
        return self._device_id

    @staticmethod
    def _str_methods(val):
        """String representation of methods or state."""
        res = []
        for method in METHODS:
            if val & method:
                res.append(METHODS[method].upper())
        return "|".join(res)

    def _execute(self, command, **params):
        """Send command to server and update local state."""
        params.update(id=self._device_id)
        # Corresponding API methods
        method = 'device/{}'.format(METHODS[command])
        if self._client.execute(method, **params):
            self.device['state'] = command
            return True

    @property
    def is_sensor(self):
        """Return true if this is a sensor."""
        return 'data' in self.device

    @property
    def statevalue(self):
        """State value of device."""
        return (self.device['statevalue'] if
                self.device and
                self.device['statevalue'] and
                self.device['statevalue'] != 'unde'
                else 0)

    @property
    def is_on(self):
        """Return true if device is on."""
        return (self.state == TURNON or
                self.state == DIM)

    @property
    def is_down(self):
        """Return true if device is down."""
        return self.state == DOWN

    @property
    def dim_level(self):
        """Return current dim level."""
        try:
            return int(self.statevalue)
        except (TypeError, ValueError):
            return None

    def turn_on(self):
        """Turn device on."""
        return self._execute(TURNON)

    def turn_off(self):
        """Turn device off."""
        return self._execute(TURNOFF)

    def dim(self, level):
        """Dim device."""
        if self._execute(DIM, level=level):
            self.device['statevalue'] = level
            return True

    def up(self):
        """Pull device up."""
        return self._execute(UP)

    def down(self):
        """Pull device down."""
        return self._execute(DOWN)

    def stop(self):
        """Stop device."""
        return self._execute(STOP)

    @property
    def items(self):
        """Return sensor items for sensor."""
        return (SensorItem(item) for item in self.data) if self.data else []

    def item(self, name, scale):
        """Return sensor item."""
        return next((item for item in self.items
                     if (item.name == name and
                         item.scale == scale)), None)

    def value(self, name, scale):
        """Return value of sensor item."""
        return self.item(name, scale).value


class SensorItem:
    # pylint: disable=too-few-public-methods, no-member
    """Reference to a sensor data item."""
    def __init__(self, data):
        vars(self).update(data)

    def __str__(self):
        return '{name}={value}'.format(
            name=self.name, value=self.value)


def main():
    """Dump configured devices and sensors."""
    from os import path
    from sys import argv
    logging.basicConfig(level=logging.INFO)
    try:
        with open(path.join(path.dirname(argv[0]),
                            '.credentials.conf')) as config:
            credentials = dict(
                x.split(': ')
                for x in config.read().strip().splitlines())
    except (IOError, OSError):
        print('Could not read configuration')
        exit(-1)

    client = Client(**credentials)
    client.update()
    print('Devices\n'
          '-------')
    for device in client.devices:
        print(device)
        for item in device.items:
            print('- {}'.format(item))


if __name__ == '__main__':
    main()
