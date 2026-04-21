from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "failure_requirement_repair.api:app",
        host="0.0.0.0",
        port=8012,
        reload=False,
    )
