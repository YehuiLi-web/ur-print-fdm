# 作用域与线程

这页集中讲 URScript 里最容易出语义问题的部分: `global/local`、第一层作用域、线程、`sec` 和 Program Label。

## 1. 作用域

### 三种写法

- `global x = ...`
- `local x = ...`
- 自由变量 `x = ...`

### 基本规则

可以把官方规则简化成:

1. `global` 强制定义或绑定全局变量
2. `local` 强制定义局部变量
3. 自由变量先查全局是否已有同名；有则绑定全局，没有则作为局部

### 遮蔽

```urscript
def myProg():
  global a = 0
  def myFun():
    local a = 1
  end
end
```

这里两个 `a` 相互独立。

### 第一层缩进是“准全局”

这条是 URScript 最容易误判的规则之一。

```urscript
def myProg():
  a = 0
  def myFun():
    a = 1
  end
end
```

在这种情况下，第一层作用域里的 `a` 会被当成全局，因此内层函数里的自由变量 `a` 绑定的是同一个变量。

## 2. 线程

### 定义线程

```urscript
thread watcher():
  textmsg("watching")
  return False
end
```

注意:

- 线程不能带参数
- `()` 必须为空
- `return` 可以写，但返回值会被丢弃

### 启动线程

```urscript
th = run watcher()
```

`run` 返回线程句柄。

### 等待线程

```urscript
join th
```

当前线程会等待 `th` 结束。

### 杀死线程

```urscript
kill th
```

线程被杀死后，句柄失效；它创建的子线程也会一起停止。

## 3. Critical Section

```urscript
thread watcher():
  enter_critical
  # shared state
  exit_critical
end
```

注意:

- `sleep`
- `sync`
- move 指令
- 某些阻塞 I/O

这些都属于耗时操作，放进 critical section 会显著削弱保护意义。

## 4. 调度与实时性

URScript 的线程调度和控制器实时循环密切相关，常见控制周期约为 `500 Hz`，也就是 `0.002 s`。

实际建议:

- 纯计算死循环里加入 `sync()` 或 `sleep()`
- 不要让后台线程一直满负荷空转

否则容易触发控制器通信丢失、实时超时或保护停机。

## 5. Program Label

PolyScope 自动生成的脚本常带这种行:

```urscript
$ 2 "var_1 = True"
global var_1 = True
```

用途:

- 跟踪程序执行位置
- 配合界面调试和程序树定位

对解析器的建议:

- 识别 `$` 行
- 但通常不要把它当作普通可执行语句

## 6. Secondary Program

### 定义

```urscript
sec io_helper():
  set_digital_out(1, True)
end
```

### 作用

Secondary program 与 primary program 并发执行，适合做轻量辅助逻辑，尤其是 I/O。

### 限制

- 不能用 move 指令
- 不应使用 `sleep`
- 不支持线程
- 不适合做阻塞式 socket 或 XML-RPC

简单理解:

- `sec` 更像实时辅助钩子
- 不是另一个完整主程序

## 7. 调试建议

作用域和线程相关问题通常可以从这几个方向排查:

- 看变量是不是落在第一层作用域
- 看自由变量是否意外绑定了全局
- 看线程循环里是否缺 `sync()` 或 `sleep()`
- 看 `sec` 里是否用了不允许的阻塞动作

## 8. 相关页面

- [语法基础](./grammar.md)
- [示例脚本](./examples.md)
- [常见坑](./pitfalls.md)
