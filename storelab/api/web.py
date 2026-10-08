"""Static frontend delivery."""

import mimetypes

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import WEB_DIR

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
router = APIRouter()


class RevalidatedStaticFiles(StaticFiles):
    """Always revalidate (cheap 304s via ETag) so a redeploy never leaves users on stale JS modules."""

    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


@router.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(
        str(WEB_DIR / "index.html"), headers={"Cache-Control": "no-cache"}
    )
