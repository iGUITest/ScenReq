from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "manual_edit_sync.api:app",
        host="0.0.0.0",
        port=8011,
        reload=False,
    )
