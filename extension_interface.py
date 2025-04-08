import abc
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass

@dataclass
class CopyResponse:
    """
    Response object returned by the on_copy method.

    Attributes:
        notification_title: Optional title for a user notification.
        notification_detail: Optional detailed message for a user notification.
        is_processing_task: Boolean indicating if the extension has started a
                       longer-running background task related to this copy event.
                       Defaults to False.
    """
    notification_title: Optional[str] = None
    notification_detail: Optional[str] = None
    is_processing_task: bool = False

@dataclass
class PasteResponse:
    """
    Response object returned by the on_paste method.
    """
    notification_title: Optional[str] = None
    notification_detail: Optional[str] = None
    paste_content: Optional[str] = None
    is_processing_task: bool = False

    def is_accepted(self) -> bool:
        """
        Returns True if the paste request is accepted by the extension.
        """
        return self.paste_content is not None or self.is_processing_task


class ExtensionInterface(abc.ABC):
    """
    Abstract Base Class defining the interface for all TabTabTab extensions.

    Each extension module must contain a class that inherits from this
    interface and implements all its abstract methods.
    """

    @abc.abstractmethod
    def setup(self, config: Dict[str, Any]) -> None:
        """
        Initializes the extension with its specific configuration.

        This method is called once by the framework when the extension is loaded.
        It should be used to store API keys, set up connections, or perform
        any other necessary initialization based on the provided configuration.

        Args:
            config: A dictionary containing configuration parameters for this
                    extension (e.g., API keys, settings loaded from a central
                    configuration file).
        """
        pass

    @abc.abstractmethod
    def on_context_request(
        self, source_extension_id: str, context_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handles a request for context information from another extension.

        This allows extensions to query each other for relevant data. The
        implementation should determine what context it can provide based on
        the query and return it as a dictionary.

        Args:
            source_extension_id: The unique identifier of the extension making
                                 the request.
            context_query: A dictionary specifying the context being requested.
                           The structure of this query is up to the calling
                           and receiving extensions to agree upon.

        Returns:
            A dictionary containing the requested context information, or an
            empty dictionary if the requested context cannot be provided.
        """
        pass

    @abc.abstractmethod
    async def on_copy(self, context: Dict[str, Any]) -> CopyResponse:
        """
        Handles a 'copy' event triggered by the user.

        This method is called when the framework detects a copy action relevant
        to potentially triggering extensions (e.g., copying text in a specific
        application). The extension can use the provided context to perform
        background tasks, prepare data, or interact with external services.

        Args:
            context: A dictionary containing information about the copy event.
                     Common keys include:
                     - 'device_id': str
                     - 'session_id': str
                     - 'request_id': str
                     - 'timestamp': str (ISO format UTC)
                     - 'metadata': Dict[str, Any] (original metadata from client)
                     - 'window_info': Dict[str, Any] (parsed window info)
                     - 'screenshot_provided': bool
                     - 'selected_text': Optional[str]
                     - 'screenshot_data': Optional[bytes] (Raw image data if screenshot_provided is True)

        Returns:
            A CopyResponse object, potentially containing a message to notify
            the user and indicating if a background task was started.
        """
        pass

    @abc.abstractmethod
    async def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        """
        Handles a 'paste' event triggered by the user, potentially modifying
        or providing the content to be pasted.

        This method is called when the framework routes a paste action to this
        specific extension. The extension can analyze the context and decide
        whether to provide custom content to be pasted.

        Args:
            context: A dictionary containing information about the paste event,
                     such as the target application, active URL, current
                     clipboard content (if available), etc.

        Returns:
            A PasteResponse object containing the optional content to paste
            and/or an optional message to notify the user.
        """
        pass
