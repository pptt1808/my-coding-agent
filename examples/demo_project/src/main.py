import sys

from src.stats import mean


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python main.py [--stats] <numbers...>")
        return 1
    if "--stats" in argv:
        argv = [a for a in argv if a != "--stats"]
        nums = [float(a) for a in argv]
        print(f"mean: {mean(nums)}")
        # TODO: also print variance and median when --stats is given
        return 0
    nums = [float(a) for a in argv]
    print(f"mean: {mean(nums)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
