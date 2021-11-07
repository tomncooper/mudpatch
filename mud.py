""" This script allows the for the automatic merging of several patch branches into a new
output release branch. The patches are each housed in their own branch and a yaml config
file defined their details and the order they are merged into the output branch. """
import sys
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path

import yaml
from git import Repo
from git.exc import NoSuchPathError, GitCommandError
from git.refs.tag import TagReference
from git.refs.head import Head

MAIN_BRANCH_NAME_OPTIONS: List[str] = ["main", "master", "trunk"]


@dataclass
class Patch:
    """Class representing a single patch"""

    # A short title for this patch. It should be unique for example an issue reference.
    title: str
    # A short description of what the patch adds and/or fixes.
    description: str
    # A link to the upstream PR this patch is derived from.
    upstream_pr: str
    # The branch that contains the patch.
    downstream_branch: str
    # The upstream version that contains this patch.
    fixed_version: str


def to_patch(patch_dict: Dict[str, str]) -> Patch:

    return Patch(
        title=patch_dict["title"],
        description=patch_dict["description"],
        upstream_pr=patch_dict["upstreamPR"],
        downstream_branch=patch_dict["downstreamBranch"],
        fixed_version=patch_dict["fixedVersion"],
    )


def get_patches(patches_path: Path) -> List[Patch]:

    with open(patches_path, "r") as path_file:
        patches_yaml = yaml.load(path_file, Loader=yaml.FullLoader)

    return [to_patch(patch) for patch in patches_yaml]


def get_head(repo: Repo, head_name: str) -> Optional[Head]:

    for head in repo.heads:
        if head.name == head_name:
            return head

    return None


def get_fallback_head(
    repo: Repo, fallback_options: List[str] = MAIN_BRANCH_NAME_OPTIONS
) -> Head:

    fallback_head: Optional[Head]
    for fallback in fallback_options:
        fallback_head = get_head(repo, fallback)
        if fallback_head:
            return fallback_head

    return repo.heads[0]


def get_tag(repo: Repo, tag_name: str) -> Optional[TagReference]:

    for tag in repo.tags:
        if tag.name == tag_name:
            return tag

    return None


def get_base_object(repo: Repo, base: str) -> Union[Head, TagReference]:

    # See if this is branch
    base_branch: Optional[Head] = get_head(repo, base)

    if not base_branch:
        base_tag: Optional[TagReference] = get_tag(repo, base)
    else:
        return base_branch

    if not base_tag:
        raise RuntimeError(
            (
                f"The base reference {base} is not present as a branch or tag in the "
                f"{repo.working_dir} repository"
            )
        )

    return base_tag


def create_output_branch(repo: Repo, base: str, output: str) -> Head:

    base_object: Union[Head, TagReference] = get_base_object(repo, base)

    # Check if the output branch already exists
    existing_output_branch: Optional[Head] = get_head(repo, output)
    if existing_output_branch:
        raise RuntimeError(
            (
                f"The output branch {output} is already present in the target "
                f"repository. Either remove this branch or choose a new output name."
            )
        )
    else:
        return repo.create_head(output, commit=base_object.commit)


def get_patch_branches(repo: Repo, patches: List[Patch]) -> List[Tuple[Patch, Head]]:

    patch_branches: List[Tuple[Patch, Head]] = []

    for patch in patches:
        patch_branch: Optional[Head] = get_head(repo, patch.downstream_branch)
        if not patch_branch:
            # TODO: Check if the branch is available in one of the remote repositories
            raise IndexError(
                (
                    f"Branch {patch.downstream_branch} for patch {patch.title} "
                    f"does not exist"
                )
            )

        patch_branches.append((patch, patch_branch))

    return patch_branches


def merge_patches_into_output(
    repo: Repo,
    output_branch: Head,
    patch_branches: List[Tuple[Patch, Head]],
    clean_up: bool = False,
    debug: bool = False,
) -> None:

    print(f"Checking out the output branch: {output_branch.name}")
    try:
        output_branch.checkout()
    except GitCommandError as gcerr:
        print(f"Error: checkout of {output_branch.name} failed")
        print("-------------------------------------------")
        print(gcerr)
        print("-------------------------------------------")
        return None

    for _, patch_branch in patch_branches:
        print(f"Merging {patch_branch.name}")
        try:
            merge_text: str = repo.git.merge(patch_branch)
        except GitCommandError as gcerr:
            print(f"Error: merge of {patch_branch.name} failed")
            print("-------------------------------------------")
            print(gcerr)
            print("-------------------------------------------")
            if clean_up:
                print("Cleaning up:")
                print("Aborting merge")
                repo.git.merge(abort=True)
                fallback_head: Head = get_fallback_head(repo)
                print(f"Falling back to branch: {fallback_head.name}")
                fallback_head.checkout()
                print(f"Deleting output branch: {output_branch.name}")
                repo.git.branch("-D", output_branch)
            return None
        else:
            if debug:
                print(merge_text)


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


if __name__ == "__main__":

    PARSER: ArgumentParser = create_parser()
    ARGS: Namespace = PARSER.parse_args()

    try:
        REPO: Repo = Repo(ARGS.repo)
    except NoSuchPathError as nspe:
        print(f"Error: No such repository {nspe}")
        sys.exit(1)

    PATCHES_PATH: Path = Path(ARGS.patches)
    print(f"Loading patches from configuration file: {PATCHES_PATH.absolute()}")
    try:
        PATCH_BRANCHES: List[Tuple[Patch, Head]] = get_patch_branches(
            REPO, get_patches(PATCHES_PATH)
        )
    except RuntimeError as err:
        print(f"Error: {err}")
        sys.exit(1)

    print(f"Creating new branch {ARGS.output} based on {ARGS.base}")
    try:
        OUTPUT_BRANCH: Head = create_output_branch(REPO, ARGS.base, ARGS.output)
    except RuntimeError as err:
        print(f"Error: {err}")
        sys.exit(1)

    merge_patches_into_output(
        REPO, OUTPUT_BRANCH, PATCH_BRANCHES, debug=ARGS.debug, clean_up=ARGS.cleanup
    )
