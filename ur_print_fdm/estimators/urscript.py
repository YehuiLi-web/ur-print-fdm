from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping, Sequence

from ur_print_fdm.shared.script_sanitizer import sanitize_script_content


@dataclass(frozen=True)
class URScriptEstimate:
    total_time_s: float
    cf_filament_mm: float
    extruder_filament_mm: float
    movej_time_s: float
    warnings: tuple[str, ...] = ()


class URScriptEstimateError(Exception):
    pass


def _vec3(pose: Sequence[float]) -> tuple[float, float, float]:
    return float(pose[0]), float(pose[1]), float(pose[2])


def _dist_m(a_pose: Sequence[float], b_pose: Sequence[float]) -> float:
    ax, ay, az = _vec3(a_pose)
    bx, by, bz = _vec3(b_pose)
    return math.sqrt((bx - ax) ** 2 + (by - ay) ** 2 + (bz - az) ** 2)


def _movec_arc_len_m(p0: Sequence[float], p1: Sequence[float], p2: Sequence[float]) -> float:
    x0, y0, z0 = _vec3(p0)
    x1, y1, z1 = _vec3(p1)
    x2, y2, z2 = _vec3(p2)

    ax, ay, az = (x1 - x0), (y1 - y0), (z1 - z0)
    bx, by, bz = (x2 - x0), (y2 - y0), (z2 - z0)

    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    cross_norm = math.sqrt(cx * cx + cy * cy + cz * cz)
    if cross_norm <= 1e-12:
        return _dist_m(p0, p1) + _dist_m(p1, p2)

    a_len = math.sqrt(ax * ax + ay * ay + az * az)
    b_len = math.sqrt(bx * bx + by * by + bz * bz)
    c_len = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
    if a_len <= 0 or b_len <= 0 or c_len <= 0:
        return 0.0

    # Circumradius: R = (abc) / (4A), and |a x b| = 2A
    radius = (a_len * b_len * c_len) / (2.0 * cross_norm)
    if radius <= 0:
        return _dist_m(p0, p1) + _dist_m(p1, p2)

    chord = _dist_m(p0, p2)
    ratio = max(-1.0, min(1.0, chord / (2.0 * radius)))
    theta = 2.0 * math.asin(ratio)  # minor arc
    return abs(radius * theta)


def _time_for_distance(distance_m: float, v_m_s: float, a_m_s2: float) -> float:
    d = max(0.0, float(distance_m))
    v = float(v_m_s)
    a = float(a_m_s2)
    if d <= 0 or v <= 0:
        return 0.0
    if a <= 0:
        return d / v

    d_reach = (v * v) / a
    if d <= d_reach:
        return 2.0 * math.sqrt(d / a)
    return (d / v) + (v / a)


@dataclass
class _Token:
    typ: str
    value: str


def _strip_inline_comment(line: str) -> str:
    in_str = False
    escaped = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            i += 1
            continue

        if ch == '"':
            in_str = True
            i += 1
            continue

        if ch == "#":
            return line[:i]
        if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
            return line[:i]
        i += 1
    return line


def _tokenize(expr: str) -> list[_Token]:
    s = expr
    tokens: list[_Token] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < len(s) and (s[j].isalnum() or s[j] == "_"):
                j += 1
            ident = s[i:j]
            tokens.append(_Token("IDENT", ident))
            i = j
            continue
        if ch.isdigit() or (ch == "." and i + 1 < len(s) and s[i + 1].isdigit()):
            j = i + 1
            while j < len(s) and (s[j].isdigit() or s[j] in ".eE+-"):
                # Stop signs that can't be part of a number
                if s[j] in "+-" and s[j - 1] not in "eE":
                    break
                j += 1
            tokens.append(_Token("NUMBER", s[i:j]))
            i = j
            continue
        if ch == '"':
            j = i + 1
            escaped = False
            while j < len(s):
                if escaped:
                    escaped = False
                    j += 1
                    continue
                if s[j] == "\\":
                    escaped = True
                    j += 1
                    continue
                if s[j] == '"':
                    break
                j += 1
            if j >= len(s) or s[j] != '"':
                raise URScriptEstimateError("Unterminated string literal")
            tokens.append(_Token("STRING", s[i + 1 : j]))
            i = j + 1
            continue

        # Two-char operators
        if i + 1 < len(s):
            two = s[i : i + 2]
            if two in ("<=", ">=", "==", "!="):
                tokens.append(_Token("OP", two))
                i += 2
                continue

        if ch in "+-*/%()[],:=":
            tokens.append(_Token("OP", ch))
            i += 1
            continue
        if ch in "<>":
            tokens.append(_Token("OP", ch))
            i += 1
            continue

        raise URScriptEstimateError(f"Unexpected character: {ch!r}")
    return tokens


class _Expr:
    pass


@dataclass(frozen=True)
class _Literal(_Expr):
    value: Any


@dataclass(frozen=True)
class _Name(_Expr):
    name: str


@dataclass(frozen=True)
class _Unary(_Expr):
    op: str
    rhs: _Expr


@dataclass(frozen=True)
class _Binary(_Expr):
    op: str
    lhs: _Expr
    rhs: _Expr


@dataclass(frozen=True)
class _Call(_Expr):
    name: str
    args: tuple[_Expr, ...]
    kwargs: Mapping[str, _Expr]


@dataclass(frozen=True)
class _Index(_Expr):
    base: _Expr
    index: _Expr


@dataclass(frozen=True)
class _ListLiteral(_Expr):
    items: tuple[_Expr, ...]


@dataclass(frozen=True)
class _PoseLiteral(_Expr):
    items: tuple[_Expr, ...]


class _ExprParser:
    def __init__(self, tokens: list[_Token]):
        self._toks = tokens
        self._i = 0

    def _peek(self) -> _Token | None:
        if self._i >= len(self._toks):
            return None
        return self._toks[self._i]

    def _accept(self, value: str | None = None, *, typ: str | None = None) -> _Token | None:
        tok = self._peek()
        if tok is None:
            return None
        if typ is not None and tok.typ != typ:
            return None
        if value is not None and tok.value != value:
            return None
        self._i += 1
        return tok

    def _expect(self, value: str | None = None, *, typ: str | None = None) -> _Token:
        tok = self._accept(value=value, typ=typ)
        if tok is None:
            wanted = value if value is not None else typ
            got = self._peek()
            raise URScriptEstimateError(f"Expected {wanted}, got {got.value if got else 'EOF'}")
        return tok

    def parse(self) -> _Expr:
        expr = self._parse_or()
        if self._peek() is not None:
            raise URScriptEstimateError(f"Unexpected token: {self._peek().value}")
        return expr

    def _parse_or(self) -> _Expr:
        lhs = self._parse_and()
        while True:
            tok = self._peek()
            if tok and tok.typ == "IDENT" and tok.value == "or":
                self._i += 1
                rhs = self._parse_and()
                lhs = _Binary("or", lhs, rhs)
            else:
                return lhs

    def _parse_and(self) -> _Expr:
        lhs = self._parse_cmp()
        while True:
            tok = self._peek()
            if tok and tok.typ == "IDENT" and tok.value == "and":
                self._i += 1
                rhs = self._parse_cmp()
                lhs = _Binary("and", lhs, rhs)
            else:
                return lhs

    def _parse_cmp(self) -> _Expr:
        lhs = self._parse_add()
        while True:
            tok = self._peek()
            if tok and tok.typ == "OP" and tok.value in ("<", ">", "<=", ">=", "==", "!="):
                op = tok.value
                self._i += 1
                rhs = self._parse_add()
                lhs = _Binary(op, lhs, rhs)
            else:
                return lhs

    def _parse_add(self) -> _Expr:
        lhs = self._parse_mul()
        while True:
            tok = self._peek()
            if tok and tok.typ == "OP" and tok.value in ("+", "-"):
                op = tok.value
                self._i += 1
                rhs = self._parse_mul()
                lhs = _Binary(op, lhs, rhs)
            else:
                return lhs

    def _parse_mul(self) -> _Expr:
        lhs = self._parse_unary()
        while True:
            tok = self._peek()
            if tok and tok.typ == "OP" and tok.value in ("*", "/", "%"):
                op = tok.value
                self._i += 1
                rhs = self._parse_unary()
                lhs = _Binary(op, lhs, rhs)
            else:
                return lhs

    def _parse_unary(self) -> _Expr:
        tok = self._peek()
        if tok and tok.typ == "OP" and tok.value == "-":
            self._i += 1
            return _Unary("-", self._parse_unary())
        if tok and tok.typ == "IDENT" and tok.value == "not":
            self._i += 1
            return _Unary("not", self._parse_unary())
        return self._parse_postfix()

    def _parse_postfix(self) -> _Expr:
        expr = self._parse_primary()
        while True:
            if self._accept("(", typ="OP"):
                args: list[_Expr] = []
                kwargs: dict[str, _Expr] = {}
                if not self._accept(")", typ="OP"):
                    while True:
                        # kw arg: IDENT '=' expr
                        save_i = self._i
                        tok = self._accept(typ="IDENT")
                        if tok and self._accept("=", typ="OP"):
                            key = tok.value
                            kwargs[key] = self._parse_or()
                        else:
                            self._i = save_i
                            args.append(self._parse_or())

                        if self._accept(",", typ="OP"):
                            continue
                        self._expect(")", typ="OP")
                        break
                if not isinstance(expr, _Name):
                    raise URScriptEstimateError("Only simple function calls are supported")
                expr = _Call(expr.name, tuple(args), kwargs)
                continue

            if self._accept("[", typ="OP"):
                idx_expr = self._parse_or()
                self._expect("]", typ="OP")
                expr = _Index(expr, idx_expr)
                continue

            return expr

    def _parse_primary(self) -> _Expr:
        tok = self._peek()
        if tok is None:
            raise URScriptEstimateError("Unexpected EOF")

        if tok.typ == "NUMBER":
            self._i += 1
            return _Literal(float(tok.value))
        if tok.typ == "STRING":
            self._i += 1
            return _Literal(tok.value)
        if tok.typ == "IDENT":
            if tok.value in ("True", "False"):
                self._i += 1
                return _Literal(tok.value == "True")
            if tok.value == "p" and self._i + 1 < len(self._toks) and self._toks[self._i + 1].value == "[":
                self._i += 1  # consume 'p'
                self._expect("[", typ="OP")
                items = self._parse_items_until("]")
                self._expect("]", typ="OP")
                return _PoseLiteral(tuple(items))
            self._i += 1
            return _Name(tok.value)
        if tok.typ == "OP" and tok.value == "(":
            self._i += 1
            expr = self._parse_or()
            self._expect(")", typ="OP")
            return expr
        if tok.typ == "OP" and tok.value == "[":
            self._i += 1
            items = self._parse_items_until("]")
            self._expect("]", typ="OP")
            return _ListLiteral(tuple(items))

        raise URScriptEstimateError(f"Unexpected token: {tok.value!r}")

    def _parse_items_until(self, closing: str) -> list[_Expr]:
        items: list[_Expr] = []
        tok = self._peek()
        if tok and tok.typ == "OP" and tok.value == closing:
            return items
        while True:
            items.append(self._parse_or())
            tok = self._peek()
            if tok and tok.typ == "OP" and tok.value == ",":
                self._i += 1
                continue
            return items


def _parse_expr(expr: str) -> _Expr:
    return _ExprParser(_tokenize(expr)).parse()


class _Stmt:
    pass


@dataclass(frozen=True)
class _Assign(_Stmt):
    scope: str  # "global" | "local" | "auto"
    name: str
    expr: _Expr


@dataclass(frozen=True)
class _IndexAssign(_Stmt):
    scope: str  # "global" | "local" | "auto"
    name: str
    index: _Expr
    expr: _Expr


@dataclass(frozen=True)
class _ExprStmt(_Stmt):
    expr: _Expr


@dataclass(frozen=True)
class _While(_Stmt):
    cond: _Expr
    body: tuple[_Stmt, ...]


@dataclass(frozen=True)
class _If(_Stmt):
    branches: tuple[tuple[_Expr, tuple[_Stmt, ...]], ...]
    else_body: tuple[_Stmt, ...] | None


@dataclass(frozen=True)
class _Def(_Stmt):
    name: str
    body: tuple[_Stmt, ...]


def _parse_script(text: str) -> tuple[tuple[_Stmt, ...], dict[str, _Def]]:
    raw_lines = sanitize_script_content(text).splitlines()
    lines: list[str] = []
    for ln in raw_lines:
        stripped = _strip_inline_comment(ln).rstrip()
        if stripped.strip():
            lines.append(stripped)

    idx = 0
    functions: dict[str, _Def] = {}

    def parse_block(stop_prefixes: tuple[str, ...]) -> tuple[list[_Stmt], int]:
        nonlocal idx
        stmts: list[_Stmt] = []
        while idx < len(lines):
            s = lines[idx].lstrip()
            if any(s.startswith(p) for p in stop_prefixes):
                break
            if s.strip() == "end":
                break
            stmt = parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        return stmts, idx

    def parse_statement() -> _Stmt | None:
        nonlocal idx
        line = lines[idx].lstrip()

        if line.startswith("def "):
            header = line
            idx += 1
            name = header[len("def ") :].split("(", 1)[0].strip()
            body, _ = parse_block(stop_prefixes=("end",))
            if idx >= len(lines) or lines[idx].strip() != "end":
                raise URScriptEstimateError(f"Missing end for def {name}")
            idx += 1  # consume end
            fn = _Def(name=name, body=tuple(body))
            functions[name] = fn
            return fn

        if line.startswith("while "):
            header = line
            if not header.endswith(":"):
                raise URScriptEstimateError("while missing ':'")
            cond_src = header[len("while ") : -1].strip()
            idx += 1
            body, _ = parse_block(stop_prefixes=("end",))
            if idx >= len(lines) or lines[idx].strip() != "end":
                raise URScriptEstimateError("Missing end for while")
            idx += 1
            return _While(cond=_parse_expr(cond_src), body=tuple(body))

        if line.startswith("if "):
            branches: list[tuple[_Expr, tuple[_Stmt, ...]]] = []
            else_body: tuple[_Stmt, ...] | None = None

            def parse_cond_from(header_line: str, kw: str) -> _Expr:
                if not header_line.endswith(":"):
                    raise URScriptEstimateError(f"{kw} missing ':'")
                return _parse_expr(header_line[len(kw) : -1].strip())

            cond = parse_cond_from(line, "if ")
            idx += 1
            body, _ = parse_block(stop_prefixes=("elif ", "else:", "end"))
            branches.append((cond, tuple(body)))

            while idx < len(lines):
                peek = lines[idx].lstrip()
                if peek.startswith("elif "):
                    cond = parse_cond_from(peek, "elif ")
                    idx += 1
                    body, _ = parse_block(stop_prefixes=("elif ", "else:", "end"))
                    branches.append((cond, tuple(body)))
                    continue
                if peek.startswith("else"):
                    if peek.strip() != "else:":
                        raise URScriptEstimateError("else must be 'else:'")
                    idx += 1
                    body, _ = parse_block(stop_prefixes=("end",))
                    else_body = tuple(body)
                    break
                break

            if idx >= len(lines) or lines[idx].strip() != "end":
                raise URScriptEstimateError("Missing end for if")
            idx += 1
            return _If(branches=tuple(branches), else_body=else_body)

        if line.strip() == "end":
            return None

        # Assignment? handle "global/local"
        scope = "auto"
        rest = line
        if rest.startswith("global "):
            scope = "global"
            rest = rest[len("global ") :].lstrip()
        elif rest.startswith("local "):
            scope = "local"
            rest = rest[len("local ") :].lstrip()

        # Find plain '=' not part of '=='/'!='
        eq_idx = None
        in_str = False
        escaped = False
        paren_depth = 0
        bracket_depth = 0
        for i, ch in enumerate(rest):
            if in_str:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
                continue
            if ch == "(":
                paren_depth += 1
                continue
            if ch == ")":
                paren_depth = max(0, paren_depth - 1)
                continue
            if ch == "[":
                bracket_depth += 1
                continue
            if ch == "]":
                bracket_depth = max(0, bracket_depth - 1)
                continue
            if ch == "=":
                if paren_depth or bracket_depth:
                    continue
                prev = rest[i - 1 : i] if i > 0 else ""
                nxt = rest[i + 1 : i + 2] if i + 1 < len(rest) else ""
                if prev in ("!", "=", "<", ">") or nxt == "=":
                    continue
                eq_idx = i
                break
        if eq_idx is not None:
            lhs = rest[:eq_idx].strip()
            rhs = rest[eq_idx + 1 :].strip()
            name = lhs.split("[", 1)[0].strip()
            if not name or not (name[0].isalpha() or name[0] == "_"):
                raise URScriptEstimateError(f"Unsupported assignment target: {lhs!r}")
            if "[" in lhs and lhs.endswith("]"):
                base = lhs[: lhs.find("[")].strip()
                idx_expr = lhs[lhs.find("[") + 1 : -1].strip()
                if not base or not idx_expr:
                    raise URScriptEstimateError(f"Unsupported index assignment target: {lhs!r}")
                idx += 1
                return _IndexAssign(
                    scope=scope,
                    name=base,
                    index=_parse_expr(idx_expr),
                    expr=_parse_expr(rhs),
                )
            idx += 1
            return _Assign(scope=scope, name=name, expr=_parse_expr(rhs))

        idx += 1
        return _ExprStmt(expr=_parse_expr(rest))

    top_level: list[_Stmt] = []
    while idx < len(lines):
        stmt = parse_statement()
        if stmt is not None:
            top_level.append(stmt)
    return tuple(top_level), functions


@dataclass
class _Frame:
    locals: dict[str, Any]


@dataclass
class _Runtime:
    extruder_modbus_id: str
    current_tcp_pose: list[float] | None
    default_feature_name: str
    max_steps: int
    max_loop_iters: int

    globals: dict[str, Any]
    functions: dict[str, _Def]

    # State
    warnings: list[str]
    steps: int = 0
    current_pose: list[float] | None = None
    extruder_mm_s: float = 0.0
    total_time_s: float = 0.0
    movej_time_s: float = 0.0
    cf_filament_mm: float = 0.0
    extruder_filament_mm: float = 0.0

    callstack: list[_Frame] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.callstack is None:
            self.callstack = []

    def _bump(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise URScriptEstimateError("Script too complex (step limit exceeded)")

    def _get_var(self, name: str) -> Any:
        if self.callstack and name in self.callstack[-1].locals:
            return self.callstack[-1].locals[name]
        return self.globals.get(name)

    def _set_var(self, scope: str, name: str, value: Any) -> None:
        if scope == "global":
            self.globals[name] = value
            return
        if scope == "local":
            if not self.callstack:
                self.globals[name] = value
                return
            self.callstack[-1].locals[name] = value
            return

        # auto
        if self.callstack:
            self.callstack[-1].locals[name] = value
        else:
            self.globals[name] = value

    def _start_pose(self, *, fallback: Sequence[float] | None = None) -> list[float]:
        if self.current_pose is not None:
            return self.current_pose

        feature = self._get_var(self.default_feature_name)
        if isinstance(feature, (list, tuple)) and len(feature) >= 6:
            self.current_pose = [float(x) for x in feature[:6]]
            return self.current_pose

        if self.current_tcp_pose is not None:
            self.current_pose = [float(x) for x in self.current_tcp_pose[:6]]
            return self.current_pose

        if fallback is not None and len(fallback) >= 6:
            self.current_pose = [float(x) for x in fallback[:6]]
            self.warnings.append("feature1 not found; using first target pose as start pose")
            return self.current_pose

        self.current_pose = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.warnings.append("No start pose available; using [0,0,0,0,0,0]")
        return self.current_pose

    def _eval(self, expr: _Expr) -> Any:
        self._bump()

        if isinstance(expr, _Literal):
            return expr.value
        if isinstance(expr, _Name):
            val = self._get_var(expr.name)
            if val is not None:
                return val
            # allow implicit modbus id variable
            if expr.name == "_mb":
                return self.extruder_modbus_id
            raise URScriptEstimateError(f"Unknown identifier: {expr.name}")
        if isinstance(expr, _Unary):
            rhs = self._eval(expr.rhs)
            if expr.op == "-":
                return -float(rhs)
            if expr.op == "not":
                return not bool(rhs)
            raise URScriptEstimateError(f"Unknown unary op: {expr.op}")
        if isinstance(expr, _Binary):
            lhs = self._eval(expr.lhs)
            rhs = self._eval(expr.rhs)
            op = expr.op
            if op == "+":
                return float(lhs) + float(rhs)
            if op == "-":
                return float(lhs) - float(rhs)
            if op == "*":
                return float(lhs) * float(rhs)
            if op == "/":
                return float(lhs) / float(rhs)
            if op == "%":
                return float(lhs) % float(rhs)
            if op == "<":
                return float(lhs) < float(rhs)
            if op == ">":
                return float(lhs) > float(rhs)
            if op == "<=":
                return float(lhs) <= float(rhs)
            if op == ">=":
                return float(lhs) >= float(rhs)
            if op == "==":
                return lhs == rhs
            if op == "!=":
                return lhs != rhs
            if op == "and":
                return bool(lhs) and bool(rhs)
            if op == "or":
                return bool(lhs) or bool(rhs)
            raise URScriptEstimateError(f"Unknown binary op: {op}")
        if isinstance(expr, _ListLiteral):
            return [self._eval(it) for it in expr.items]
        if isinstance(expr, _PoseLiteral):
            items = [float(self._eval(it)) for it in expr.items]
            # normalize to 6D pose
            while len(items) < 6:
                items.append(0.0)
            return items[:6]
        if isinstance(expr, _Index):
            base = self._eval(expr.base)
            idx = int(float(self._eval(expr.index)))
            try:
                return base[idx]
            except Exception as e:
                raise URScriptEstimateError(f"Index failed: {e}") from e
        if isinstance(expr, _Call):
            return self._call(expr.name, expr.args, expr.kwargs)
        raise URScriptEstimateError(f"Unsupported expression: {type(expr).__name__}")

    def _call(self, name: str, args: Sequence[_Expr], kwargs: Mapping[str, _Expr]) -> Any:
        # User-defined function call
        if name in self.functions:
            frame = _Frame(locals={})
            self.callstack.append(frame)
            try:
                for st in self.functions[name].body:
                    self._exec(st)
            finally:
                self.callstack.pop()
            return None

        # Built-ins
        if name == "pose_trans":
            if len(args) < 2:
                raise URScriptEstimateError("pose_trans requires 2 args")
            a_pose = self._eval(args[0])
            b_pose = self._eval(args[1])
            if not (isinstance(a_pose, (list, tuple)) and isinstance(b_pose, (list, tuple))):
                raise URScriptEstimateError("pose_trans expects poses")
            out = [0.0] * 6
            for i in range(6):
                av = float(a_pose[i]) if i < len(a_pose) else 0.0
                bv = float(b_pose[i]) if i < len(b_pose) else 0.0
                out[i] = av + bv
            return out

        if name == "d2r":
            if not args:
                raise URScriptEstimateError("d2r requires arg")
            return float(self._eval(args[0])) * math.pi / 180.0

        if name == "get_actual_tcp_pose":
            return self._start_pose()

        if name in ("set_tcp", "set_standard_digital_out"):
            return None

        if name == "sleep":
            if not args:
                return None
            dt = max(0.0, float(self._eval(args[0])))
            self.total_time_s += dt
            if self.extruder_mm_s > 0:
                self.extruder_filament_mm += self.extruder_mm_s * dt
            return None

        if name == "modbus_set_output_register":
            if len(args) < 2:
                return None
            mb_name = self._eval(args[0])
            reg = self._eval(args[1])
            if str(mb_name) == self.extruder_modbus_id:
                reg_i = int(float(reg))
                if reg_i >= 4000:
                    self.extruder_mm_s = max(0.0, (reg_i - 4000) / 100.0)
                else:
                    self.extruder_mm_s = 0.0
            return None

        if name in ("movel", "movep", "movej"):
            if not args:
                return None
            target = self._eval(args[0])
            if not (isinstance(target, (list, tuple)) and len(target) >= 6):
                raise URScriptEstimateError(f"{name} target must be pose")
            target_pose = [float(x) for x in target[:6]]

            start_pose = self._start_pose(fallback=target_pose)
            v = float(self._eval(kwargs.get("v", _Literal(0.0))))
            a = float(self._eval(kwargs.get("a", _Literal(0.0))))

            d_m = _dist_m(start_pose, target_pose)
            dt = _time_for_distance(d_m, v, a)
            self.total_time_s += dt
            if name == "movej":
                self.movej_time_s += dt
            else:
                self.cf_filament_mm += d_m * 1000.0
            if self.extruder_mm_s > 0:
                self.extruder_filament_mm += self.extruder_mm_s * dt

            self.current_pose = target_pose
            return None

        if name == "movec":
            if len(args) < 2:
                return None
            via = self._eval(args[0])
            to = self._eval(args[1])
            if not (isinstance(via, (list, tuple)) and isinstance(to, (list, tuple))):
                raise URScriptEstimateError("movec expects via/to poses")
            via_pose = [float(x) for x in via[:6]]
            to_pose = [float(x) for x in to[:6]]

            start_pose = self._start_pose(fallback=via_pose)
            v = float(self._eval(kwargs.get("v", _Literal(0.0))))
            a = float(self._eval(kwargs.get("a", _Literal(0.0))))
            d_m = _movec_arc_len_m(start_pose, via_pose, to_pose)
            dt = _time_for_distance(d_m, v, a)
            self.total_time_s += dt
            self.cf_filament_mm += d_m * 1000.0
            if self.extruder_mm_s > 0:
                self.extruder_filament_mm += self.extruder_mm_s * dt
            self.current_pose = to_pose
            return None

        # Unknown: ignore
        self.warnings.append(f"Ignoring unknown call: {name}()")
        return None

    def _exec(self, stmt: _Stmt) -> None:
        self._bump()

        if isinstance(stmt, _Def):
            # Definitions already collected.
            return
        if isinstance(stmt, _Assign):
            val = self._eval(stmt.expr)
            if isinstance(val, (list, tuple)):
                # URScript assigns lists/poses by value, not by reference.
                val = list(val)
            self._set_var(stmt.scope, stmt.name, val)
            return
        if isinstance(stmt, _IndexAssign):
            base = self._get_var(stmt.name)
            if base is None:
                raise URScriptEstimateError(f"Unknown identifier: {stmt.name}")
            idx = int(float(self._eval(stmt.index)))
            if idx < 0:
                raise URScriptEstimateError("Negative index assignment is not supported")
            if isinstance(base, tuple):
                base = list(base)
            if not isinstance(base, list):
                raise URScriptEstimateError(f"Index assignment requires list, got {type(base).__name__}")
            if idx >= len(base):
                base.extend([0.0] * (idx + 1 - len(base)))
            base[idx] = self._eval(stmt.expr)
            self._set_var(stmt.scope, stmt.name, base)
            return
        if isinstance(stmt, _ExprStmt):
            self._eval(stmt.expr)
            return
        if isinstance(stmt, _While):
            iters = 0
            while bool(self._eval(stmt.cond)):
                iters += 1
                if iters > self.max_loop_iters:
                    raise URScriptEstimateError("Loop iteration limit exceeded")
                for s in stmt.body:
                    self._exec(s)
            return
        if isinstance(stmt, _If):
            for cond, body in stmt.branches:
                if bool(self._eval(cond)):
                    for s in body:
                        self._exec(s)
                    return
            if stmt.else_body is not None:
                for s in stmt.else_body:
                    self._exec(s)
            return
        raise URScriptEstimateError(f"Unsupported statement: {type(stmt).__name__}")


def estimate_urscript(
    script_text: str,
    *,
    current_tcp_pose: Sequence[float] | None = None,
    extruder_modbus_id: str = "MODBUS_1",
    default_feature_name: str = "feature1",
    max_steps: int = 2_000_000,
    max_loop_iters: int = 500_000,
) -> URScriptEstimate:
    top_level, functions = _parse_script(script_text)

    rt = _Runtime(
        extruder_modbus_id=str(extruder_modbus_id),
        current_tcp_pose=[float(x) for x in current_tcp_pose[:6]] if current_tcp_pose is not None else None,
        default_feature_name=default_feature_name,
        max_steps=int(max_steps),
        max_loop_iters=int(max_loop_iters),
        globals={"_mb": str(extruder_modbus_id)},
        functions=functions,
        warnings=[],
    )

    for st in top_level:
        # Skip def statements at top-level; interpreter uses functions table.
        if isinstance(st, _Def):
            continue
        rt._exec(st)

    return URScriptEstimate(
        total_time_s=float(rt.total_time_s),
        cf_filament_mm=float(rt.cf_filament_mm),
        extruder_filament_mm=float(rt.extruder_filament_mm),
        movej_time_s=float(rt.movej_time_s),
        warnings=tuple(rt.warnings),
    )
