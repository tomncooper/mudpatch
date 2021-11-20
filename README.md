# MUDpatch: Managing Upstream and Downstream patches 

A tool for managing a collection of downstream patches applied to an upstream tag/branch.

## Installation

### Install a released version

A wheel file is available via the [releases](https://github.com/tomncooper/mudpatch/releases) page. 
Download the wheel file (`.whl`) and use `pip` to install locally:

```bash
pip install mudpatch-0.1.0-py3-none-any.whl
```

### Install from source

[`poetry`](https://python-poetry.org/) is used to build and develop the `mud` tool:

```bash
poetry install
```
Will set up a virtual environment with the required dependencies. 
The script can then be run by calling:

```bash
poetry run mud --help
```

## Building a release

A distributable wheel and tar archive can be built using:

```bash
poetry build
```

This will build the distributables and place them in the `dist` folder.

## Usage

`mud` works by merging a set of patch branches on top of a base branch or tag. 
This provides an automated way of carrying a set of patches on top of an upstream release, backports and custom features/fixes can be added and removed by editing the [patches configuration file](#patch-configuration).

The general workflow for adding a new backport/patch/feature is:

1) Checkout the upstream tag/branch that you are currently releasing on top of (eg `1.0.0`) and create a new branch (eg `ISSUE-REF-1.0.0`).
2) Backport/develop your features/fixes onto this new branch.
3) Create an entry in your [patches configuration file](#patch-configuration) for this new patch branch.
4) When you are ready to release (after adding/removing other patches as needed), [invoke](#performing-a-mudpatch) the `mud` tool to create a new release branch (eg `1.0.0+patch1`). 

### Patch Configuration

The list of patches used by `mud` is defined in a yaml file with the following format:

```yaml
- title: patch-1
  description: The first patch
  upstreamPR: https://bithub.com/baz/foobar/1
  downstreamBranch: patch-1-1.0.0
  fixedVersion: 1.1.0
- title: patch-2
  description: The second patch
  upstreamPR: https://bithub.com/baz/foobar/2
  downstreamBranch: patch-2-1.0.0
  fixedVersion: 1.1.0
```

- `title`: A short title for this patch. It should be unique, for example it could be a reference in an issue tracking system.
- `description`: A short description of what the patch adds and/or fixes. Links to additional information/issues could be included here for context and auditing.
- `upstreamPR` : A link to the upstream PR this patch is derived from.
- `downstreamBranch`: The branch that contains the patch code. This should be available in the repository.
- `fixedVersion`: The upstream version that contains this patch. This signals when this patch can be dropped.

Most of these fields are for the benefit of human readers. 
The only one currently used by `mud` is the `downstreamBranch` field. 
This should be the name of the branch, within the target repository, that contains the patched code.

### Performing a mudpatch

Mud requires several arguments in order to create a new merged branch:
- `--repo` is the path to the repository you wish to run operations on. 
- `--base` defines the base branch or tag that the patches will be merged on top of. 
- `--output` is the name of the new output branch, checked out from the base branch/tag, that the patches will be applied too. 
- `--patches` is the path to the patches config yaml. 

For example, if you wish to merge the patches defined above (stored in a file called `patches.yaml`) on top of the `1.0.0` release tag of the foobar repo and have the final branch be called `1.0.0+patch1`, then you would issue the following command:

```bash
mud --repo foobar --base 1.0.0 --output 1.0.0+patch1 --patches patches.yaml
```

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
