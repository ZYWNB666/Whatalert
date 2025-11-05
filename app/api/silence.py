"""静默规则 API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.database import get_db
from app.models.silence import SilenceRule
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter()


@router.post("/", status_code=201)
async def create_silence_rule(
    rule_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建静默规则"""
    new_rule = SilenceRule(
        **rule_data,
        tenant_id=current_user.tenant_id,
        created_by=current_user.username
    )
    
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    return new_rule.to_dict()


@router.get("/")
async def list_silence_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取静默规则列表"""
    stmt = select(SilenceRule).where(SilenceRule.tenant_id == current_user.tenant_id)
    result = await db.execute(stmt)
    rules = result.scalars().all()
    
    return [rule.to_dict() for rule in rules]


@router.delete("/{rule_id}")
async def delete_silence_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除静默规则"""
    stmt = select(SilenceRule).where(
        and_(
            SilenceRule.id == rule_id,
            SilenceRule.tenant_id == current_user.tenant_id
        )
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Silence rule not found")
    
    await db.delete(rule)
    await db.commit()
    
    return {"message": "Silence rule deleted"}

