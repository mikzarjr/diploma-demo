from core.deps import require_head_or_admin
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from infra.storage.db.database import get_db
from infra.storage.db.models import Call, CheckResult, Check, User

router = APIRouter()


@router.get("/manager-stats")
async def manager_stats(
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(require_head_or_admin),
):
    call_stats_q = (
        select(
            Call.manager_id,
            User.name.label("manager_name"),
            func.count(Call.id).label("total_calls"),
            func.count(case((Call.status == "analyzed", 1))).label("analyzed_calls"),
            func.count(case((Call.status == "error", 1))).label("error_calls"),
            func.avg(Call.duration_sec).label("avg_duration"),
        )
        .join(User, Call.manager_id == User.id, isouter=True)
        .where(Call.manager_id.isnot(None))
        .group_by(Call.manager_id, User.name)
    )
    call_result = await db.execute(call_stats_q)
    call_rows = call_result.all()

    check_stats_q = (
        select(
            Call.manager_id,
            func.count(CheckResult.id).label("total_checks"),
            func.count(case((CheckResult.value_boolean == True, 1))).label("passed_checks"),
            func.count(case((CheckResult.value_boolean == False, 1))).label("failed_checks"),
            func.avg(CheckResult.value_score).label("avg_score"),
        )
        .join(Call, CheckResult.call_id == Call.id)
        .where(Call.manager_id.isnot(None))
        .group_by(Call.manager_id)
    )
    check_result = await db.execute(check_stats_q)
    check_map = {row.manager_id: row for row in check_result.all()}

    managers = []
    for row in call_rows:
        cr = check_map.get(row.manager_id)
        managers.append({
            "manager_id": row.manager_id,
            "manager_name": row.manager_name or f"Менеджер #{row.manager_id}",
            "total_calls": row.total_calls,
            "analyzed_calls": row.analyzed_calls,
            "error_calls": row.error_calls,
            "avg_duration": round(row.avg_duration or 0, 1),
            "analyze_rate": round(row.analyzed_calls / row.total_calls * 100, 1) if row.total_calls else 0,

            "total_checks": cr.total_checks if cr else 0,
            "passed_checks": cr.passed_checks if cr else 0,
            "failed_checks": cr.failed_checks if cr else 0,
            "check_pass_rate": round(cr.passed_checks / (cr.passed_checks + cr.failed_checks) * 100, 1)
            if cr and (cr.passed_checks + cr.failed_checks) > 0 else None,
            "avg_score": round(cr.avg_score, 2) if cr and cr.avg_score is not None else None,
        })

    managers.sort(key=lambda m: m["total_calls"], reverse=True)
    return managers


@router.get("/check-stats")
async def check_stats(
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(require_head_or_admin),
):
    q = (
        select(
            Check.id,
            Check.name,
            Check.type,
            Check.output_type,
            Check.active,
            func.count(CheckResult.id).label("total_runs"),
            func.count(case((CheckResult.value_boolean == True, 1))).label("passed"),
            func.count(case((CheckResult.value_boolean == False, 1))).label("failed"),
            func.avg(CheckResult.value_score).label("avg_score"),
        )
        .join(CheckResult, CheckResult.check_id == Check.id, isouter=True)
        .group_by(Check.id, Check.name, Check.type, Check.output_type, Check.active)
        .order_by(func.count(CheckResult.id).desc())
    )
    result = await db.execute(q)
    rows = result.all()

    return [
        {
            "check_id": row.id,
            "name": row.name,
            "type": row.type,
            "output_type": row.output_type,
            "active": row.active,
            "total_runs": row.total_runs,
            "passed": row.passed,
            "failed": row.failed,
            "pass_rate": round(row.passed / (row.passed + row.failed) * 100, 1)
            if (row.passed + row.failed) > 0 else None,
            "avg_score": round(row.avg_score, 2) if row.avg_score is not None else None,
        }
        for row in rows
    ]
