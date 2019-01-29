from argparse import ArgumentParser
from tqdm import tqdm


def parse_flags():
    a = ArgumentParser()
    a.add_argument('--in', type=str, required=True)
    a.add_argument('--out', type=str, required=True)
    return a.parse_args()


def force_ascii(text):
    cc = list(text)
    for i, c in enumerate(cc):
        if 255 < ord(c):
            cc[i] = '?'
    return ''.join(cc)


def main(flags):
    f = getattr(flags, 'in')
    text = open(f, 'rb').read().decode('latin-1')
    text = text.replace('\r\n', '\n')
    message_ids = []
    for line in text.split('\n'):
        ss = line.split()
        if not ss:
            continue
        if ss[0] != 'BO_':
            continue
        message_id = int(ss[1])
        message_ids.append(message_id)
    for message_id in tqdm(message_ids):
        pgn = (message_id >> 8) & 0xFFFF
        text = text.replace(str(message_id), str(pgn))
    with open(flags.out, 'w') as out:
        out.write(text)
    

if __name__ == '__main__':
    main(parse_flags())
