"""
Transformer from async client code to sync one

Usage:
    python transform_to_sync.py src/annetbox/v37/client_async.py > src/annetbox/v37/client_sync.py
"""
import sys


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = f.read()
    else:
        data = sys.stdin.read()

    data = data.replace("annetbox.base.client_async", "annetbox.base.client_sync")
    data = data.replace("async ", "")
    data = data.replace("await ", "")
    print(data, end="")


if __name__ == '__main__':
    main()
