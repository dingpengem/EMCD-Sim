"""Cooperative cancellation shared by GUI workers and numerical kernels."""


class Cancelled(Exception):
    """The calculation stopped without publishing a completed result."""


def check_cancelled(cancelled=None):
    if cancelled is not None and cancelled():
        raise Cancelled()
