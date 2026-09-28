"""The base class every view module's models share: a plain pydantic model, with nothing of the contract's own
config (no `frozen`, no `extra="ignore"`) — a view is kestrel's own output, not something read back in.

`home.py` re-exports `View` for the modules that already import it from there; new code should import it from here.
"""

from __future__ import annotations

from pydantic import BaseModel


class View(BaseModel):
    pass
