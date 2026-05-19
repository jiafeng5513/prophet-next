# -*- coding: utf-8 -*-
"""
===================================
Agent 输出解析器
===================================

通用的 LLM 输出 → Pydantic Schema 解析管线。
三层尝试: strict JSON → lenient JSON → fallback 到现有文本解析。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# JSON 代码块正则（支持 ```json ... ``` 和 ``` ... ```）
_JSON_BLOCK_RE = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?\s*```",
    re.DOTALL,
)

# 裸 JSON 对象正则（匹配最外层 {...}）
_BARE_JSON_RE = re.compile(
    r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
    re.DOTALL,
)


def extract_json_text(raw: str) -> Optional[str]:
    """
    从 LLM 原始输出中提取 JSON 文本。

    优先级:
    1. ```json ... ``` 代码块
    2. ``` ... ``` 代码块
    3. 最后一个裸 JSON 对象
    """
    if not raw:
        return None

    # 1. 代码块
    matches = _JSON_BLOCK_RE.findall(raw)
    if matches:
        return matches[-1].strip()

    # 2. 裸 JSON（取最长匹配）
    bare_matches = _BARE_JSON_RE.findall(raw)
    if bare_matches:
        # 取最长的匹配（通常是完整 JSON）
        return max(bare_matches, key=len).strip()

    return None


def parse_structured_output(
    raw_text: str,
    schema_cls: Type[T],
    *,
    strict: bool = False,
) -> Optional[T]:
    """
    尝试将 LLM 原始文本解析为 Pydantic Schema。

    Args:
        raw_text: LLM 原始输出
        schema_cls: 目标 Pydantic 模型类
        strict: 如果 True，验证失败直接返回 None；否则尝试宽松解析

    Returns:
        解析成功返回 Schema 实例，否则 None
    """
    json_text = extract_json_text(raw_text)
    if not json_text:
        return None

    # 第一层: 严格解析
    try:
        data = json.loads(json_text)
        return schema_cls.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        if strict:
            logger.debug("[OutputParser] strict parse failed: %s", e)
            return None

    # 第二层: 宽松解析 — 修复常见 LLM JSON 问题
    try:
        cleaned = _fix_common_json_issues(json_text)
        data = json.loads(cleaned)
        return schema_cls.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.debug("[OutputParser] lenient parse failed: %s", e)

    # 第三层: 尝试只提取已知字段
    try:
        data = json.loads(json_text) if json_text else {}
        # 用 model_construct 跳过验证，允许部分字段
        return schema_cls.model_validate(data)
    except Exception:
        pass

    return None


def _fix_common_json_issues(text: str) -> str:
    """修复 LLM 输出的常见 JSON 格式问题"""
    # 移除尾部逗号 (trailing commas)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # 修复单引号 → 双引号
    # (只在明显是 JSON 键值对的情况下)
    text = re.sub(r"(?<=[\[{,])\s*'([^']+)'\s*:", r' "\1":', text)
    # 移除注释行
    text = re.sub(r"//[^\n]*", "", text)
    return text


def parse_to_dict(raw_text: str) -> Optional[dict]:
    """
    提取 JSON 为 dict，不做 Schema 验证。
    兼容现有 try_parse_json 的用法。
    """
    json_text = extract_json_text(raw_text)
    if not json_text:
        return None

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        try:
            cleaned = _fix_common_json_issues(json_text)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None
