from argparse import ArgumentParser
from collections import Counter
import json

from cannot.ascfile import ASC
from cannot.dbcfile import J1939DBC


def parse_flags():
    a = ArgumentParser()
    a.add_argument('--dbc', type=str, required=True)
    a.add_argument('--asc', type=str, required=True)
    a.add_argument('--jsonl', type=str, required=True)
    return a.parse_args()


def test_j1939(j1939):
    id = 0x18f00430
    data = b'\xFF\xFF\xFF\x68\x13\xFF\xFF'
    decoding = j1939.decode(id, data)
    assert decoding.message.id == 61444
    assert decoding.message.name == 'EEC1'
    assert decoding.params['EngSpeed'] == 621


def json_dumps_bytes(b):
    return ''.join(map(lambda b: '%02X' % int(b), b))


def main(flags):
    j1939 = J1939DBC.from_file(flags.dbc)
    test_j1939(j1939)
    log = ASC.from_file(flags.asc)
    out = open(flags.jsonl, 'w')
    stats = Counter()
    for event in log.events:
        decoding = j1939.decode(event.id, event.data)
        if decoding:
            stats[decoding.message.name] += 1
        x = {
            'abs_ts': event.abs_ts,
            'rel_ts': event.rel_ts,
            'id': event.id,
            'data': json_dumps_bytes(event.data),
            'decoding': decoding.to_json() if decoding else None,
        }
        line = '%s\n' % json.dumps(x)
        out.write(line)
    out.close()
    print(stats)


if __name__ == '__main__':
    main(parse_flags())
