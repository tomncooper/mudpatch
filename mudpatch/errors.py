from git.exc import CommandError


class MudPatchError(RuntimeError):
    pass


class RepoManipulationError(MudPatchError):
    def __init__(self, msg: str, comm_err: CommandError) -> None:
        self.message = msg
        self.comm_err = comm_err
        super().__init__(self.message)


class CheckoutError(RepoManipulationError):
    pass


class CommitError(RepoManipulationError):
    pass


class UnknownReferenceError(MudPatchError):
    pass


class UnknownBranchError(UnknownReferenceError):
    pass


class BranchExistsError(MudPatchError):
    pass


class MultipleRemoteReferences(MudPatchError):
    pass
