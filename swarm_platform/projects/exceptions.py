class ProjectError(Exception):
    """Base class for project-related errors."""


class ProjectLoadError(ProjectError):
    """Raised when a project cannot be loaded (e.g. install, update, or activation failure)."""


class ExperimentNotFound(ProjectError):
    """Raised when a requested experiment does not exist within a project."""