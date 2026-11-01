"""行程 CRUD、每日预算、单事务重排序与 Markdown 导出。"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.time import now_utc
from app.modules.trip.models import Trip, TripItem
from app.modules.trip.schemas import (
    DaySummary,
    ReorderRequest,
    TripCreate,
    TripItemCreate,
    TripItemResponse,
    TripItemUpdate,
    TripListResponse,
    TripResponse,
    TripUpdate,
)


def get_trip(db: Session, user_id: int, trip_id: int) -> Trip:
    trip = db.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.user_id == user_id,
            Trip.deleted_at.is_(None),
        )
    )
    if trip is None:
        raise AppError(ErrorCode.NOT_FOUND, "行程不存在", 404)
    return trip


def _trip_items(db: Session, user_id: int, trip_id: int) -> list[TripItem]:
    return list(
        db.scalars(
            select(TripItem)
            .where(
                TripItem.trip_id == trip_id,
                TripItem.user_id == user_id,
                TripItem.deleted_at.is_(None),
            )
            .order_by(TripItem.day_index, TripItem.sort_order, TripItem.id)
        ).all()
    )


def trip_response(db: Session, user_id: int, trip: Trip) -> TripResponse:
    items = _trip_items(db, user_id, trip.id)
    item_responses = [TripItemResponse.model_validate(item) for item in items]
    daily: list[DaySummary] = []
    for day_index in range(1, trip.days + 1):
        day_items = [item for item in item_responses if item.day_index == day_index]
        daily.append(
            DaySummary(
                day_index=day_index,
                date=trip.start_date + timedelta(days=day_index - 1)
                if trip.start_date
                else None,
                items=day_items,
                subtotal_cents=sum(item.cost_cents for item in day_items),
            )
        )
    planned = sum(item.cost_cents for item in items)
    remaining = trip.budget_cents - planned if trip.budget_cents is not None else None
    return TripResponse(
        id=trip.id,
        title=trip.title,
        destination=trip.destination,
        start_date=trip.start_date,
        days=trip.days,
        budget_cents=trip.budget_cents,
        preferences=trip.preferences,
        generated_by=trip.generated_by,
        status=trip.status,
        items=item_responses,
        daily_summaries=daily,
        planned_cents=planned,
        budget_remaining_cents=remaining,
        over_budget=remaining is not None and remaining < 0,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
    )


def create_trip(db: Session, user_id: int, data: TripCreate, *, commit: bool = True) -> Trip:
    values = data.model_dump(exclude={"items"})
    trip = Trip(user_id=user_id, **values)
    db.add(trip)
    db.flush()
    next_positions: dict[int, int] = {}
    for item_data in data.items:
        position = next_positions.get(item_data.day_index, 0)
        sort_order = item_data.sort_order if item_data.sort_order is not None else position
        values = item_data.model_dump(exclude={"sort_order"})
        db.add(
            TripItem(
                user_id=user_id,
                trip_id=trip.id,
                sort_order=sort_order,
                **values,
            )
        )
        next_positions[item_data.day_index] = max(position, sort_order) + 1
    if commit:
        db.commit()
        db.refresh(trip)
    else:
        db.flush()
    return trip


def list_trips(
    db: Session, user_id: int, *, page: int, page_size: int
) -> TripListResponse:
    filters = [Trip.user_id == user_id, Trip.deleted_at.is_(None)]
    total = db.scalar(select(func.count(Trip.id)).where(*filters)) or 0
    trips = db.scalars(
        select(Trip)
        .where(*filters)
        .order_by(Trip.created_at.desc(), Trip.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return TripListResponse(
        items=[trip_response(db, user_id, trip) for trip in trips],
        total=total,
        page=page,
        page_size=page_size,
    )


def update_trip(db: Session, user_id: int, trip_id: int, data: TripUpdate) -> Trip:
    trip = get_trip(db, user_id, trip_id)
    updates = data.model_dump(exclude_unset=True)
    if "days" in updates:
        max_day = db.scalar(
            select(func.max(TripItem.day_index)).where(
                TripItem.trip_id == trip.id,
                TripItem.user_id == user_id,
                TripItem.deleted_at.is_(None),
            )
        )
        if max_day is not None and updates["days"] < max_day:
            raise AppError(
                ErrorCode.BUSINESS_RULE_VIOLATION,
                "不能缩短到已有条目之后，请先移动或删除对应日期的条目",
                422,
            )
    for field, value in updates.items():
        setattr(trip, field, value)
    db.commit()
    db.refresh(trip)
    return trip


def delete_trip(db: Session, user_id: int, trip_id: int) -> None:
    trip = get_trip(db, user_id, trip_id)
    deleted_at = now_utc()
    trip.deleted_at = deleted_at
    for item in _trip_items(db, user_id, trip.id):
        item.deleted_at = deleted_at
    db.commit()


def get_trip_item(db: Session, user_id: int, trip_id: int, item_id: int) -> TripItem:
    get_trip(db, user_id, trip_id)
    item = db.scalar(
        select(TripItem).where(
            TripItem.id == item_id,
            TripItem.trip_id == trip_id,
            TripItem.user_id == user_id,
            TripItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise AppError(ErrorCode.NOT_FOUND, "行程条目不存在", 404)
    return item


def _validate_day(trip: Trip, day_index: int) -> None:
    if day_index > trip.days:
        raise AppError(ErrorCode.BUSINESS_RULE_VIOLATION, "条目日期不能超过行程总天数", 422)


def add_trip_item(
    db: Session, user_id: int, trip_id: int, data: TripItemCreate
) -> TripItem:
    trip = get_trip(db, user_id, trip_id)
    _validate_day(trip, data.day_index)
    sort_order = data.sort_order
    if sort_order is None:
        current_max = db.scalar(
            select(func.max(TripItem.sort_order)).where(
                TripItem.trip_id == trip_id,
                TripItem.user_id == user_id,
                TripItem.day_index == data.day_index,
                TripItem.deleted_at.is_(None),
            )
        )
        sort_order = 0 if current_max is None else current_max + 1
    values = data.model_dump(exclude={"sort_order"})
    item = TripItem(user_id=user_id, trip_id=trip_id, sort_order=sort_order, **values)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_trip_item(
    db: Session, user_id: int, trip_id: int, item_id: int, data: TripItemUpdate
) -> TripItem:
    item = get_trip_item(db, user_id, trip_id, item_id)
    trip = get_trip(db, user_id, trip_id)
    updates = data.model_dump(exclude_unset=True)
    if "day_index" in updates:
        _validate_day(trip, updates["day_index"])
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_trip_item(db: Session, user_id: int, trip_id: int, item_id: int) -> None:
    item = get_trip_item(db, user_id, trip_id, item_id)
    item.deleted_at = now_utc()
    db.commit()


def reorder_trip_items(
    db: Session, user_id: int, trip_id: int, data: ReorderRequest
) -> list[TripItem]:
    trip = get_trip(db, user_id, trip_id)
    current = _trip_items(db, user_id, trip_id)
    by_id = {item.id: item for item in current}
    requested_ids = {item.id for item in data.items}
    if requested_ids != set(by_id):
        raise AppError(
            ErrorCode.BUSINESS_RULE_VIOLATION,
            "重排序必须包含当前行程的全部有效条目",
            422,
        )
    for requested in data.items:
        _validate_day(trip, requested.day_index)
        item = by_id[requested.id]
        item.day_index = requested.day_index
        item.sort_order = requested.sort_order
    db.flush()
    db.commit()
    return _trip_items(db, user_id, trip_id)


def _yuan(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    absolute = abs(cents)
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"


def export_trip_markdown(db: Session, user_id: int, trip_id: int) -> str:
    trip = get_trip(db, user_id, trip_id)
    detail = trip_response(db, user_id, trip)
    lines = [
        f"# {detail.title}",
        "",
        f"- 目的地：{detail.destination}",
        f"- 开始日期：{detail.start_date or '待定'}",
        f"- 天数：{detail.days} 天",
        "- 总预算："
        + (_yuan(detail.budget_cents) + " 元" if detail.budget_cents is not None else "未设置"),
        f"- 已规划：{_yuan(detail.planned_cents)} 元",
    ]
    if detail.budget_remaining_cents is not None:
        lines.append(f"- 预算余额：{_yuan(detail.budget_remaining_cents)} 元")
    if detail.preferences:
        lines.extend([f"- 偏好：{detail.preferences}"])
    for day in detail.daily_summaries:
        lines.extend(["", f"## 第 {day.day_index} 天（{day.date or '日期待定'}）", ""])
        if not day.items:
            lines.append("暂无安排")
        for item in day.items:
            start = item.start_time.strftime("%H:%M") if item.start_time else "时间待定"
            lines.append(f"- {start} · {item.place} · 预计 {_yuan(item.cost_cents)} 元")
            if item.note:
                lines.append(f"  {item.note}")
        lines.append(f"\n当日小计：{_yuan(day.subtotal_cents)} 元")
    lines.extend(["", "---", "AI 生成内容中的景点、营业时间与价格请出行前核实。", ""])
    return "\n".join(lines)
