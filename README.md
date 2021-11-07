# MUDpatch: Managing Upstream and Downstream patches 

A tool for managing a collection of downstream patches applied to an upstream tag/branch.

## Installation

For development, `poetry` can be used to create a virtual environment:

```bash
poetry install
```

The script can then be run by calling:

```bash
poetry run python mud.py --help
```

## Patch Configuration

Mud works by merging a set of patch branches on top of a base branch or tag. The list of 
patches is defined in a yaml file with the following format:

```yaml
- title: patch-1
  description: The first patch
  upstreamPR: https://bithub.com/org/repo/1
  downstreamBranch: patch-1-1.0.0
  fixedVersion: 1.1.0
- title: patch-2
  description: The second patch
  upstreamPR: https://bithub.com/org/repo/2
  downstreamBranch: patch-2-1.0.0
  fixedVersion: 1.1.0
```

## Usage

Mud requires several arguments:
- `--repo` is the path to the repository you wish to run operations on. 
- `--base` defines the base branch or tag that the patches will be merged on top of. 
- `--ouput` is the name of the new output branch, checked out from the base branch/tag, 
that the patches will be applied too. 
- `--patches` sets the path to the patches config yaml. 

### Merge Conflicts 

The patches defined in the config yaml will me merged on top of the output branch in the 
order that they are written in the config file. If one of these merges results in a merge
conflict then the merge process will be cancelled. If you add the `--cleanup` flag then,
on encountering a merge conflict the script will abort the merge, move to the main branch
and delete the output_branch. If the clean up flag is not set the target repo will be left 
in the un-merged state.

_TODO_: Should we recommend re-basing the conflicting branch on the other branch and 
removing the conflicting branch? Depending on how many MCs you have you could rapidly get
to state where you have merged most of the patch branches, which defeats the point of the 
tool?
