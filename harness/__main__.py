import argparse
import json
import sys

from .runner import (
    ExperimentError,
    discover_experiments,
    run_all,
    run_experiment,
    verify_all,
    verify_experiment,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run and verify HERESY-SOFA experiments.")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("list", help="list implemented experiments and placeholders")
    run_parser = commands.add_parser("run", help="execute one experiment")
    run_parser.add_argument("experiment_id")
    verify_parser = commands.add_parser("verify", help="verify one local receipt")
    verify_parser.add_argument("experiment_id")
    commands.add_parser("run-all", help="execute every implemented experiment")
    commands.add_parser("verify-all", help="verify receipts for implemented experiments")
    args = parser.parse_args(argv)

    try:
        if args.action == "list":
            for experiment in discover_experiments():
                print(
                    "{}  {:<11}  {}".format(
                        experiment["id"], experiment["status"], experiment["title"]
                    )
                )
            return 0
        if args.action == "run":
            return run_experiment(args.experiment_id)
        if args.action == "verify":
            return verify_experiment(args.experiment_id)
        if args.action == "run-all":
            return run_all()
        if args.action == "verify-all":
            return verify_all()
    except ExperimentError as error:
        print("harness: {}".format(error), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
