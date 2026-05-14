"""
Fixture: Standalone script with __main__ entry point.

Reachable via __main__:
  - main
  - called_from_main (called by main)

Unreachable:
  - never_called
  - also_dead (called only by never_called)
"""

import os


def main():
    result = called_from_main("hello")
    print(result)


def called_from_main(data):
    # ACR-QA-TEST: reachable function
    return os.popen(data).read()  # noqa: S605


def never_called():
    # ACR-QA-TEST: dead code (unreachable)
    return also_dead()


def also_dead():
    # ACR-QA-TEST: unreachable via never_called
    import pickle

    return pickle.loads(b"")  # noqa: S301


if __name__ == "__main__":
    main()
