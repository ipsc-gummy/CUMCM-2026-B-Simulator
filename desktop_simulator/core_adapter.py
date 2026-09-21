"""Boundary to the non-public simulator runtime.

The public repository intentionally does not contain scene generation,
physics, ErrorField, replay data, or hidden evaluation material.
Packaged desktop builds replace this module with the private runtime adapter.
"""


class PrivateCoreUnavailable(RuntimeError):
    """Raised when a source checkout tries to start a local simulation."""


def prepare(task, seed, scene_id):
    del task, seed, scene_id
    raise PrivateCoreUnavailable(
        "The local simulator core is not distributed in the public source repository. "
        "Use an official desktop build for Q3/Q4 local simulation."
    )
