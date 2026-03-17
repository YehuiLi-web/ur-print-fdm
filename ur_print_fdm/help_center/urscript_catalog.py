from __future__ import annotations

URSCRIPT_DOCS: list[dict[str, str]] = [
    {
        "slug": "grammar",
        "filename": "grammar.md",
        "title": "语法基础",
        "summary": "集中讲块结构、字面量、表达式、控制流、函数和命名参数，是入门第一站。",
        "audience": "基础",
    },
    {
        "slug": "scope-and-threads",
        "filename": "scope-and-threads.md",
        "title": "作用域与线程",
        "summary": "重点解释第一层变量、global/local、thread、sec 和 Program Label。",
        "audience": "基础",
    },
    {
        "slug": "motion",
        "filename": "motion.md",
        "title": "运动指令",
        "summary": "覆盖 movej、movel、movep、movec、servo、speed 和 stop 指令。",
        "audience": "运动",
    },
    {
        "slug": "pose-math",
        "filename": "pose-math.md",
        "title": "位姿与数学",
        "summary": "讲清 pose 轴角、位姿变换、运动学函数和常用数学函数。",
        "audience": "运动",
    },
    {
        "slug": "io-and-runtime",
        "filename": "io-and-runtime.md",
        "title": "系统、I/O 与 RPC",
        "summary": "把 set_tcp、状态读取、I/O、RPC 和容器方法放到同一页查阅。",
        "audience": "运行时",
    },
    {
        "slug": "examples",
        "filename": "examples.md",
        "title": "示例脚本",
        "summary": "提供最小主程序、看门狗线程、feature 变换和速度控制示例。",
        "audience": "示例",
    },
    {
        "slug": "pitfalls",
        "filename": "pitfalls.md",
        "title": "常见坑",
        "summary": "专门提醒最容易误判的点，比如把 pose 当欧拉角、漏写 end、线程死循环不让步。",
        "audience": "避坑",
    },
]

URSCRIPT_FOUNDATION_TRACK: list[str] = [
    "grammar",
    "scope-and-threads",
    "pitfalls",
]

URSCRIPT_MOTION_TRACK: list[str] = [
    "motion",
    "pose-math",
]

URSCRIPT_RUNTIME_TRACK: list[str] = [
    "io-and-runtime",
    "examples",
]
