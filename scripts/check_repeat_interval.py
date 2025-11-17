"""检查并更新 repeat_interval 字段"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import engine
from sqlalchemy import text


async def check_and_fix():
    """检查并修复数据"""
    async with engine.begin() as conn:
        # 检查所有规则的 repeat_interval 值
        print("检查现有告警规则...")
        result = await conn.execute(text("""
            SELECT id, name, repeat_interval 
            FROM alert_rule 
            ORDER BY id
        """))
        
        rules = result.fetchall()
        print(f"\n找到 {len(rules)} 条告警规则：")
        print("-" * 80)
        
        need_update = []
        for rule in rules:
            rule_id, name, repeat_interval = rule
            status = "✓" if repeat_interval else "✗"
            print(f"{status} ID: {rule_id:3d} | {name:40s} | repeat_interval: {repeat_interval}")
            
            if not repeat_interval or repeat_interval == 0:
                need_update.append(rule_id)
        
        if need_update:
            print(f"\n发现 {len(need_update)} 条规则需要更新默认值...")
            await conn.execute(text("""
                UPDATE alert_rule 
                SET repeat_interval = 1800 
                WHERE repeat_interval IS NULL OR repeat_interval = 0
            """))
            print("✓ 已更新为默认值 1800 秒（30分钟）")
        else:
            print("\n✓ 所有规则的 repeat_interval 值都正常")


async def main():
    try:
        await check_and_fix()
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
