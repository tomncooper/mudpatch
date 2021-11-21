""" This script allows the for the automatic merging of several patch branches into a new
output release branch. The patches are each housed in their own branch and a yaml config
file defined their details and the order they are merged into the output branch. """
import sys
import logging

from argparse import ArgumentParser, Namespace
from typing import List, Tuple
from pathlib import Path

from git import Repo
from git.exc import NoSuchPathError
from git.refs.head import Head

from mudpatch.patches import Patch, get_patches
from mudpatch.operations import get_patch_branches, merge_patches_into_output, create_output_branch

def create_parser() -> ArgumentParser:

    parser: ArgumentParser = ArgumentParser("Managing Up and Down (MUD) stream patches")

    parser.add_argument(
        "--repo", "-r", required=True, help="The path to the base repository."
    )

    parser.add_argument(
        "--base",
        "-b",
        required=True,
        help="The base tag or branch that patches will be applied too.",
    )

    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="The name of the new output branch for this patched version",
    )

    parser.add_argument(
        "--patches",
        "-p",
        required=True,
        help="Path to the patches configuration file.",
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

    parser.add_argument(
        "--cleanup",
        required=False,
        action="store_true",
        help=(
            "Flag indicating if, in the event of errors in the patch branch merging, "
            "the new output branch should be deleted."
        ),
    )

    return parser

def setup_logger(debug: bool=False) -> logging.Logger:

    top_log: logging.Logger = logging.getLogger("mudpatch")

    if debug:
        level = logging.DEBUG
        fmt = (
            "{levelname} | {name} | "
            "function: {funcName} "
            "| line: {lineno} | {message}"
        )
        style = "{"
    else:
        level = logging.INFO
        fmt = "{asctime} | {name} | {levelname} | {message}"
        style = "{"

    formatter: logging.Formatter = logging.Formatter(fmt, style=style)

    handler: logging.StreamHandler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    top_log.setLevel(level)
    top_log.addHandler(handler)

    return top_log


def run():
    """ Main run method for the mud tool"""

    parser: ArgumentParser = create_parser()
    args: Namespace = parser.parse_args()

    top_log: logging.Logger = setup_logger(args.debug)

    try:
        repo: Repo = Repo(args.repo)
    except NoSuchPathError as nspe:
        top_log.error("No such repository %s", nspe)
        sys.exit(1)

    patches_path: Path = Path(args.patches)
    try:
        patch_branches: List[Tuple[Patch, Head]] = get_patch_branches(
            repo, get_patches(patches_path)
        )
    except RuntimeError as err:
        top_log.error("%s", err)
        sys.exit(1)

    try:
        output_branch: Head = create_output_branch(repo, args.base, args.output)
    except RuntimeError as err:
        top_log.error("%s", err)
        sys.exit(1)

    result: bool = merge_patches_into_output(
        repo, output_branch, patch_branches, clean_up=args.cleanup
    )

    if result:
        top_log.info("Merging of patches has completed successfully")

if __name__ == "__main__":

    run()
