""" This module contains methods that deal with the patches configuration file"""
import logging

from typing import List, Dict
from pathlib import Path
from dataclasses import dataclass

import yaml

LOG: logging.Logger = logging.getLogger(__name__)


@dataclass
class Patch:
    """Class representing a single patch.

    Attributes
    ----------
    title : str
        A short title for this patch. It should be unique for example an issue reference.
    description : str
        A short description of what the patch adds and/or fixes.
    upstream_pr : str
        A link to the upstream PR this patch is derived from.
    downstream_branch : str
        The branch that contains the patch.
    fixed_version : str
        The upstream version that contains this patch.
    """

    title: str
    description: str
    upstream_pr: str
    downstream_branch: str
    fixed_version: str


def from_dict_to_patch(patch_dict: Dict[str, str]) -> Patch:
    """Converts a dictionary to a Patch dataclass.

    Parameters
    ----------
    patch_dict: dict
        A dictionary representing a single patch.

    Returns
    -------
    Patch
        An Patch instance containing the data from the supplied dict.
    """

    return Patch(
        title=patch_dict["title"],
        description=patch_dict["description"],
        upstream_pr=patch_dict["upstreamPR"],
        downstream_branch=patch_dict["downstreamBranch"],
        fixed_version=patch_dict["fixedVersion"],
    )


def from_patch_to_dict(patch: Patch) -> Dict[str, str]:
    """Converts a Patch dataclass into a plain python dictionary.

    Parameters
    ----------
    patch: Patch
        A Patch instance to be converted.

    Returns
    -------
    dict
        A dictionary representing the data from the supplied patch instance.
    """

    patch_dict = {}

    patch_dict["title"] = patch.title
    patch_dict["description"] = patch.description
    patch_dict["upstreamPR"] = patch.upstream_pr
    patch_dict["downstreamBranch"] = patch.downstream_branch
    patch_dict["fixedVersion"] = patch.fixed_version

    return patch_dict


def get_patches(patches_path: Path) -> List[Patch]:
    """Loads the patches from the supplied patch config file path and returns a list
    of Patch dataclass instances.

    Parameters
    ----------
    patches_path : Path
        pathlib.Path instance pointing to the patches config file.

    Returns
    -------
    list
        A list of Patch instances represeting the patches defined in the supplied
        patches file.
    """

    LOG.info("Loading patches from configuration file: %s", patches_path.absolute())

    with open(patches_path, "r", encoding="utf8") as path_file:
        patches_yaml = yaml.load(path_file, Loader=yaml.FullLoader)

    return [from_dict_to_patch(patch) for patch in patches_yaml]


def write_patches_to_file(patches: List[Patch], output_filepath: Path) -> None:
    """Writes the supplied list of Patch objects to a yaml file at the specified output filepath.

    Parameters
    ----------
    patches: List[Patch]
        A list of Patch instances to be converted to a yaml file.

    Returns
    -------
    list
        A list of Patch instances representing the patches defined in the supplied
        patches file.
    """

    patch_dicts = [from_patch_to_dict(patch) for patch in patches]

    with open(output_filepath, "w", encoding="utf8") as output_file:
        yaml.dump(patch_dicts, output_file, sort_keys=False)
