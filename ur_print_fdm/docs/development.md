# 开发与安装（可安装包）

## 本地开发安装
在仓库根目录执行：

```bash
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

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

