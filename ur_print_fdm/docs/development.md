# 开发与安装（可安装包）

## 本地开发安装
在仓库根目录执行：

```bash
python -m pip install -U pip
python -m pip install -r requirements-dev.txt
```

说明：

- 根目录 `pyproject.toml` 是依赖和版本范围的唯一来源。
- `requirements-dev.txt` 是给协作者使用的快捷安装清单。
- 如果只需要运行程序，可以改用 `python -m pip install -r requirements.txt`。

启动：

```bash
ur-print-fdm
```

或：

```bash
python -m ur_print_fdm
```

## 代码风格
安装并启用 pre-commit：

```bash
python -m pip install pre-commit
pre-commit install
pre-commit run -a
```
