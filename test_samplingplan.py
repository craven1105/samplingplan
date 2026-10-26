"""samplingplan —— 自检测试。

对照任务类型列出温度、长度等参数的取值区间与取舍依据。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import samplingplan  # noqa: E402


class TestSamplingPlan(unittest.TestCase):
    def test_known_task_returns_plan(self):
        p = samplingplan.plan("extraction")
        self.assertTrue(p["known"])
        self.assertIn("temperature", p["params"])

    def test_unknown_task_is_flagged(self):
        p = samplingplan.plan("nonexistent-task")
        self.assertFalse(p["known"])

    def test_every_param_states_the_sacrifice(self):
        for key in samplingplan.TASKS:
            p = samplingplan.plan(key)
            for name, info in p["params"].items():
                self.assertTrue(info["sacrifice"], f"{key}.{name} 缺牺牲说明")
                self.assertTrue(info["why"], f"{key}.{name} 缺依据")

    def test_creative_allows_high_temperature(self):
        p = samplingplan.plan("creative")
        lo, hi = p["params"]["temperature"]["range"]
        self.assertGreater(lo, 0.5)

    def test_extraction_keeps_temperature_low(self):
        p = samplingplan.plan("extraction")
        lo, hi = p["params"]["temperature"]["range"]
        self.assertLessEqual(hi, 0.3)

    def test_all_tasks_have_notes(self):
        for key in samplingplan.TASKS:
            self.assertTrue(samplingplan.plan(key)["notes"])
