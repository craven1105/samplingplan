# samplingplan

**把采样参数的选择讲成一次有依据的决策。**

`samplingplan` —— 对照任务类型列出温度、长度等参数的取值区间与取舍依据。

- 零依赖，Python 3.10+ 标准库即可运行
- 单文件，`samplingplan.py` 拷走就能用
- 不联网、不写文件

<!-- ipos:install -->
## 安装

零依赖，Python 3.10+ 即可：

```bash
pip install craven1105-samplingplan
```

装完直接用命令名调用：

```bash
samplingplan --help
```

也可以不用安装，直接把 `samplingplan.py` 拷走用——它只依赖标准库。

## 为什么需要它

参数指南多给推荐值；samplingplan 按任务类型给区间与依据，并写明每个取值会牺牲什么。

它遵守下面几条自己定的规矩：

1. **没有唯一答案**。不同任务需要不同的取舍，所以给区间与依据，不给推荐值。
2. **每个取值都要说明牺牲了什么**。温度调低换来一致性，代价是多样性。
3. **默认值也在做选择**。不写参数就等于默认替你做了决定——这件事要说出来。

## 用法

```bash
python samplingplan.py --task extraction
python samplingplan.py --task creative --json
```

加 `--json` 可以拿到机器可读的结果，便于接到流水线里。

## 已知局限

- 给的是参数取值区间与理由，不替你跑。
- 不接具体模型的价格与限流，只按任务类型给通用建议。
- 任务类型是你自己标的，标错就推荐错。

## 跑测试

```bash
python test_samplingplan.py
```

测试用独立的断言与临时数据，不污染工作目录。

## 来源与参考

- Python 标准库文档：<https://docs.python.org/3/>
- GitHub 仓库：<https://github.com/craven1105/samplingplan>

---

## 关于作者

craven1105 做采样参数的任务化选择相关的问题。这个工具先替你回答一个具体问题，再谈别的。

- 个人主页：<https://craven1105.github.io>
- 仓库：<https://github.com/craven1105/samplingplan>

## 许可

MIT，见 [LICENSE](LICENSE)。
