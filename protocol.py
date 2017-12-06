# pylint:disable=invalid-name
"""
protoco module and modules under protocol is based on;
https://github.com/molobrakos/tellsticknet
encode/and decode protocol as described in
https://developer.telldus.com/doxygen/html/TellStickNet.html
"""
import importlib
import sys
import os
sys.path.append(os.path.dirname(__file__))
import logging
# pylint:disable=unused-wildcard-import
from constants import *
_LOGGER = logging.getLogger(__name__)

class Protocol(object):
    """ main object for encodeing and decodeing devices """
    def __init__(self, protocol=None):
        if protocol is not None:
            self._protocol = protocol
            self._methods = None
            modname = "protocols.%s" % self._protocol
            self._module = importlib.import_module(modname)
            self._model = None
            self._method = None
            self._params = None

    def __str__(self):
        """ retrus protolu used as string """
        return self._protocol

    def setModel(self, model):
        """ sets model attribute """
        self._model = model

    def setParameters(self, params):
        """ seTs prameters """
        self._params = params

    def setMethod(self, action):
        """" sets method """
        self._method = self.varForMethod(action)

    def encode(self, command):
        """" ecodes command with selcted protocol """
        msg = {'protocol' : self._protocol, 'method' : self._method, 'model' : self._model}
        msg = {**msg, **self._params}
        return self.encode_packet(command, **msg)

    def methods(self, model):
        """ retruns metods available in a proticol """
        try:
            modname = "protocols.%s" % self._protocol
            func = getattr(self._module, "methods")
            self._methods = func(model)
            return self._methods
        except:
            """ passes if protocol is incomplete """
            _LOGGER.exception("Can not get methods for protocol %s, model <%s> modname, %s",
                              self._protocol, self._model, modname)

    def varForMethod(self, method):
        """ retruns int representation of method """
        try:
            modname = "protocols.%s" % self._protocol
            func = getattr(self._module, "method")
            self._method = func(method)
            return self._method
        except:
            _LOGGER.exception("Can not get methods for protocol %s, modname, %s",
                              self._protocol, modname)
            raise


    @staticmethod
    def _expect(condition):
        """ checks condition """
        if not condition:
            raise RuntimeError()


    @staticmethod
    def _encode_string(s):
        """
        encode a string

        >>> _encode_string("hello")
        '5:hello'

        >>> _encode_string("hellothere")
        'A:hellothere'

        >>> _encode_string("")
        '0:'

        >>> _encode_string(4711)
        Traceback (most recent call last):
            ...
        TypeError: object of type 'int' has no len()
        """
        return "%X%s%s" % (len(s), TAG_SEP, s)


    @staticmethod
    def _encode_integer(d):
        """
        encode a integer

        >>> _encode_integer(42)
        'i2as'

        >>> _encode_integer(-42)
        'i-2as'

        >>> _encode_integer(0)
        'i0s'

        >>> _encode_integer(3.3)
        'i3s'
        """
        return "%s%x%s" % (TAG_INTEGER, int(d), TAG_END)


    def _encode_dict(self, d):
        """
        encode a dict
        (keys will be put in sorted order)

        >>> _encode_dict({"foo": "bar", "baz": 42})
        'h3:bazi2as3:foo3:bars'

        >>> _encode_dict({})
        'hs'

        >>> _encode_dict([])
        Traceback (most recent call last):
            ...
        RuntimeError

        >>> _encode_dict(None)
        Traceback (most recent call last):
            ...
        RuntimeError
        """
        self._expect(isinstance(d, dict))

        return "%s%s%s" % (
            TAG_DICT,
            "".join(self._encode_any(x)
                    for keyval in sorted(d.items())
                    for x in keyval),
            TAG_END)


    @staticmethod
    def _encode_list(l):
        """ encodes list, not implemeted yet """
        raise NotImplementedError()


    def _encode_any(self, t):
        """ encodes any message """
        if isinstance(t, int):
            return self._encode_integer(t)
        elif isinstance(t, str):
            return self._encode_string(t)
        elif isinstance(t, dict):
            return self._encode_dict(t)
        elif isinstance(t, list):
            return self._encode_list(t)
        else:
            raise NotImplementedError()


    def encode_packet(self, command, **args):
        """
        encode a packet

        >>> encode_packet("hello", foo="x")
        b'5:helloh3:foo1:xs'

        >>> encode_packet("hello", data=dict(number=7))
        b'5:helloh4:datah6:numberi7sss'
        """
        res = self._encode_string(command)
        if args:
            res += self._encode_dict(args)
        return res.encode("ascii")


    def _decode_string(self, packet):
        """
        decode a string
        returns tuple (decoded string, rest of packet not consumed)

        >>> _decode_string("5:hello")
        ('hello', '')

        >>> _decode_string("5:hell")
        Traceback (most recent call last):
            ...
        RuntimeError

        >>> _decode_string("hello")
        Traceback (most recent call last):
            ...
        RuntimeError
        """
        sep = packet.find(TAG_SEP)
        self._expect(sep > 0)
        length = packet[:sep]
        length = int(length, 16)
        start = len(TAG_SEP) + sep
        end = start + length
        self._expect(end <= len(packet))
        val = packet[start:end]
        return val, packet[end:]


    def _decode_integer(self, packet):
        """
        decode an integer
        returns tuple (decoded integer, rest of packet not consumed)

        >>> _decode_integer("i4711s")
        (18193, '')

        >>> _decode_integer("i0s")
        (0, '')

        >>> _decode_integer("i-3s")
        (-3, '')

        >>> _decode_integer("i03s") # invalid according to specification
        (3, '')

        #Traceback (most recent call last):
        #    ...
        #RuntimeError

        >>> _decode_integer("i-0s") # invalid according to specification
        Traceback (most recent call last):
            ...
        RuntimeError

        # this is invalid according to specification but seems to be
        # generated anyway
        >>> _decode_integer("i0000000000s")
        (0, '')
        """
        self._expect(packet[0] == TAG_INTEGER)
        packet = packet[len(TAG_INTEGER):]
        end = packet.find(TAG_END)
        self._expect(end > 0)
        val = packet[:end]
        # disabled check since i0000000000s seems to be present
        # but invalid according to specification
        # _expect(val[0] != "0" or len(val) == 1)
        self._expect(val[0] != "-" or val[1] != "0")
        return int(val, 16), packet[end + len(TAG_END):]


    def _decode_dict(self, packet):
        """
        decode a dict
        returns tuple (decoded string, rest of packet not consumed)

        >>> _decode_dict("h3:foo3:bars")
        ({'foo': 'bar'}, '')
        """
        rest = packet[1:]
        d = {}

        while rest[0] != TAG_END:
            k, rest = self._decode_string(rest)
            v, rest = self._decode_any(rest)
            d[k] = v
        return d, rest[1:]


    def _decode_list(self, packet):
        """
        decode a list
        returns tuple (decoded list, rest of packet not consumed)

        """
        raise NotImplementedError()


    def _decode_any(self, packet):
        """
        decode a token
        """
        tag = packet[0]
        if tag == TAG_INTEGER:
            return self._decode_integer(packet)
        elif tag == TAG_DICT:
            return self._decode_dict(packet)
        elif tag == TAG_LIST:
            return self._decode_list(packet)
        else:
            return self._decode_string(packet)


    @staticmethod
    def _fixup(d):
        """
        Convenience method to let the protocol implementation use the key '_class'
        instead of 'class', which is a reserved word, as an argument to the dict
        constructor

        >>> _fixup(dict(a=1, _b=2)) == {'a': 1, 'b': 2}
        True
        """
        if d:
            for k in d:
                if k.startswith("_"):
                    d[k[1:]] = d.pop(k)
        return d


    def _decode(self, **packet):
        """
        dynamic lookup of the protocol implementation
        """

        protocol = packet["protocol"]
        try:
            modname = "protocols.%s" % protocol
            module = importlib.import_module(modname)
            func = getattr(module, "decode")
            return self._fixup(func(packet.copy()))
        except:
            SRC_URL = ("https://github.com/telldus/telldus/"
                       "tree/master/telldus-core/service")
            _LOGGER.exception("Can not decode protocol %s, packet <%s> "
                              "Missing or broken _decode in %s "
                              "Check %s for protocol implementation",
                              protocol, packet["data"],
                              modname, SRC_URL)
            raise


    def _decode_command(self, packet):
        """ decodes commad """
        command, rest = self._decode_any(packet)
        args, rest = self._decode_any(rest)
        self._expect(len(rest) == 0)
        self._expect(isinstance(command, str))
        self._expect(isinstance(args, dict))
        return command, args


    def decode_packet(self, packet):
        """
        decode a packet

        >>> packet = "7:RawDatah5:class6:sensor8:protocol\
        8:mandolyn5:model13:temperaturehumidity4:dataiAF1D466Bss"
        >>> decode_packet(packet)["data"]["temp"]
        20.4

        >>> packet = "7:RawDatah5:class6:sensor8:protocol\
        A:fineoffset4:datai488029FF9Ass"
        >>> decode_packet(packet)["data"]["temp"]
        4.1

        >>> packet = "7:RawDatah8:protocolC:everflourish4:dataiA1CC92ss"
        """
        try:
            command, args = self._decode_command(packet)
            if command == 'zwaveinfo':
                _LOGGER.info('Got Z-Wave info packet')
            elif command == "RawData":
                return self._decode(**args)
            else:
                raise NotImplementedError()
        except:
            _LOGGER.exception("failed to decode packet, skipping: %s", packet)
