from typing import List, Optional, Union, Tuple

from git import Repo
from git.exc import GitCommandError
from git.refs.remote import RemoteReference
from git.refs.tag import TagReference
from git.refs.head import Head
from mudpatch.errors import BranchExistsError, MudPatchError, MultipleRemoteReferences, UnknownBranchError, UnknownReferenceError

from mudpatch.patches import Patch

# A list of options for the primary branch of a repository, the order dictates the order these options
# will be tried the first one found will be the one used as the fallback branch in case of clean up
PRIMARY_BRANCH_NAME_OPTIONS: List[str] = ["main", "master", "trunk"]

def get_local_head(repo: Repo, head_name: str) -> Optional[Head]:
    """ Searches for the specified head (branch) in the supplied repository instance.  
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
    repo: Repo, fallback_options: List[str] = PRIMARY_BRANCH_NAME_OPTIONS
) -> Head:
    """ Find the fallback (primary) branch in the supplied Repo instance using the 
    supplied list of primary branch name options. The first matching branch found in 
    the list will be returned.
    
    Parameters
    ----------
    repo : Repo
        The Repo instance representing the git repository we are working on.
    fallback_options : list
        A list of branch name strings to be searched for as fallback branches.

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
    print((f"Unable to find one of the defined fallback branches {fallback_options} in this repo. " 
           f"Falling back to the first branch in the head list: {fallback_head}"))
    return fallback_head


def get_tag(repo: Repo, tag_name: str) -> Optional[TagReference]:
    """ Gets the specified tag reference from the supplied Repo instance. If the tag cannot be found 
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
        The TagReference instance for the supplied tag name. If that cannot be found, None is returned.
    """

    for tag in repo.tags:
        if tag.name == tag_name:
            return tag

    return None


def get_local_base_object(repo: Repo, base: str) -> Union[Head, TagReference]:
    """ Find the supplied git reference object (head or tag) corresponding to the supplied base string.

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
        raise UnknownReferenceError(
            (
                f"The base reference {base} is not present as a branch or tag in the "
                f"{repo.working_dir} repository"
            )
        )

    return base_tag


def get_remote_ref(repo: Repo, ref_name: str, remote: Optional[str]=None) -> Optional[Head]:
    """ Find the reference corresponding to the supplied reference name in the remote repositories. If the 
    reference is found then a new branch based on it will be created and the corresponding Head instance
    returned. If the reference cannot be found in the remote repositories then None will be returned. The 
    search can optionally be limited to a single remote repository.

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
        print(f"Unable to find reference '{ref_name}' in remote repositories as none are configured")
        return None

    found_ref: Optional[RemoteReference] = None

    if remote:
        print(f"Searching for reference '{ref_name}' in remote repository {remote}")
        for remote_repo in repo.remotes:
            if remote_repo.name == remote:
                for remote_ref in remote_repo.refs:
                    if remote_ref.name.split("/")[-1] == ref_name:
                        found_ref = remote_ref
                        break
                break
    else:
        print(f"Searching all remote repositories for reference '{ref_name}'")
        found_refs: List[RemoteReference] = []

        for remote_repo in repo.remotes:
            for remote_ref in remote_repo.refs:
                if remote_ref.name.split("/")[-1] == ref_name:
                    found_refs.append(remote_ref)

        if len(found_refs) > 1:
            raise MultipleRemoteReferences(
                f"Found multiple references to {ref_name} in the configured remote repositories: {found_refs}")
        elif len(found_refs) == 1:
            found_ref = found_refs[0]
    
    if not found_ref:
        return None

    print(f"Found reference matching '{ref_name}' in remote {found_ref.name.split('/')[0]}")
    print(f"Creating local branch for {found_ref.name}")
    found_head = repo.create_head(ref_name, found_ref)
    found_head.set_tracking_branch(found_ref)

    return found_head


def create_output_branch(repo: Repo, base: str, output: str) -> Head:
    """ Creates a new branch labeled with the supplied output string based on the reference corresponding to the 
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

    base_object: Union[Head, TagReference] = get_local_base_object(repo, base)

    # Check if the output branch already exists
    existing_output_branch: Optional[Head] = get_local_head(repo, output)
    if existing_output_branch:
        raise BranchExistsError(
            (
                f"The output branch {output} is already present in the target "
                f"repository. Either remove this branch or choose a new output name."
            )
        )
    else:
        return repo.create_head(output, commit=base_object.commit)


def get_patch_branches(repo: Repo, patches: List[Patch]) -> List[Tuple[Patch, Head]]:
    """ Finds the branches in the supplied Repo instance corresponding to the supplied list of Patch instances.
    
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
            print(f"Unable to find patch branch '{patch.downstream_branch}' in the local repository. Searching the remote repositories.")
            patch_branch = get_remote_ref(repo, patch.downstream_branch)
            if not patch_branch:
                raise UnknownBranchError(
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
    """ Merges the branches in the supplied patch branches list into the supplied output branch. If the cleanup flag is set 
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
    debug : bool
        Flag indicating if debug messages should be printed.
    """

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