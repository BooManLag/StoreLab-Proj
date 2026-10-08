"""Static frontend delivery."""

import mimetypes

from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse, Response
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
def index() -> Response:
    # WEB_DIR is frontend/'s build output (frontend/vite.config.ts base: '/static/'); the
    # Dockerfile always populates it before this module imports. Locally it may not exist at
    # all (web/ isn't checked in, and `npm run dev` serves the frontend itself via its own
    # proxy to this backend) — application.py's mkdir keeps the static mount from refusing to
    # start, and this explains itself instead of a raw 404 when nobody has run `npm run build`.
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        return PlainTextResponse(
            "Frontend not built. Run `npm run build` in frontend/ to serve it from here, "
            "or run `npm run dev` in frontend/ for local development (it proxies /api to this backend).",
            status_code=404,
        )
    return FileResponse(str(index_path), headers={"Cache-Control": "no-cache"})
