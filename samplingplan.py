"""samplingplan —— 把采样参数的选择讲成一次有依据的决策。

设计原则：
1. **没有唯一答案**。不同任务需要不同的取舍，所以给区间与依据，不给推荐值。
2. **每个取值都要说明牺牲了什么**。温度调低换来一致性，代价是多样性。
3. **默认值也在做选择**。不写参数就等于默认替你做了决定——这件事要说出来。

仅依赖 Python 标准库。

用法:
    python samplingplan.py --help
    python samplingplan.py --task extraction
    python samplingplan.py --task creative --json
"""

from __future__ import annotations

import argparse
import json
import sys

# ---------------------------------------------------------------------------
# 任务画像
# ---------------------------------------------------------------------------

# 每类任务给出：参数区间 + 每个取值牺牲了什么 + 适用说明
TASKS: dict[str, dict] = {
    "extraction": {
        "label": "结构化抽取",
        "desc": "从文本里取出字段，答案有唯一形态。",
        "params": {
            "temperature": {
                "range": [0.0, 0.2],
                "why": "越低越稳定，因为同一段文本应该抽出同样的字段",
                "sacrifice": "拿多样性换可复现——但抽取本来就不需要多样性",
            },
            "max_tokens": {
                "range": [256, 1024],
                "why": "按输出字段数留够，别截断",
                "sacrifice": "留太多会诱导模型编出多余字段",
            },
            "top_p": {
                "range": [0.8, 1.0],
                "why": "低温度下这个参数基本不起作用，设 1.0 最省心",
                "sacrifice": "没有牺牲，这是本任务里可以不管的参数",
            },
            "seed": {
                "range": "建议固定",
                "why": "抽取要能回归测试，固定种子才能对比",
                "sacrifice": "固定种子会让人误以为输出完全确定——其实还受权重影响",
            },
        },
        "notes": [
            "抽取类任务最该盯的是「字段别多给」——用 schema 约束比调温度管用。",
        ],
    },
    "classification": {
        "label": "分类打标",
        "desc": "给一段内容选一个或多个标签。",
        "params": {
            "temperature": {
                "range": [0.0, 0.3],
                "why": "标签集合有限，低温度减少游走出界的标签",
                "sacrifice": "多样性没了，长尾内容可能被硬塞进最近的类",
            },
            "max_tokens": {
                "range": [16, 128],
                "why": "标签数量少，输出很短",
                "sacrifice": "留太多反而给模型机会输出多余解释",
            },
            "top_p": {
                "range": [0.9, 1.0],
                "why": "同上，低温度时基本不生效",
                "sacrifice": "没有牺牲",
            },
            "seed": {
                "range": "建议固定",
                "why": "打标结果要能复现做回归",
                "sacrifice": "同上",
            },
        },
        "notes": [
            "分类的难点通常不在采样参数，而在标签定义本身。",
        ],
    },
    "summarization": {
        "label": "摘要压缩",
        "desc": "把长文压成短摘要。",
        "params": {
            "temperature": {
                "range": [0.2, 0.5],
                "why": "太低会压成流水账，太高会跑题",
                "sacrifice": "取下限会牺牲表达力，取上限会牺牲忠实度",
            },
            "max_tokens": {
                "range": [200, 800],
                "why": "按目标长度倒推，压缩比先定下来",
                "sacrifice": "压得越狠越容易漏掉细节",
            },
            "top_p": {
                "range": [0.9, 1.0],
                "why": "基本不生效，设 1.0",
                "sacrifice": "没有牺牲",
            },
            "seed": {
                "range": "可不固定",
                "why": "摘要不追求逐字一致",
                "sacrifice": "不固定就没法做逐字回归，只能做语义对比",
            },
        },
        "notes": [
            "摘要任务更该控制的是「压缩比」而不是采样参数。",
        ],
    },
    "qa": {
        "label": "问答",
        "desc": "根据给定材料回答问题。",
        "params": {
            "temperature": {
                "range": [0.0, 0.4],
                "why": "要有据可依，别自己发挥",
                "sacrifice": "取上限牺牲忠实度换表达自然度",
            },
            "max_tokens": {
                "range": [300, 1200],
                "why": "按答案长度预期留",
                "sacrifice": "留太多可能诱发模型把材料整段复述",
            },
            "top_p": {
                "range": [0.9, 1.0],
                "why": "低温度下不生效",
                "sacrifice": "没有牺牲",
            },
            "seed": {
                "range": "建议固定",
                "why": "问答是评测里最常被测的一类，要能回归",
                "sacrifice": "同上",
            },
        },
        "notes": [
            "问答里的关键变量往往是「材料给多少」，不是温度。",
        ],
    },
    "creative": {
        "label": "创意写作",
        "desc": "写故事、文案、方案这类没有唯一答案的东西。",
        "params": {
            "temperature": {
                "range": [0.7, 1.0],
                "why": "多样性是目的本身，压低就压掉了",
                "sacrifice": "取上限牺牲稳定性，同一提示词多次结果差异大",
            },
            "max_tokens": {
                "range": [800, 2000],
                "why": "看要写多长",
                "sacrifice": "限制长度会逼出草草收尾的结尾",
            },
            "top_p": {
                "range": [0.9, 1.0],
                "why": "调 top_p 会改变候选分布的形状，比调温度更细",
                "sacrifice": "同时调温度和 top_p 会分不清是谁起的作用",
            },
            "seed": {
                "range": "可不固定",
                "why": "创意任务本来就想要多个不同的结果",
                "sacrifice": "不固定就没法复现某一次的好结果",
            },
        },
        "notes": [
            "一次只改一个参数。同时改两个，得到好结果也不知道该归功于谁。",
        ],
    },
    "code": {
        "label": "代码生成",
        "desc": "写出可运行的代码。",
        "params": {
            "temperature": {
                "range": [0.0, 0.3],
                "why": "代码要么对要么错，多样性帮不上忙",
                "sacrifice": "拿多样性换正确率——但也压掉偶尔更优的写法",
            },
            "max_tokens": {
                "range": [1000, 4000],
                "why": "代码长度波动大，留够避免截断",
                "sacrifice": "留太多会拉高成本与延迟",
            },
            "top_p": {
                "range": [0.9, 1.0],
                "why": "不生效",
                "sacrifice": "没有牺牲",
            },
            "seed": {
                "range": "建议固定",
                "why": "代码测试需要逐字回归",
                "sacrifice": "同上",
            },
        },
        "notes": [
            "代码生成更值得投入的是「怎么让编译错误回到模型」这条回路。",
        ],
    },
    "rewriting": {
        "label": "改写润色",
        "desc": "在保留原意的前提下换一种说法。",
        "params": {
            "temperature": {
                "range": [0.4, 0.8],
                "why": "太低会原意不变，太高会改掉意思",
                "sacrifice": "这个区间本身就是权衡，两头都有代价",
            },
            "max_tokens": {
                "range": ["与原文等长", "原文 1.5 倍"],
                "why": "改写后长度不该差太多",
                "sacrifice": "卡死长度会限制表达",
            },
            "top_p": {
                "range": [0.9, 1.0],
                "why": "不生效",
                "sacrifice": "没有牺牲",
            },
            "seed": {
                "range": "可不固定",
                "why": "改写任务通常接受多个版本",
                "sacrifice": "不固定则无法定位「上次那版改得更好」",
            },
        },
        "notes": [
            "改写类任务应该单独测「语义保持」，而不是只测相似度。",
        ],
    },
    "planning": {
        "label": "规划推理",
        "desc": "拆解任务、排出步骤。",
        "params": {
            "temperature": {
                "range": [0.2, 0.6],
                "why": "要有一定探索空间，但别发散",
                "sacrifice": "取下限牺牲步骤多样性，取上限牺牲步骤合理性",
            },
            "max_tokens": {
                "range": [500, 2000],
                "why": "步骤多就要留够",
                "sacrifice": "留够意味着成本上升",
            },
            "top_p": {
                "range": [0.9, 1.0],
                "why": "不生效",
                "sacrifice": "没有牺牲",
            },
            "seed": {
                "range": "建议固定",
                "why": "规划错误要能复现排查",
                "sacrifice": "固定后可能把探索锁死在第一条路径",
            },
        },
        "notes": [
            "规划的瓶颈通常在「工具能不能真的执行」，不在采样。",
        ],
    },
}

DEFAULT_SAMPLERS = {
    "temperature": "（各家默认值不同，常见在 0.7～1.0）",
    "top_p": "（常见在 0.9～1.0）",
    "max_tokens": "（看模型上限）",
    "seed": "（通常不固定）",
}


def plan(task: str) -> dict:
    """给出一份参数决策说明。"""
    t = TASKS.get(task)
    if not t:
        return {"task": task, "known": False}
    return {"task": task, "known": True, **t}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render(p: dict) -> str:
    if not p.get("known"):
        out: list[str] = []
        out.append(f"没有「{p['task']}」这个任务类型。")
        out.append("")
        out.append("已知类型：")
        for key, t in TASKS.items():
            out.append(f"  {key:<16} {t['label']}——{t['desc']}")
        return "\n".join(out)

    out: list[str] = []
    out.append(f"采样参数决策：{p['label']}")
    out.append("=" * 60)
    out.append(p["desc"])
    out.append("")

    for name, info in p["params"].items():
        rng = info["range"]
        rng_text = rng if isinstance(rng, str) else f"{rng[0]} ～ {rng[1]}"
        out.append(f"{name}")
        out.append(f"  取值区间  {rng_text}")
        out.append(f"  依据      {info['why']}")
        out.append(f"  牺牲了什么  {info['sacrifice']}")
        out.append("")

    out.append("说明：")
    for n in p["notes"]:
        out.append(f"  · {n}")
    out.append("")
    out.append("不写参数会怎样：")
    for k, v in DEFAULT_SAMPLERS.items():
        out.append(f"  · {k} {v}")
    out.append("")
    out.append("  也就是说，不调参数本身就是一次选择——默认在替任务做决定。")
    return "\n".join(out).rstrip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="samplingplan",
        description="把采样参数的选择讲成一次有依据的决策（仅依赖标准库）",
        epilog=(
            "可用任务类型：\n  " + "、".join(TASKS) + "\n"
            "  python samplingplan.py --task extraction\n"
            "  python samplingplan.py --list\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--task", help="任务类型")
    ap.add_argument("--list", action="store_true", help="列出所有任务类型")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    if args.list:
        if args.json:
            print(json.dumps({"tasks": {k: {"label": v["label"],
                                             "desc": v["desc"]}
                                         for k, v in TASKS.items()}},
                             ensure_ascii=False, indent=2))
        else:
            for key, t in TASKS.items():
                print(f"  {key:<16} {t['label']}——{t['desc']}")
        return 0

    if not args.task:
        print("需要 --task 或 --list。", file=sys.stderr)
        return 2

    p = plan(args.task)

    if args.json:
        print(json.dumps(p, ensure_ascii=False, indent=2))
        return 0

    print(render(p))
    return 0 if p.get("known") else 2


if __name__ == "__main__":
    raise SystemExit(main())
