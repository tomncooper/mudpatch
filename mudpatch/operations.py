"""This module contains methods which perform the patch merging operations."""
import logging

from typing import List, Optional, Union, Tuple
from pathlib import Path

from git import Repo
from git.exc import CommandError
from git.refs.remote import RemoteReference
from git.refs.tag import TagReference
from git.refs.head import Head
from mudpatch.errors import (
    CheckoutError,
    CommitError,
    BranchExistsError,
    MudPatchError,
    MultipleRemoteReferences,
    UnknownBranchError,
    UnknownReferenceError,
)

from mudpatch.patches import Patch, write_patches_to_file

LOG: logging.Logger = logging.getLogger(__name__)
DEFAULT_PATCH_CONFIG_FILENAME = "patches-config.yaml"


def get_local_head(repo: Repo, head_name: str) -> Optional[Head]:
    """Searches for the specified head (branch) in the supplied repository instance.
    If the head cannot be found the method will return None.

    Parameters
    ----------
    repo : Repo
        The Repo instance represeting the git repository we are working on.
    head_name : str
        The name of the head (branch) that will be searched for.

    Returns
    -------
    Head
        If the supplied head name is found then a Head instance will be returned, if not then None.
    """

    for head in repo.heads:
        if head.name == head_name:
            return head

    return None


def get_fallback_head(
    repo: Repo, fallback_options: List[str] = ["main", "master", "trunk"]
) -> Head:
    """Find the fallback (primary) branch in the supplied Repo instance using the
    supplied list of primary branch name options. The first matching branch found in
    the list will be returned.

    Parameters
    ----------
    repo : Repo
        The Repo instance representing the git repository we are working on.
    fallback_options : list
        A list of branch name strings to be searched for as fallback branches. The default
        list is 'main', 'master' and 'trunk.

    Returns:
    Head
        A head instance for the first branch found in the supplied fallback_options list.
        If none of the branch in the fallback list can be found the 1st head in the
        head (branches) list will be returned.
    """

    fallback_head: Optional[Head]
    for fallback in fallback_options:
        fallback_head = get_local_head(repo, fallback)
        if fallback_head:
            return fallback_head

    fallback_head = repo.heads[0]
    LOG.warning(
        (
            "Unable to find one of the defined fallback branches %s in this repo. "
            "Falling back to the first branch in the head list: %s"
        ),
        fallback_options,
        fallback_head,
    )
    return fallback_head


def get_tag(repo: Repo, tag_name: str) -> Optional[TagReference]:
    """Gets the specified tag reference from the supplied Repo instance. If the tag cannot be found
    then None is returned.

    Parameters
    ----------
    repo : Repo
        The Repo instance representing the git repository we are working on.
    tag_name : str
        The name of the tag to be searched for.

    Returns
    -------
    TagReference
        The TagReference instance for the supplied tag name. If that cannot be found,
        None is returned.
    """

    for tag in repo.tags:
        if tag.name == tag_name:
            return tag

    return None


def get_local_base_object(repo: Repo, base: str) -> Union[Head, TagReference]:
    """Find the supplied git reference object (head or tag) corresponding to the supplied base string.

    Parameters
    ----------
    repo : Repo
        The Repo instance representing the git repository we are working on.
    base : str
        The name of the git reference we are searching for.

    Returns
    ------
    Head or TagReference
        Depending on what the base object is either a Head (branch) or TagReference (tag) will be returned.

    Throws
    ------
    UnknownReferenceError
        If the supplied base string does not correspond to either a branch or tag in the supplied Repo instance.
    """

    # See if this is a branch
    base_branch: Optional[Head] = get_local_head(repo, base)

    if not base_branch:
        base_tag: Optional[TagReference] = get_tag(repo, base)
    else:
        return base_branch

    if not base_tag:
        err_msg: str = (
            f"The base reference {base} is not present as a branch or tag in the "
            f"{repo.working_dir} repository"
        )
        LOG.error(err_msg)
        raise UnknownReferenceError(err_msg)

    return base_tag


def get_remote_ref(
    repo: Repo, ref_name: str, remote: Optional[str] = None
) -> Optional[Head]:
    """Find the reference corresponding to the supplied reference name in the remote repositories. If the
    reference is found then a new branch based on it will be created and the corresponding Head instance returned. If the reference cannot be found in the remote repositories then None will be returned. The search can optionally be limited to a single remote repository.

    Parameters
    ----------
    repo : Repo
        The Repo instance representing the git repository we are working on.
    ref_name : str
        The name of the git reference we are searching for.
    remote : str
        Allows a specific remote repository to be searched. If this is not supplied then all configured remote
        repositories will be searched.

    Returns
    -------
    Head or None
        If a reference can be found in the configured remote repositories a new branch will be created from
        that reference and the Head instance returned. If no reference can be found then None will be returned.

    Throws
    ------
    MultipleRemoteReferences
        If the reference exists in multiple remote repositories.
    """

    if not repo.remotes:
        LOG.warning(
            "Unable to find reference '%s' in remote repositories as none are configured",
            ref_name,
        )
        return None

    found_ref: Optional[RemoteReference] = None

    if remote:
        LOG.info(
            "Searching for reference '%s' in remote repository %s", ref_name, remote
        )
        for remote_repo in repo.remotes:
            if remote_repo.name == remote:
                for remote_ref in remote_repo.refs:
                    if remote_ref.name.split("/")[-1] == ref_name:
                        found_ref = remote_ref
                        break
                break
    else:
        LOG.info("Searching all remote repositories for reference '%s'", ref_name)
        found_refs: List[RemoteReference] = []

        for remote_repo in repo.remotes:
            for remote_ref in remote_repo.refs:
                if remote_ref.name.split("/")[-1] == ref_name:
                    found_refs.append(remote_ref)

        if len(found_refs) > 1:
            err_msg: str = f"Found multiple references to {ref_name} in the configured remote repositories: {found_refs}"
            LOG.error(err_msg)
            raise MultipleRemoteReferences(err_msg)
        elif len(found_refs) == 1:
            found_ref = found_refs[0]

    if not found_ref:
        return None

    LOG.info(
        "Found reference matching '%s' in remote %s",
        ref_name,
        found_ref.name.split("/")[0],
    )
    LOG.info("Creating local branch for %s", found_ref.name)
    found_head = repo.create_head(ref_name, found_ref)
    found_head.set_tracking_branch(found_ref)

    return found_head


def checkout_branch(branch: Head) -> None:
    """Checks out the supplied Head object adding logging and error handling.

    Parameters
    ----------
    branch : Head
        The git head object to be checked out.

    Throws
    ------
    CheckoutError
        If the underlying git checkout command throws a CommandError.
    """

    LOG.debug("Checking out branch: %s", branch.name)
    try:
        branch.checkout()
    except CommandError as comm_err:
        checkout_msg: str = f"Checkout of {branch.name} failed"
        LOG.error(checkout_msg)
        LOG.error(comm_err)
        raise CheckoutError(checkout_msg, comm_err) from comm_err
    else:
        LOG.debug("Checking out of branch %s was successful", branch.name)


def create_output_branch(repo: Repo, base: str, output: str) -> Head:
    """Creates a new branch labeled with the supplied output string based on the reference corresponding to the
    supplied base string.

    Parameters
    ----------
    repo : Repo
        The Repo instance representing the git repository we are working on.
    base : str
        The name of the git reference (branch or tag) to base the new branch on.
    output : str
        The name of the newly created branch.

    Returns
    -------
    Head
        A Head instance corresponding to the newly created branch.

    Throws
    ------
    BranchExistsError
        If the output branch already exists or the base reference does not exist.
    """

    LOG.info("Creating new branch %s based on %s", output, base)

    base_object: Union[Head, TagReference] = get_local_base_object(repo, base)

    # Check if the output branch already exists
    existing_output_branch: Optional[Head] = get_local_head(repo, output)
    if existing_output_branch:
        err_msg: str = (
            f"The output branch {output} is already present in the target "
            f"repository. Either remove this branch or choose a new output name."
        )
        LOG.error(err_msg)
        raise BranchExistsError(err_msg)
    else:
        return repo.create_head(output, commit=base_object.commit)


def write_patch_config_to_branch(
    repo: Repo,
    branch: Head,
    patches: List[Patch],
    config_filename: str = DEFAULT_PATCH_CONFIG_FILENAME,
) -> None:
    """Writes the supplied list of Patch objects to a yaml file in the supplied repository and
    commits the file to the branch supplied.

    Parameters
    ----------
    repo : Repo
        The Repo instance representing the git repository we are working on.
    branch : Head
        The Head instance representing the branch the patches file should be committed to.
    patches : List[Patch]
        The list of Patch instances to be converted to yaml and committed to the specified branch.
    config_filename : str
        The name of the yaml file to be saved to the specified branch.

    Throws
    ------
    CommitError
        If the committing of the yaml file fails.
    """

    if repo.working_dir:
        output_filepath: Path = Path(repo.working_dir, config_filename)
    else:
        msg: str = "The supplied repository has no working directory"
        LOG.error(msg)
        raise MudPatchError(msg)

    checkout_branch(branch)

    LOG.info("Commiting patch configuration file to output branch: %s", branch.name)

    write_patches_to_file(patches, output_filepath)

    try:
        repo.git.add(output_filepath)
        commit_output: str = repo.git.commit(message="Added patches configuration file")
        LOG.debug(commit_output)
    except CommandError as comm_err:
        err_msg: str = "Encountered error committing the patches configuration file"
        LOG.error(err_msg)
        LOG.error(comm_err)
        raise CommitError(err_msg, comm_err) from comm_err
    else:
        LOG.info(
            "Successfully committed patches configuration file to branch: %s",
            branch.name,
        )


def get_patch_branches(repo: Repo, patches: List[Patch]) -> List[Tuple[Patch, Head]]:
    """Finds the branches in the supplied Repo instance corresponding to the supplied list of Patch instances.

    Parameters
    ----------
    repo : Repo
        The Repo instance representing the git repository we are working on.
    patches : list
        A list of Patch instances.

    Returns
    -------
    list
        A list of tuples, each with a Patch instance and the Head instance pointing to a branch in the supplied Repo
        corresponding to the Patch's "downstream branch" value.

    Throws
    ------
    UnknownBranchError
        If any of the "downstream branch" values, of the supplied patches, cannot be found locally in the supplied
        Repo instance or in any of the configure remote repositories.
    """

    patch_branches: List[Tuple[Patch, Head]] = []

    for patch in patches:
        patch_branch: Optional[Head] = get_local_head(repo, patch.downstream_branch)
        if not patch_branch:
            LOG.info(
                "Unable to find patch branch '%s' in the local repository. Searching the remote repositories.",
                patch.downstream_branch,
            )
            patch_branch = get_remote_ref(repo, patch.downstream_branch)
            if not patch_branch:
                err_msg: str = (
                    f"Branch {patch.downstream_branch} for patch {patch.title} "
                    f"does not exist"
                )
                LOG.error(err_msg)
                raise UnknownBranchError(err_msg)

        patch_branches.append((patch, patch_branch))

    return patch_branches


def merge_patches_into_output(
    repo: Repo,
    output_branch: Head,
    patch_branches: List[Tuple[Patch, Head]],
    clean_up: bool = False,
) -> bool:
    """Merges the branches in the supplied patch branches list into the supplied output branch. If the cleanup flag is set
    then any resulting errors in the merge process will be cleaned up by aborting the merge, moving to the primary fallback
    branch (eg main) and deleting the output branch. If cleanup is false (default) the new output branch will be left in
    merging state.

    Parameters
    ----------
    repo : Repo
        The Repo instance representing the git repository we are working on.
    output_branch : Head
        The Head instance corresponding to the output branch that the patches will be merged into.
    patch_branches : list
        A list of tuples, each with a Patch instance and the Head instance pointing to a branch corresponding to the
        Patch's "downstream branch" value.
    clean_up : bool
        If cleanup is set to True then any resulting errors in the merge process will be cleaned up by aborting the merge,
        moving to the primary fallback branch (eg main) and deleting the output branch. If cleanup is false (default) the new
        output branch will be left in merging state.

    Returns
    -------
    bool
        True if no errors were encountered, false otherwise.
    """

    LOG.info("Merging patch branches into output branch %s", output_branch.name)

    try:
        checkout_branch(output_branch)
    except CheckoutError:
        return False

    for _, patch_branch in patch_branches:
        LOG.info("Merging branch %s", patch_branch.name)
        try:
            merge_text: str = repo.git.merge(patch_branch)
        except CommandError as comm_err:
            LOG.error("Merge of %s failed", patch_branch.name)
            LOG.error(comm_err)
            if clean_up:
                LOG.info("Cleaning up:")
                LOG.info("Aborting merge")
                repo.git.merge(abort=True)
                fallback_head: Head = get_fallback_head(repo)
                LOG.info("Falling back to branch: %s", fallback_head.name)
                fallback_head.checkout()
                LOG.info("Deleting output branch: %s", output_branch.name)
                repo.git.branch("-D", output_branch)
            return False
        else:
            LOG.debug(merge_text)

    return True
