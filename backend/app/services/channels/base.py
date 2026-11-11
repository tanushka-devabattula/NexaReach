"""Base abstraction for communication channels.

All concrete channel implementations (e.g. Email, SMS) must inherit from
:class:`Channel` and implement the :meth:`send` method. The method receives a
`message` string and a `recipient` dictionary containing the contact details.
It must return a dictionary with the following keys:

* ``success`` (bool) – whether the send operation was considered successful.
* ``provider_message_id`` (str | None) – an identifier supplied by the provider
  (for mock channels a deterministic ``mock-...`` value is used).
* ``status`` (str) – a textual status such as ``"sent"`` or ``"failed"``.
* ``error`` (str | None) – an error description when ``success`` is ``False``.
"""

from __future__ import annotations

import abc
from typing import Dict, Any


class Channel(abc.ABC):
    """Abstract communication channel.

    Sub‑classes must implement :meth:`send`.
    """

    @abc.abstractmethod
    def send(self, message: str, recipient: Dict[str, Any]) -> Dict[str, Any]:
        """Send ``message`` to ``recipient``.

        Parameters
        ----------
        message:
            The message body to be delivered.
        recipient:
            A mapping that at minimum contains the contact information required
            by the concrete channel (e.g. ``{"email": "user@example.com"}``).

        Returns
        -------
        dict
            ``{"success": bool, "provider_message_id": str | None,
            "status": str, "error": str | None}``
        """
        raise NotImplementedError
