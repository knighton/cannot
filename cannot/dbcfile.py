import re
import struct


class Signal(object):
    def __init__(self, name, start_bit, size, is_little_endian, is_signed,
                 factor, offset, tmin, tmax, unit, int2str):
        self.name = name
        self.start_bit = start_bit
        self.size = size
        self.is_little_endian = is_little_endian
        self.is_signed = is_signed
        self.factor = factor
        self.offset = offset
        self.tmin = tmin
        self.tmax = tmax
        self.unit = unit
        self.int2str = int2str


class Message(object):
    def __init__(self, id, name, size, signals):
        self.id = id
        self.name = name
        self.size = size
        self.signals = signals


class Decoding(object):
    def __init__(self, message, params):
        self.message = message
        self.params = params

    def to_json(self):
        return {
            'message_id': self.message.id,
            'message_name': self.message.name,
            'params': self.params,
        }


def reverse_bytes(self, x):
    return ((x & 0xff00000000000000) >> 56) | \
        ((x & 0x00ff000000000000) >> 40) | \
        ((x & 0x0000ff0000000000) >> 24) | \
        ((x & 0x000000ff00000000) >> 8) | \
        ((x & 0x00000000ff000000) << 8) | \
        ((x & 0x0000000000ff0000) << 24) | \
        ((x & 0x000000000000ff00) << 40) | \
        ((x & 0x00000000000000ff) << 56)


class DBC(object):
    # https://github.com/ebroecker/canmatrix/blob/master/canmatrix/importdbc.py
    bo_re = re.compile(r"^BO\_ (\w+) (\w+) *: (\w+) (\w+)")
    sg_re = re.compile(
        r"^SG\_ (\w+) : (\d+)\|(\d+)@(\d+)([\+|\-]) \(([0-9.+\-eE]+),([0-9.+\-eE]+)\) " +
        "\[([0-9.+\-eE]+)\|([0-9.+\-eE]+)\] \"(.*)\" (.*)")
    sgm_re = re.compile(
        r"^SG\_ (\w+) (\w+) *: (\d+)\|(\d+)@(\d+)([\+|\-]) \(([0-9.+\-eE]+),([0-9.+\-eE]+)\) " +
        "\[([0-9.+\-eE]+)\|([0-9.+\-eE]+)\] \"(.*)\" (.*)")
    val_re = re.compile(r"VAL\_ (\w+) (\w+) (\s*[-+]?[0-9]+\s+\".+?\"[^;]*)")

    @classmethod
    def parse_bo_line(cls, line):
        x = cls.bo_re.match(line)
        if x is None:
            return None
        name = x.group(2)
        size = int(x.group(3))
        id = int(x.group(1), 0)
        return Message(id, name, size, [])

    @classmethod
    def parse_number(cls, x):
        if 'E' in x or 'e' in x:
            return float(x)
        elif '.' in x:
            return float(x)
        else:
            return int(x)

    @classmethod
    def parse_sg_line(cls, line):
        x = cls.sg_re.match(line)
        skip = 0
        if x is None:
            x = cls.sgm_re.match(line)
            skip = 1
        if x is None:
            return None
        name = x.group(1)
        start_bit = int(x.group(skip + 2))
        signal_size = int(x.group(skip + 3))
        is_little_endian = int(x.group(skip + 4))==1
        is_signed = x.group(skip + 5)=='-'
        factor = cls.parse_number(x.group(skip + 6))
        offset = cls.parse_number(x.group(skip + 7))
        tmin = cls.parse_number(x.group(skip + 8))
        tmax = cls.parse_number(x.group(skip + 9))
        unit = x.group(skip + 10)
        return Signal(name, start_bit, signal_size, is_little_endian, is_signed,
                      factor, offset, tmin, tmax, unit, None)

    @classmethod
    def parse_enum_values(cls, s):
        ss = s.split('"')[:-1]
        ss = list(map(lambda s: s.strip(), ss))
        key2value = {}
        for i, s in enumerate(ss):
            if not i % 2:
                key = int(s)
            else:
                key2value[key] = s
        return key2value

    @classmethod
    def parse_val_line(cls, line):
        x = cls.val_re.match(line)
        if x is None:
            return None
        id = int(x.group(1), 0)
        name = x.group(2)
        return cls.parse_enum_values(x.group(3))

    @classmethod
    def from_text(cls, text):
        id2message = {}
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            head = line.split()[0]
            if head == 'BO_':
                message = cls.parse_bo_line(line)
                if not message:
                    continue
                id2message[message.id] = message
            elif head == 'SG_':
                signal = cls.parse_sg_line(line)
                if not signal:
                    continue
                id2message[message.id].signals.append(signal)
            elif head == 'VAL_':
                int2str = cls.parse_val_line(line)
                if not int2str:
                    continue
                id2message[message.id].int2str = int2str
            else:
                continue
        for message in id2message.values():
            message.signals.sort(key=lambda x: x.start_bit)
        return cls(id2message)

    @classmethod
    def from_file(cls, filename):
        text = open(filename).read()
        return cls.from_text(text)

    def __init__(self, id2message):
        self.id2message = id2message
        self.name2id = {}
        for id, message in id2message.items():
            self.name2id[message.name] = id

    def encode(self, id_or_name, name2value):
        if isinstance(id_or_name, int):
            id = id_or_name
        elif isinstance(id_or_name, str):
            id = self.name2id.get(id_or_name)
            if id is None:
                return None
        else:
            assert False
        message = self.id2message.get(id)
        if not message:
            return None
        ret = 0
        for signal in message.signals:
            x = name2value.get(signal.name)
            if x is None:
                continue
            b2 = signal.size
            if signal.is_little_endian:
                b1 = signal.start_bit
            else:
                b1 = (signal.start_bit // 8) * 8 + (-signal.start_bit - 1) % 8
            b0 = 64 - (b1 + signal.size)
            x = (x // signal.factor) - signal.offset
            x = int(round(x))
            if signal.is_signed and x < 0:
                x = (1 << b2) + x
            shift = b1 if signal.is_little_endian else b0
            mask = ((1 << b2) - 1) << shift
            x = (x & ((1 << b2) - 1)) << shift
            if signal.is_little_endian:
                mask = self.reverse_bytes(mask)
                x = self.reverse_bytes(x)
            ret &= ~mask
            ret |= x
        ret = struct.pack('>Q', ret)
        return ret[:message.size]

    def decode(self, id, data):
        message = self.id2message.get(id)
        if not message:
            return None
        st = data.ljust(8, b'\x00')
        le = None
        be = None
        name2value = {}
        for signal in message.signals:
            b2 = signal.size
            if signal.is_little_endian:
                b1 = signal.start_bit
            else:
                b1 = (signal.start_bit // 8) * 8 + (-signal.start_bit - 1) % 8
            b0 = 64 - (b1 + signal.size)
            if signal.is_little_endian:
                if le is None:
                    le = struct.unpack('<Q', st)[0]
                shift_amount = b1
                x = le
            else:
                if be is None:
                    be = struct.unpack('>Q', st)[0]
                shift_amount = b0
                x = be
            if shift_amount < 0:
                continue
            x = (x >> shift_amount) & ((1 << b2) - 1)
            if signal.is_signed and (x >> (b2 - 1)):
                x -= (1 << b2)
            x = x * signal.factor + signal.offset
            name2value[signal.name] = x
        return Decoding(message, name2value)


class J1939DBC(DBC):
    def __init__(self, id2message):
        DBC.__init__(self, id2message)

    def encode(self, id_or_name, name2value):
        return DBC.encode(self, id_or_name, name2value)

    def decode(self, id, data):
        pgn = (id >> 8) & 0xFFFF
        return DBC.decode(self, pgn, data)
