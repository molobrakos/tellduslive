#!/usr/bin/env python3
# -*- mode: python; coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
import sys
import requests
from requests.compat import urljoin
from requests_oauthlib import OAuth1Session

sys.version_info >= (3, 0) or exit("Python 3 required")

__version__ = "0.10.10"

_LOGGER = logging.getLogger(__name__)

TELLDUS_LIVE_API_URL = "https://pa-api.telldus.com/json/"
TELLDUS_LIVE_REQUEST_TOKEN_URL = "https://pa-api.telldus.com/oauth/requestToken"
TELLDUS_LIVE_AUTHORIZE_URL = "https://pa-api.telldus.com/oauth/authorize"
TELLDUS_LIVE_ACCESS_TOKEN_URL = "https://pa-api.telldus.com/oauth/accessToken"

TELLDUS_LOCAL_API_URL = "http://{host}/api/"
TELLDUS_LOCAL_REQUEST_TOKEN_URL = "http://{host}/api/token"
TELLDUS_LOCAL_REFRESH_TOKEN_URL = "http://{host}/api/refreshToken"

TIMEOUT = timedelta(seconds=10)

UNNAMED_DEVICE = "NO NAME"

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

SUPPORTED_METHODS = TURNON | TURNOFF | DIM | UP | DOWN | STOP

METHODS = {
    TURNON: "turnOn",
    TURNOFF: "turnOff",
    BELL: "bell",
    TOGGLE: "toggle",
    DIM: "dim",
    LEARN: "learn",
    UP: "up",
    DOWN: "down",
    STOP: "stop",
    RGBW: "rgbw",
    THERMOSTAT: "thermostat",
}

# Sensor types
TEMPERATURE = "temperature"
HUMIDITY = "humidity"
RAINRATE = "rrate"
RAINTOTAL = "rtot"
WINDDIRECTION = "wdir"
WINDAVERAGE = "wavg"
WINDGUST = "wgust"
UV = "uv"
WATT = "watt"
LUMINANCE = "lum"
DEW_POINT = "dewp"
BAROMETRIC_PRESSURE = "barpress"

BATTERY_LOW = 255
BATTERY_UNKNOWN = 254
BATTERY_OK = 253

SUPPORTS_LOCAL_API = ["TellstickZnet", "TellstickNetV2"]

DEFAULT_APPLICATION_NAME = "tellduslive"


def supports_local_api(device):
    """Return true if the device supports local access."""
    return any(dev in device for dev in SUPPORTS_LOCAL_API)


class LocalAPISession(requests.Session):
    """Connect directly to the device."""

    def __init__(self, host, application, access_token=None):
        super().__init__()
        self.url = TELLDUS_LOCAL_API_URL.format(host=host)
        self._host = host
        self._hub_id = None
        self._application = application or DEFAULT_APPLICATION_NAME
        self.request_token = None
        self.token_timestamp = None
        self.access_token = access_token
        if access_token:
            self.headers.update(
                {"Authorization": "Bearer {}".format(self.access_token)}
            )
            self.refresh_access_token()

    def discovery_info(self):
        """Retrive information from discovery socket."""
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        try:
            sock.sendto(b"D", (self._host, 30303))
            data, (address, _) = sock.recvfrom(1024)
        except socket.timeout:
            _LOGGER.warning(
                "Socket timeout trying to read info from Tellstick"
            )
            return []
        entry = data.decode("ascii").split(":")
        # expecting product, mac, activation code, version
        if len(entry) != 4:
            return []
        ret = [
            {
                "name": address,
                "type": entry[0],
                "id": entry[1],
                "version": entry[3],
            }
        ]
        _LOGGER.debug("Discovered hub: %s", ret)
        self._hub_id = entry[1]
        return ret

    @property
    def hub_id(self):
        return self._hub_id

    @property
    def authorize_url(self):
        """Retrieve URL for authorization."""
        try:
            response = self.put(
                TELLDUS_LOCAL_REQUEST_TOKEN_URL.format(host=self._host),
                data={"app": self._application},
                timeout=TIMEOUT.seconds,
            )
            response.raise_for_status()
            result = response.json()
            self.request_token = result.get("token")
            return result.get("authUrl")
        except (OSError, ValueError) as e:
            _LOGGER.error("Failed to retrieve authorization URL: %s", e)

    def authorize(self):
        """Perform authorization."""
        try:
            response = self.get(
                TELLDUS_LOCAL_REQUEST_TOKEN_URL.format(host=self._host),
                params=dict(token=self.request_token),
                timeout=TIMEOUT.seconds,
            )
            response.raise_for_status()
            result = response.json()
            if "token" in result:
                self.access_token = result["token"]
                self.headers.update(
                    {"Authorization": "Bearer {}".format(self.access_token)}
                )
                self.token_timestamp = datetime.now()
                token_expiry = datetime.fromtimestamp(result.get("expires"))
                _LOGGER.debug("Token expires %s", token_expiry)
                return True
        except OSError as e:
            _LOGGER.error("Failed to authorize: %s", e)

    def refresh_access_token(self):
        """Refresh api token"""
        try:
            response = self.get(
                TELLDUS_LOCAL_REFRESH_TOKEN_URL.format(host=self._host)
            )
            response.raise_for_status()
            result = response.json()
            self.access_token = result.get("token")
            self.token_timestamp = datetime.now()
            token_expiry = datetime.fromtimestamp(result.get("expires"))
            _LOGGER.debug("Token expires %s", token_expiry)
            return True
        except OSError as e:
            _LOGGER.error("Failed to refresh access token: %s", e)

    @property
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
    def __init__(
        self,
        public_key,
        private_key,
        token=None,
        token_secret=None,
        application=None,
    ):
        super().__init__(public_key, private_key, token, token_secret)
        self.url = TELLDUS_LIVE_API_URL
        self.access_token = None
        self.access_token_secret = None
        if application:
            self.headers.update({"X-Application": application})

    @property
    def hub_id(self):
        pass

    @property
    def authorize_url(self):
        """Retrieve URL for authorization."""
        _LOGGER.debug("Fetching request token")
        try:
            self.fetch_request_token(
                TELLDUS_LIVE_REQUEST_TOKEN_URL, timeout=TIMEOUT.seconds
            )
            _LOGGER.debug("Got request token")
            return self.authorization_url(TELLDUS_LIVE_AUTHORIZE_URL)
        except (OSError, ValueError) as e:
            _LOGGER.error("Failed to retrieve authorization URL: %s", e)

    def authorize(self):
        """Perform authorization."""
        try:
            _LOGGER.debug("Fetching access token")
            token = self._fetch_token(
                TELLDUS_LIVE_ACCESS_TOKEN_URL, timeout=TIMEOUT.seconds
            )
            _LOGGER.debug("Got access token")
            self.access_token = token["oauth_token"]
            self.access_token_secret = token["oauth_token_secret"]
            _LOGGER.debug("Authorized: %s", self.authorized)
            return self.authorized
        except (OSError, ValueError) as e:
            _LOGGER.error("Failed to authorize: %s", e)

    def maybe_refresh_token(self):
        """Refresh access_token if expired."""
        pass


class Session:
    """Tellduslive session."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        public_key=None,
        private_key=None,
        token=None,
        token_secret=None,
        host=None,
        application=None,
    ):

        _LOGGER.info("%s version %s", __name__, __version__)

        if not (
            all([public_key, private_key, token, token_secret])
            or all([public_key, private_key])
            or all([host, token])
            or host
        ):
            raise ValueError("Missing configuration")

        self._state = {}
        self._session = (
            LocalAPISession(host, application, token)
            if host
            else LiveAPISession(
                public_key, private_key, token, token_secret, application
            )
        )
        self._isLocal = True if host else False

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

    def _request(self, path, **params):
        """Send a request to the Tellstick Live API."""
        try:
            self._session.maybe_refresh_token()
            url = urljoin(self._session.url, path)
            _LOGGER.debug("Request %s %s", url, params)
            response = self._session.get(
                url, params=params, timeout=TIMEOUT.seconds
            )
            response.raise_for_status()
            _LOGGER.debug(
                "Response %s %s %s",
                response.status_code,
                response.headers["content-type"],
                response.json(),
            )
            response = response.json()
            if "error" in response:
                raise OSError(response["error"])
            return response
        except OSError as error:
            _LOGGER.warning("Failed request: %s", error)

    def execute(self, method, **params):
        """Make request, check result if successful."""
        response = self._request(method, **params)
        return response and response.get("status") == "success"

    def _request_devices(self):
        """Request list of devices from server."""
        res = self._request(
            "devices/list",
            supportedMethods=SUPPORTED_METHODS,
            includeIgnored=0,
        )
        return res.get("device") if res else None

    def _request_sensors(self):
        """Request list of sensors from server."""
        res = self._request(
            "sensors/list", includeValues=1, includeScale=1, includeIgnored=0
        )
        return res.get("sensor") if res else None

    def update(self):
        """Updates all devices and sensors from server."""

        def collect(devices, is_sensor=False):
            """Update local state.
            N.B. We prefix sensors with '_', since apparently sensors
            and devices do not share name space and there can be
            collissions.
            FIXME: Remove this hack."""
            return {
                "_" * is_sensor + str(device["id"]): device
                for device in devices or {}
                if device["name"] and not (is_sensor and "data" not in device)
            }

        devices = self._request_devices()
        sensors = self._request_sensors()
        new_state = collect(devices)
        new_state.update(collect(sensors, True))
        self._state = new_state

        return devices is not None and sensors is not None

    def request_info(self, device_id):
        """Request device info."""
        res = self._request("device/info", id=device_id)
        return res if res else None

    @property
    def hub_id(self):
        """Return hub id."""
        return self._session.hub_id

    def get_clients(self):
        """Request list of clients (Telldus devices) from server."""
        if self._isLocal:
            return self._session.discovery_info()
        res = self._request("clients/list")
        return res.get("client") if res else []

    def device(self, device_id):
        """Return a device object."""
        return Device(self, device_id)

    @property
    def sensors(self):
        """Return only sensors.
        FIXME: terminology device vs device."""
        return (device for device in self.devices if device.is_sensor)

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

    def __init__(self, session, device_id):
        self._session = session
        self._device_id = device_id

    def __str__(self):
        if self.is_sensor:
            items = ", ".join(str(item) for item in self.items)
            return "Sensor #{id:>9} {name:<20} ({items})".format(
                id=self.device_id,
                name=self.name or UNNAMED_DEVICE,
                items=items,
            )
        else:
            return (
                "Device #{id:>9} {name:<20} " "({state}:{value}) [{methods}]"
            ).format(
                id=self.device_id,
                name=self.name or UNNAMED_DEVICE,
                state=self._str_methods(self.state),
                value=self.statevalue,
                methods=self._str_methods(self.methods),
            )

    def __getattr__(self, name):
        if self.device and name in [
            "name",
            "state",
            "battery",
            "model",
            "protocol",
            "lastUpdated",
            "methods",
            "data",
            "sensorId",
        ]:
            return self.device.get(name)

    @property
    def is_online(self):
        """Return online status."""
        return self.device.get("online") == "1"

    @property
    def device(self):
        """Return the raw representation of the device."""
        # pylint: disable=protected-access
        return self._session._device(self.device_id)

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
        params.update(id=self.device_id)
        # Corresponding API methods
        method = "device/{}".format(METHODS[command])
        if self._session.execute(method, **params):
            self.device["state"] = command
            return True

    @property
    def is_sensor(self):
        """Return true if this is a sensor."""
        return "data" in self.device

    @property
    def statevalue(self):
        """State value of device."""
        val = self.device.get("statevalue")
        return val if val and val != "unde" else 0

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.state == TURNON or self.state == DIM

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

    def info(self):
        """Retrive device info."""
        if self.is_sensor:
            res = self.device
        else:
            res = self._session.request_info(self.device_id)
        if res and "client" not in res:
            res["client"] = self._session.hub_id
        return res if res else None

    def turn_on(self):
        """Turn device on."""
        return self._execute(TURNON)

    def turn_off(self):
        """Turn device off."""
        return self._execute(TURNOFF)

    def dim(self, level):
        """Dim device."""
        if self._execute(DIM, level=level):
            self.device["statevalue"] = level
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
        return next(
            (
                item
                for item in self.items
                if (item.name == name and int(item.scale) == int(scale))
            ),
            None,
        )

    def value(self, name, scale):
        """Return value of sensor item."""
        return self.item(name, scale).value


class SensorItem:
    # pylint: disable=too-few-public-methods, no-member
    """Reference to a sensor data item."""

    def __init__(self, data):
        vars(self).update(data)

    def __str__(self):
        return "{name}={value}".format(name=self.name, value=self.value)


def read_credentials():
    from sys import argv
    from os.path import join, dirname, expanduser

    for directory in [dirname(argv[0]), expanduser("~")]:
        try:
            with open(join(directory, ".tellduslive.conf")) as config:
                return dict(
                    x.split(": ")
                    for x in config.read().strip().splitlines()
                    if not x.startswith("#")
                )
        except OSError:
            continue
    return {}


if __name__ == "__main__":
    """Dump configured devices and sensors."""
    logging.basicConfig(level=logging.INFO)
    credentials = read_credentials()
    session = Session(**credentials)
    session.update()
    print("Devices\n" "-------")
    for device in session.devices:
        print(device)
        for item in device.items:
            print("- {}".format(item))
