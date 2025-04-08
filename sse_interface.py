import abc
from typing import Dict, Any


class SSESenderInterface(abc.ABC):
    """
    Abstract Base Class defining the interface for sending Server-Sent Events (SSE).
    Extensions can use this interface to send notifications or data back to the client
    without depending on the specific SSE implementation.
    """

    @abc.abstractmethod
    async def send_event(
        self, device_id: str, event_name: str, data: Dict[str, Any]
    ) -> None:
        """
        Sends an event payload to a specific device's SSE connection.

        Args:
            device_id: The target device ID.
            event_name: The name of the SSE event (e.g., "extension_notification").
            data: A dictionary containing the event payload. This dictionary
                  will typically be serialized (e.g., to JSON) by the
                  concrete implementation before sending.
        """
        pass
