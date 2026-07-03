class ProjectError(Exception):
    """Base class for project errors."""


class ProjectLoadError(ProjectError):
    """Raised when a project cannot be loaded."""


class ExperimentNotFound(ProjectError):
    """Raised when an experiment does not exist."""