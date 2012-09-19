# vim: tabstop=4 shiftwidth=4 softtabstop=4


class Error(RuntimeError):
    pass


class ImageNotFound(Error):
    pass


class SnapshotFailure(Error):
    pass


class FixedIPAssignFailure(Error):
    pass


class FloatingIPAssignFailure(Error):
    pass


class NoIPsAvailable(Error):
    pass


class UserConfigNotPresent(Error):
    pass
