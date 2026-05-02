# -*- coding: utf-8 -*-
"""
DataSourceChain + TickFlow 降级集成测试

测试场景:
1. TickFlow 可用时优先使用 TickFlow
2. TickFlow 不可用时自动降级到 AKShare / DataFetcherManager
3. 权限错误永久跳过
4. 临时错误触发指数退避
5. TickFlow 代码转换正确性
"""

import pytest
import time
from unittest.mock import MagicMock, patch

import sys
import os

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.data_source_chain import DataSourceChain, DataSource, AllSourcesFailedError
from src.services.tickflow_symbol import to_tickflow_symbol, from_tickflow_symbol


# ==================== 代码转换测试 ====================


class TestTickFlowSymbolConversion:
    """测试内部代码 ↔ TickFlow 代码格式转换"""

    def test_sh_stock(self):
        assert to_tickflow_symbol("600519") == "600519.SH"
        assert to_tickflow_symbol("601398") == "601398.SH"
        assert to_tickflow_symbol("688001") == "688001.SH"

    def test_sz_stock(self):
        assert to_tickflow_symbol("000001") == "000001.SZ"
        assert to_tickflow_symbol("002594") == "002594.SZ"
        assert to_tickflow_symbol("300750") == "300750.SZ"

    def test_bj_stock(self):
        assert to_tickflow_symbol("430047") == "430047.BJ"
        assert to_tickflow_symbol("920748") == "920748.BJ"
        assert to_tickflow_symbol("831010") == "831010.BJ"

    def test_hk_stock(self):
        assert to_tickflow_symbol("HK00700") == "00700.HK"
        assert to_tickflow_symbol("HK09988") == "09988.HK"

    def test_us_stock(self):
        assert to_tickflow_symbol("AAPL") == "AAPL.US"
        assert to_tickflow_symbol("TSLA") == "TSLA.US"

    def test_already_tickflow_format(self):
        assert to_tickflow_symbol("600519.SH") == "600519.SH"
        assert to_tickflow_symbol("AAPL.US") == "AAPL.US"

    def test_from_sh(self):
        assert from_tickflow_symbol("600519.SH") == "600519"
        assert from_tickflow_symbol("000001.SZ") == "000001"
        assert from_tickflow_symbol("920748.BJ") == "920748"

    def test_from_hk(self):
        assert from_tickflow_symbol("00700.HK") == "HK00700"
        assert from_tickflow_symbol("9988.HK") == "HK09988"

    def test_from_us(self):
        assert from_tickflow_symbol("AAPL.US") == "AAPL"
        assert from_tickflow_symbol("TSLA.US") == "TSLA"

    def test_etf(self):
        assert to_tickflow_symbol("510050") == "510050.SH"
        assert to_tickflow_symbol("159919") == "159919.SZ"

    def test_empty(self):
        assert to_tickflow_symbol("") == ""
        assert from_tickflow_symbol("") == ""


# ==================== DataSourceChain 测试 ====================


class TestDataSourceChain:
    """测试数据源优先级链机制"""

    def test_first_source_success(self):
        """第一个数据源成功时直接返回"""
        chain = DataSourceChain()
        chain.register("test", [
            DataSource("src1", lambda **kw: ["data_from_src1"]),
            DataSource("src2", lambda **kw: ["data_from_src2"]),
        ])
        result = chain.fetch("test")
        assert result == ["data_from_src1"]

    def test_fallback_on_failure(self):
        """第一个失败时自动降级到第二个"""
        chain = DataSourceChain()

        def fail(**kw):
            raise Exception("src1 网络超时")

        chain.register("test", [
            DataSource("src1", fail),
            DataSource("src2", lambda **kw: ["data_from_src2"]),
        ])
        result = chain.fetch("test")
        assert result == ["data_from_src2"]

    def test_all_fail_raises(self):
        """所有数据源均失败时抛 AllSourcesFailedError"""
        chain = DataSourceChain()
        chain.register("test", [
            DataSource("src1", lambda **kw: (_ for _ in ()).throw(Exception("fail1"))),
            DataSource("src2", lambda **kw: (_ for _ in ()).throw(Exception("fail2"))),
        ])

        def fail1(**kw):
            raise Exception("fail1")

        def fail2(**kw):
            raise Exception("fail2")

        chain = DataSourceChain()
        chain.register("test", [
            DataSource("src1", fail1),
            DataSource("src2", fail2),
        ])

        with pytest.raises(AllSourcesFailedError) as exc_info:
            chain.fetch("test")
        assert "test" in str(exc_info.value)

    def test_permanent_skip_on_auth_error(self):
        """认证错误导致永久跳过"""
        chain = DataSourceChain()
        call_count = {"src1": 0}

        class AuthError(Exception):
            status_code = 401

        def auth_fail(**kw):
            call_count["src1"] += 1
            raise AuthError("Invalid API Key")

        chain.register("test", [
            DataSource("src1", auth_fail),
            DataSource("src2", lambda **kw: ["fallback"]),
        ])

        # 第一次调用: src1 失败, src2 成功
        result = chain.fetch("test")
        assert result == ["fallback"]
        assert call_count["src1"] == 1

        # 第二次调用: src1 被永久跳过, 直接走 src2
        result = chain.fetch("test")
        assert result == ["fallback"]
        assert call_count["src1"] == 1  # 没有再调用 src1

    def test_exponential_backoff(self):
        """临时失败触发指数退避冷却"""
        chain = DataSourceChain()
        call_count = {"src1": 0}

        def temp_fail(**kw):
            call_count["src1"] += 1
            raise Exception("临时网络错误")

        chain.register("test", [
            DataSource("src1", temp_fail),
            DataSource("src2", lambda **kw: ["fallback"]),
        ])

        # 第一次: src1 失败一次, fail_count=1, 冷却 2 秒
        chain.fetch("test")
        assert call_count["src1"] == 1

        # 立即第二次: src1 处于冷却中，被跳过
        chain.fetch("test")
        assert call_count["src1"] == 1  # 仍然是 1

    def test_kwargs_passed_through(self):
        """关键字参数正确传递给 fetch 函数"""
        chain = DataSourceChain()
        received = {}

        def capture(**kw):
            received.update(kw)
            return ["ok"]

        chain.register("test", [DataSource("src1", capture)])
        chain.fetch("test", symbol="600519", period="1d")
        assert received == {"symbol": "600519", "period": "1d"}

    def test_disabled_source_skipped(self):
        """disabled 的源被跳过"""
        chain = DataSourceChain()
        chain.register("test", [
            DataSource("src1", lambda **kw: ["src1"], enabled=False),
            DataSource("src2", lambda **kw: ["src2"]),
        ])
        result = chain.fetch("test")
        assert result == ["src2"]

    def test_reset_clears_health(self):
        """reset 后健康状态被清除"""
        chain = DataSourceChain()

        class AuthError(Exception):
            status_code = 403

        def perm_fail(**kw):
            raise AuthError("forbidden")

        chain.register("test", [
            DataSource("src1", perm_fail),
            DataSource("src2", lambda **kw: ["ok"]),
        ])

        chain.fetch("test")  # src1 被永久跳过

        # 重置后 src1 重新可用
        chain.reset("test")
        # 需要重新注册（实际使用中只需 reset）
        # 验证健康报告
        report = chain.get_health_report()
        assert report["test:src1"]["permanent_skip"] is False

    def test_health_report(self):
        """健康报告包含正确信息"""
        chain = DataSourceChain()
        chain.register("test", [
            DataSource("src1", lambda **kw: ["ok"]),
        ])
        chain.fetch("test")
        report = chain.get_health_report()
        assert "test:src1" in report
        assert report["test:src1"]["healthy"] is True
        assert report["test:src1"]["fail_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
