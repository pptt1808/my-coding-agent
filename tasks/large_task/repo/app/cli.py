import sys
from .service import add_task, sort_by_priority


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m app.cli add <title> | list [--priority]")
        return 1
    # TODO: handle a --priority flag that prints tasks sorted by priority
    actions = {"add": lambda: add_task([], " ".join(argv[1:])), "list": lambda: []}
    if argv[0] not in actions:
        print(f"unknown action: {argv[0]}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
