import datetime
import time
from tqdm import tqdm


def parse_timestamp(line):
    """Like 'date Mon Aug  6 10:12:56 2018'."""
    ss = line.split()
    assert ss[0] == 'date'
    text = ' '.join(ss[1:])
    x = datetime.datetime.strptime(text, '%a %b %d %H:%M:%S %Y')
    return time.mktime(x.timetuple())


def each_event_from_text(text):
    lines = text.split('\n')
    if not lines:
        return

    begin_ts = parse_timestamp(lines[0])
    if begin_ts is None:
        return

    for line in tqdm(text.split('\n')):
        ss = line.split()
        if not ss:
            continue

        try:
            rel_ts = float(ss[0])
        except:
            continue
        abs_ts = begin_ts + rel_ts

        try:
            assert ss[2].endswith('x')
            id = int(ss[2][:-1], 16)
        except:
            continue

        dlc = int(ss[5])
        if len(ss) != 6 + dlc:
            continue

        bb = []
        for s in ss[-dlc:]:
            n = int(s, 16)
            assert 0 <= n <= 255
            b = bytes((n,))
            bb.append(b)
        data = b''.join(bb)

        yield id, data, abs_ts, rel_ts


def each_event_from_file(f):
    text = open(f).read()
    for event in each_event_from_text(text):
        yield event


class Event(object):
    def __init__(self, id, data, abs_ts, rel_ts):
        self.id = id
        self.data = data
        self.abs_ts = abs_ts
        self.rel_ts = rel_ts


class ASC(object):
    @classmethod
    def from_text(cls, text):
        events = list(map(lambda args: Event(*args), each_event_from_text(text)))
        return cls(events)

    @classmethod
    def from_file(cls, filename):
        text = open(filename).read()
        return cls.from_text(text)

    def __init__(self, events):
        self.events = events
