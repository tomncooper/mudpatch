"""This module contains methods for creating the command line interface parser."""
from argparse import ArgumentParser


def create_parser(version: str) -> ArgumentParser:
    """Creates the Argument Parser instance for the command line interface."""

    parser: ArgumentParser = ArgumentParser(
        f"Managing Up and Down (MUD) stream patches ({version})"
    )

    parser.add_argument(
        "--debug",
        required=False,
        action="store_true",
        help=(
            "Flag indicating if debug level information (including debug logging and "
            "raw git output) should be displayed"
        ),
    )

    main_subparser = parser.add_subparsers(title="subcommands", dest="subcommand")
    setup_merge_command(main_subparser)

    return parser


def setup_merge_command(main_subparser):
    """Setup the top level merge command line option."""

    merge_parser = main_subparser.add_parser(
        "merge", help="Command for performing the merging of patch branches"
    )
    merge_subparser = merge_parser.add_subparsers(dest="merge_subcommand")
    setup_merge_init_command(merge_subparser)


def setup_merge_init_command(merge_subparser):
    """Setup the init command line option for the merge command."""

    merge_init_parser = merge_subparser.add_parser(
        "init", help="Command for initiating a patch merge"
    )

    merge_init_parser.add_argument("repo", help="The path to the base repository.")

    merge_init_parser.add_argument(
        "base",
        help="The base tag or branch that patches will be applied too.",
    )

    merge_init_parser.add_argument(
        "output",
        help="The name of the new output branch for this patched version",
    )

    merge_init_parser.add_argument(
        "patches",
        help="Path to the patches configuration file.",
    )

    merge_init_parser.add_argument(
        "--cleanup",
        required=False,
        action="store_true",
        help=(
            "Flag indicating if, in the event of errors in the patch branch merging, "
            "the new output branch should be deleted."
        ),
    )
