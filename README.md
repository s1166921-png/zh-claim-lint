# zh-claim-lint · 中文文案数字校验

**AI 把 8% 改成了 18%？发稿前先对一遍原文。**

离线比较原文与中文稿件，标出原文中找不到的日期、金额、百分比（含常见范围）和公告编号。适用于编辑复核或接入生成流水线。运行只需 Python 3.10+，无需 API Key，不上传文件。

## 30 秒试用

在项目目录中运行（包含虚构示例）：

```sh
python -m zh_claim_lint examples/source.txt examples/draft.txt
```

```text
examples/draft.txt:1:22: [date] 原文未找到：2026-04-10
examples/draft.txt:2:19: [percent] 原文未找到：18%
```

工具认得等值的写法，所以原文的 `1.2万元` 与草稿的 `12,000元` 不会触发告警。

## 日常使用

```sh
python -m pip install .
zh-claim-lint 原文.txt 草稿.txt
zh-claim-lint 原文.txt 草稿.txt --format json
```

输入为 UTF-8（可带 BOM）；JSON 输出带版本字段及每条发现的位置。行号、列号从 1 起，`start`、`end` 是 Python 字符偏移（从 0 起，右端不含）。

退出码：`0` 未发现标记；`1` 有待复核的标记；`2` 参数或输入错误。

Python 接口：`from zh_claim_lint import check`，调用 `check(原文, 草稿)` 返回按稿件顺序排列的 `Finding` 列表。

## 它不做什么

这是发稿前的规则筛查，不是事实核查。它不访问外部资料，不判断上下文是否支持某项声明，也不能找出所有错误。尤其是原文中已有的数字被挪到错误对象上，或同号公告来自不同机构，都可能漏报。未覆盖的写法（如纯中文数字、无年份日期和部分自定义编号）不会被当作已核实。

## 测试

```sh
python -m unittest discover -s tests -v
```

## English

An offline editorial lint for Chinese drafts. It compares structured dates, monetary amounts, percentages, and notice identifiers against a supplied source file. It flags values for **human review**, not semantic factuality. Run the fictional demo above or pass two UTF-8 files with optional JSON output.
