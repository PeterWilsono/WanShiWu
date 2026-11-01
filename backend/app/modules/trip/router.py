"""旅行规划 HTTP 接口。"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.assistant.dependencies import LLMClientDependency
from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import CurrentUser
from app.modules.trip.ai_service import generate_trip_draft
from app.modules.trip.schemas import (
    ReorderRequest,
    TripCreate,
    TripGenerateRequest,
    TripItemCreate,
    TripItemResponse,
    TripItemUpdate,
    TripUpdate,
)
from app.modules.trip.service import (
    add_trip_item,
    create_trip,
    delete_trip,
    delete_trip_item,
    export_trip_markdown,
    get_trip,
    list_trips,
    reorder_trip_items,
    trip_response,
    update_trip,
    update_trip_item,
)

router = APIRouter(prefix="/trips", tags=["旅行规划"])
Db = Annotated[Session, Depends(get_db)]


@router.post("/generate")
def generate_trip_endpoint(
    current_user: CurrentUser, data: TripGenerateRequest, llm: LLMClientDependency
) -> dict:
    result = generate_trip_draft(llm, data)
    return ok(result.model_dump(mode="json"), "行程草稿已生成，请确认后保存")


@router.get("")
def list_trips_endpoint(
    db: Db,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    result = list_trips(db, current_user.id, page=page, page_size=page_size)
    return ok(result.model_dump(mode="json"))


@router.post("")
def create_trip_endpoint(db: Db, current_user: CurrentUser, data: TripCreate) -> dict:
    trip = create_trip(db, current_user.id, data)
    result = trip_response(db, current_user.id, trip)
    return ok(result.model_dump(mode="json"), "行程已保存")


@router.put("/{trip_id}/items/reorder")
def reorder_items_endpoint(
    db: Db, current_user: CurrentUser, trip_id: int, data: ReorderRequest
) -> dict:
    reorder_trip_items(db, current_user.id, trip_id, data)
    result = trip_response(db, current_user.id, get_trip(db, current_user.id, trip_id))
    return ok(result.model_dump(mode="json"), "顺序已更新")


@router.post("/{trip_id}/items")
def add_item_endpoint(
    db: Db, current_user: CurrentUser, trip_id: int, data: TripItemCreate
) -> dict:
    item = add_trip_item(db, current_user.id, trip_id, data)
    result = TripItemResponse.model_validate(item)
    return ok(result.model_dump(mode="json"), "行程条目已添加")


@router.patch("/{trip_id}/items/{item_id}")
def update_item_endpoint(
    db: Db, current_user: CurrentUser, trip_id: int, item_id: int, data: TripItemUpdate
) -> dict:
    item = update_trip_item(db, current_user.id, trip_id, item_id, data)
    result = TripItemResponse.model_validate(item)
    return ok(result.model_dump(mode="json"), "行程条目已更新")


@router.delete("/{trip_id}/items/{item_id}")
def delete_item_endpoint(db: Db, current_user: CurrentUser, trip_id: int, item_id: int) -> dict:
    delete_trip_item(db, current_user.id, trip_id, item_id)
    return ok(None, "行程条目已删除")


@router.get("/{trip_id}/export")
def export_trip_endpoint(
    db: Db,
    current_user: CurrentUser,
    trip_id: int,
    format: Literal["md"] = "md",
) -> Response:
    content = export_trip_markdown(db, current_user.id, trip_id)
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="trip-{trip_id}.md"'},
    )


@router.get("/{trip_id}")
def get_trip_endpoint(db: Db, current_user: CurrentUser, trip_id: int) -> dict:
    trip = get_trip(db, current_user.id, trip_id)
    result = trip_response(db, current_user.id, trip)
    return ok(result.model_dump(mode="json"))


@router.patch("/{trip_id}")
def update_trip_endpoint(
    db: Db, current_user: CurrentUser, trip_id: int, data: TripUpdate
) -> dict:
    trip = update_trip(db, current_user.id, trip_id, data)
    result = trip_response(db, current_user.id, trip)
    return ok(result.model_dump(mode="json"), "行程已更新")


@router.delete("/{trip_id}")
def delete_trip_endpoint(db: Db, current_user: CurrentUser, trip_id: int) -> dict:
    delete_trip(db, current_user.id, trip_id)
    return ok(None, "行程已删除")
