import sys

from src.billing import calc_total


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    items = [{"price": float(v)} for v in argv]
    print(f"total: {calc_total(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
