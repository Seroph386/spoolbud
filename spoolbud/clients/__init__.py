"""External service clients."""

from .spoolman import SpoolmanClient, TagScanError, TagScanRequest

__all__ = ["SpoolmanClient", "TagScanError", "TagScanRequest"]
