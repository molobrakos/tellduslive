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
# pylint:disable=unused-wildcard-import
from constants import *
from protocol import Protocol
class Controller(object):
    """
    A base class for a contoller.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, logger=None):
        """ init of Controller class """
        super(Controller, self).__init__()
        self.decode_packet = Protocol().decode_packet
        self.encode_packet = Protocol().encode_packet
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
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        """ exits on signal """
        self._LOGGER.debug("exit gracefully, %d %s", signum, frame)
        self._stop = True

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

    def _send(self, sock, command, **args):
        """Send a command to the controller
        Available commands documented in
        https://github.com/telldus/tellstick-net/blob/master/
            firmware/tellsticknet.c"""
        packet = self.encode_packet(command, **args)
        self._LOGGER.debug("Sending packet to controller %s:%d <%s>",
                           self._address, COMMAND_PORT, packet)
        sock.sendto(packet, (self._address, COMMAND_PORT))

    def _register(self, sock):
        """ register self as listener fÃor telstick net """
        self._LOGGER.info("Registering self as listener for device at %s",
                          self._address)
        try:
            self._send(sock, "reglistener")
            self._last_registration = datetime.now()
        except OSError:  # e.g. Network is unreachable
            # just retry
            pass

    def _registration_needed(self):
        """Register self at controller"""
        if self._last_registration is None:
            return True
        since_last_check = datetime.now() - self._last_registration
        return since_last_check > REGISTRATION_INTERVAL

    def _recv_packet(self, sock):
        """Wait for a new packet from controller"""

        if self._registration_needed():
            self._register(sock)

        try:
            response, (self._address, self._port) = sock.recvfrom(1024)
            if self._address != self._address:
                return
            return response.decode("ascii")
        except (socket.timeout, OSError):
            pass

    def packets(self):
        """Listen forever for network events, yield stream of packets"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setblocking(1)
            sock.settimeout(TIMEOUT.seconds)
            self._LOGGER.debug("Listening for signals from %s", self._address)
            while not self._stop:
                packet = self._recv_packet(sock)
                if packet is not None:
                    yield packet


