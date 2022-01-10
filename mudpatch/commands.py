import logging
import sys

from argparse import Namespace
from typing import List, Tuple
from pathlib import Path

from git import Repo
from git.exc import NoSuchPathError
from git.refs.head import Head

from mudpatch.patches import Patch, get_patches
from mudpatch.git_operations import (
    get_patch_branches,
    merge_patches_into_output,
    create_output_branch,
    write_patch_config_to_branch,
)

LOG: logging.Logger = logging.getLogger(__name__)


def merge_init(args: Namespace):
    """Logic for running the init option of the merge subcommand."""

    LOG.info("Initializing patch branch merge")

    try:
        repo: Repo = Repo(args.repo)
    except NoSuchPathError as nspe:
        LOG.error("No such repository %s", nspe)
        sys.exit(1)

    patches_path: Path = Path(args.patches)
    patches: List[Patch] = get_patches(patches_path)

    try:
        patch_branches: List[Tuple[Patch, Head]] = get_patch_branches(repo, patches)
    except RuntimeError as err:
        LOG.error("%s", err)
        sys.exit(1)

    try:
        output_branch: Head = create_output_branch(repo, args.base, args.output)
    except RuntimeError as err:
        LOG.error("%s", err)
        sys.exit(1)

    try:
        write_patch_config_to_branch(repo, output_branch, patches)
    except RuntimeError as err:
        LOG.error("%s", err)
        sys.exit(1)

    result: bool = merge_patches_into_output(
        repo, output_branch, patch_branches, clean_up=args.cleanup
    )

    if result:
        LOG.info("Merging of patches has completed successfully")
