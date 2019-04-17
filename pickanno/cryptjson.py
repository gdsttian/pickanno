#!/usr/bin/env python3

# Encrypt/decrypt string values in JSON files.

# NOTE: this is intended to keep secrets from collaborating users, not
# any dedicated attacker. Don't use for anything serious.


import sys
import os
import json

from getpass import getpass

from cryptography.fernet import Fernet, InvalidToken


def argparser():
    import argparse
    ap = argparse.ArgumentParser(
        description='Encrypt/decrypt string values in JSON files.')
    ap.add_argument('-e', '--encoding', default='utf-8')
    ap.add_argument('-p', '--password', default=None,
                    help='password (not safe, prompt by default)')
    ap.add_argument('mode', metavar='mode', choices=['encrypt', 'decrypt'],
                    help='"encrypt" or "decrypt"')
    ap.add_argument('names', metavar='name[,name...]',
                    help='names for values to encrypt or decrypt')
    ap.add_argument('file', nargs='+',
                    help='input JSON files')
    return ap


def derive_key(options):
    # mostly following https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/
    import base64
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    backend = default_backend()
    salt = b'O\x88C\x00)|\xc0h\xe3\xc1\xd4\xef#\x87D\xb7' # (yes, I know.)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=100000, backend=backend)
    key = kdf.derive(options.password.encode(options.encoding))
    return base64.urlsafe_b64encode(key)


def process_file(fn, codec, options):
    encoding = options.encoding
    with open(fn, encoding=encoding) as f:
        data = json.load(f)
    for n in options.names:
        if n in data:
            data[n] = codec(data[n].encode(encoding)).decode(encoding)
    print(json.dumps(data, indent=4, sort_keys=True))


def main(argv):
    args = argparser().parse_args(argv[1:])
    args.names = args.names.split(',')
    if args.password is None:
        args.password = getpass('password:')
    key = derive_key(args)
    cipher = Fernet(key)
    if args.mode == 'encrypt':
        codec = cipher.encrypt
    else:
        codec = cipher.decrypt
    for fn in args.file:
        try:
            process_file(fn, codec, args)
        except InvalidToken:
            print('error: invalid token (check password)', file=sys.stderr)
            break


if __name__ == '__main__':
    sys.exit(main(sys.argv))
