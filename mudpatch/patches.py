from typing import List, Dict
from pathlib import Path
from dataclasses import dataclass

import yaml

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


def to_patch(patch_dict: Dict[str, str]) -> Patch:
    """ Converts a dictionary to a Patch dataclass. 
    
    Parameters
    ----------
    patch_dict: dict
        A dictionary representing a single patch.
        
    Returns
    -------
    Patch
        An Patch instance containg the data from the supplied dict. 
    """

    return Patch(
        title=patch_dict["title"],
        description=patch_dict["description"],
        upstream_pr=patch_dict["upstreamPR"],
        downstream_branch=patch_dict["downstreamBranch"],
        fixed_version=patch_dict["fixedVersion"],
    )


def get_patches(patches_path: Path) -> List[Patch]:
    """ Loads the patches from the supplied patch config file path.
    
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

    with open(patches_path, "r") as path_file:
        patches_yaml = yaml.load(path_file, Loader=yaml.FullLoader)

    return [to_patch(patch) for patch in patches_yaml]