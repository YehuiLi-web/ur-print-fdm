# URScript 语法基础

这页专门讲 URScript 的块结构、字面量、表达式、控制流和函数定义。

如果你要查 `global/local`、线程、`sec` 等特殊语义，请继续看 [作用域与线程](./scope-and-threads.md)。

## 1. 脚本整体结构

URScript 的主程序本质上是一个函数。最常见写法:

```urscript
def main():
  textmsg("hello")
end
```

核心块关键字:

- `def ... :`
- `if / elif / else`
- `while`
- `end`

扩展块结构:

- `thread ... :`
- `sec ... :`

如果脚本通过 socket 发给控制器执行，通常应满足:

- 除最外层 `def` 和对应 `end` 外，其余语句带至少一级缩进
- 脚本最后一行是顶格 `end`

## 2. 注释、大小写与标识符

### 注释

使用 `#`:

```urscript
# this is a comment
movej(q_home)
```

### 大小写

URScript 大小写敏感。

```urscript
True
False
```

### 标识符

建议规则:

- 由字母、数字、下划线组成
- 以字母或下划线开头
- 不与关键字重名
- 不覆盖系统函数名

## 3. 多行表达式

URScript 中常见的多行表达式包括:

- 多行 `p[...]`
- 多行 list
- 多行 matrix
- 多行 `struct(...)`
- 多行函数调用

示例:

```urscript
target = p[
  0.4,
  0.2,
  0.3,
  0.0,
  3.14159,
  0.0
]
```

做解析器时，不要简单按“一行一条语句”切分。

## 4. 数据类型与字面量

基础类型:

- `none`
- `bool`
- `number`
- `string`
- `pose`

工程里常见扩展容器:

- `list`
- `struct`
- `matrix`

### 数字

```urscript
a = 1
b = 3.14159
c = -0.25
```

### 布尔

```urscript
flag = True
ready = False
```

### 字符串

```urscript
msg = "Hello"
```

注意:

- 官方把字符串视作字节数组
- 长度相关函数按字节工作

### Pose

```urscript
target = p[0.4, 0.2, 0.3, 0.0, 3.14159, 0.0]
```

格式:

```text
p[x, y, z, ax, ay, az]
```

其中后三项是轴角旋转向量，不是欧拉角。

### None

函数不返回值时，建议显式写:

```urscript
return None
```

## 5. 表达式与运算符

### 算术运算

```urscript
1 + 2 - 3
4 * 5 / 6
(1 + 2) * 3
2346.44 % 10
```

常见运算符:

- `+`
- `-`
- `*`
- `/`
- `%`

### 比较运算

```urscript
a == b
a != b
a < b
a <= b
a > b
a >= b
```

### 布尔运算

URScript 使用单词形式:

```urscript
True or False
not ready and ok
a xor b
```

常见运算符:

- `and`
- `or`
- `not`
- `xor`

复杂条件建议总是加括号。

### 赋值

```urscript
foo = 42
bar = False or True
```

### 下标与成员访问

```urscript
arr = [10, 20, 30]
v = arr[0]

mat = [[1, 2], [3, 4]]
x = mat[0, 1]

cfg = struct(speed = 0.25)
y = cfg.speed
```

## 6. List、Struct、Matrix

### Struct

```urscript
part = struct(id = 1, name = "bolt", ok = True)
```

特点:

- 成员名来自命名参数
- 成员类型初始化后不能变
- 可嵌套
- 可作为参数和返回值

### List

固定长度:

```urscript
a = [11, 22, 33, 44]
```

可变长度:

```urscript
b = make_list(length = 7, initial_value = 11, capacity = 20)
```

注意:

- `length` 是当前长度
- `capacity` 是最大容量
- 容量创建后不能改
- 元素类型不能变
- 普通 list 套 list 不支持，因为这种写法会被解释为 matrix

### Matrix

```urscript
m = [[1, 2], [3, 4], [5, 6]]
```

常见能力:

- 矩阵乘矩阵
- 矩阵乘向量
- 数组与数组逐元素运算
- 数组/矩阵与标量运算

## 7. 控制流

### if / elif / else

```urscript
if a > 3:
  a = a + 1
elif b < 7:
  b = b * a
else:
  a = a + b
end
```

### while

```urscript
i = 0
while i < 5:
  i = i + 1
end
```

### break / continue

```urscript
while True:
  if stop_flag:
    break
  end
  if skip_flag:
    continue
  end
end
```

### 特殊关键字

- `halt`
- `return`
- `pause`

机器人在运动时直接 `halt` 风险较高，应谨慎使用。

## 8. 函数

### 定义

```urscript
def add(a, b):
  return a + b
end
```

### 调用

```urscript
result = add(1, 4)
```

### 默认参数

```urscript
def add(a = 0, b = 0):
  return a + b
end
```

### 命名参数

```urscript
def blend_move(v = 0.25, a = 1.2):
  return [v, a]
end

cfg = blend_move(a = 0.8, v = 0.2)
```

### 传参语义

官方语义是按值传递，包括数组和容器。

这意味着:

- 函数内部修改的是参数副本
- 外部原变量不会被同步改写

## 9. 延伸阅读

- [作用域与线程](./scope-and-threads.md)
- [运动指令](./motion.md)
- [常见坑](./pitfalls.md)
