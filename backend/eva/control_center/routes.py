from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .collector import collect_control_center_status
from .formatter import render_control_center_html


def get_control_center_routes() -> APIRouter:
    router = APIRouter()

    @router.get("/control", response_class=HTMLResponse)
    def control_center_page() -> HTMLResponse:
        status = collect_control_center_status()
        return HTMLResponse(render_control_center_html(status))

    @router.get("/control/status.json")
    def control_center_status_json() -> dict[str, object]:
        return collect_control_center_status().as_dict()

    return router
