class RepositoryImportError(Exception):
    """Base exception for all repository import errors."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidRepositoryURLError(RepositoryImportError):
    """Exception raised when the repository URL is invalid or malformed."""
    pass


class GitCloneError(RepositoryImportError):
    """Exception raised when cloning a repository fails."""
    pass
