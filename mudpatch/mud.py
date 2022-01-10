""" This script allows the for the automatic merging of several patch branches into a new
output release branch. The patches are each housed in their own branch and a yaml config
file defined their details and the order they are merged into the output branch. """
import logging

from argparse import ArgumentParser, Namespace

from mudpatch.cli import create_parser
from mudpatch.commands import merge_init
from mudpatch.logs import setup_logger

VERSION: str = "2.0.0-SNAPSHOT"


def run():
    """Main run method for the mud tool"""

    parser: ArgumentParser = create_parser(VERSION)
    args: Namespace = parser.parse_args()

    top_log: logging.Logger = setup_logger(args.debug)

    top_log.info("Staring MUDpatch tool (%s)", VERSION)

    if args.subcommand == "merge":
        if args.merge_subcommand == "init":
            merge_init(args)


if __name__ == "__main__":

    run()
