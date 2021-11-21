class MudPatchError(RuntimeError):
    pass

class UnknownReferenceError(MudPatchError):
    pass

class UnknownBranchError(UnknownReferenceError):
    pass

class BranchExistsError(MudPatchError):
    pass

class MultipleRemoteReferences(MudPatchError):
    pass