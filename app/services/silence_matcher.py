"""静默规则匹配工具"""
import re
from typing import Dict, List, Any
from loguru import logger


def check_silence_match(alert_labels: Dict[str, str], matchers: List[Dict[str, str]]) -> bool:
    """
    检查告警标签是否匹配静默规则
    
    Args:
        alert_labels: 告警标签字典，如 {"alertname": "HighCPU", "severity": "critical"}
        matchers: 匹配器列表，如 [
            {"label": "alertname", "operator": "=", "value": "HighCPU"},
            {"label": "severity", "operator": "=~", "value": "warning|critical"}
        ]
    
    Returns:
        bool: 所有 matcher 都匹配返回 True（AND 逻辑），否则返回 False
    """
    if not matchers:
        return False
    
    for matcher in matchers:
        label_name = matcher.get('label', '')
        operator = matcher.get('operator', '=')
        expected_value = matcher.get('value', '')
        
        # 获取告警中的标签值（不存在则为空字符串）
        actual_value = alert_labels.get(label_name, '')
        
        # 执行匹配
        try:
            if operator == '=':
                # 精确匹配
                if actual_value != expected_value:
                    return False
                    
            elif operator == '!=':
                # 不等于
                if actual_value == expected_value:
                    return False
                    
            elif operator == '=~':
                # 正则表达式匹配
                if not re.match(expected_value, actual_value):
                    return False
                    
            elif operator == '!~':
                # 正则表达式不匹配
                if re.match(expected_value, actual_value):
                    return False
            else:
                # 未知操作符，记录警告并认为不匹配
                logger.warning(f"未知的匹配操作符: {operator}")
                return False
                
        except re.error as e:
            # 正则表达式错误，记录并认为不匹配
            logger.error(f"正则表达式错误 '{expected_value}': {e}")
            return False
    
    # 所有 matcher 都匹配
    return True


def validate_matchers(matchers: List[Dict[str, str]]) -> tuple[bool, str]:
    """
    验证 matchers 配置是否有效
    
    Args:
        matchers: 匹配器列表
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not matchers:
        return False, "matchers 不能为空"
    
    if not isinstance(matchers, list):
        return False, "matchers 必须是列表"
    
    allowed_operators = ['=', '!=', '=~', '!~']
    
    for i, matcher in enumerate(matchers):
        if not isinstance(matcher, dict):
            return False, f"matcher[{i}] 必须是字典"
        
        # 检查必需字段
        if 'label' not in matcher:
            return False, f"matcher[{i}] 缺少 'label' 字段"
        
        if 'operator' not in matcher:
            return False, f"matcher[{i}] 缺少 'operator' 字段"
        
        if 'value' not in matcher:
            return False, f"matcher[{i}] 缺少 'value' 字段"
        
        # 检查操作符
        operator = matcher['operator']
        if operator not in allowed_operators:
            return False, f"matcher[{i}] 操作符 '{operator}' 无效，允许的操作符: {', '.join(allowed_operators)}"
        
        # 检查正则表达式
        if operator in ['=~', '!~']:
            try:
                re.compile(matcher['value'])
            except re.error as e:
                return False, f"matcher[{i}] 正则表达式 '{matcher['value']}' 无效: {str(e)}"
    
    return True, ""


def format_matcher_description(matcher: Dict[str, str]) -> str:
    """
    格式化 matcher 为可读的描述
    
    Args:
        matcher: 单个 matcher 字典
    
    Returns:
        str: 格式化的描述，如 "alertname = HighCPU"
    """
    label = matcher.get('label', '')
    operator = matcher.get('operator', '=')
    value = matcher.get('value', '')
    
    operator_desc = {
        '=': '等于',
        '!=': '不等于',
        '=~': '匹配正则',
        '!~': '不匹配正则'
    }
    
    op_text = operator_desc.get(operator, operator)
    return f"{label} {op_text} '{value}'"


def format_matchers_description(matchers: List[Dict[str, str]]) -> str:
    """
    格式化 matchers 列表为可读的描述
    
    Args:
        matchers: matchers 列表
    
    Returns:
        str: 格式化的描述，多个条件用 AND 连接
    """
    if not matchers:
        return "无匹配条件"
    
    descriptions = [format_matcher_description(m) for m in matchers]
    return " AND ".join(descriptions)
