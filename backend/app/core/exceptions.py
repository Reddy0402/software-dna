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


class DependencyExtractionError(Exception):
    """Exception raised when dependency extraction encounters an error."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class GraphSyncError(Exception):
    """Exception raised when Neo4j graph synchronization encounters an error."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class GraphQueryError(Exception):
    """Exception raised when a graph query operation fails."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AnalyticsError(Exception):
    """Exception raised when an analytics computation fails."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
