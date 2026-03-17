# 示例脚本

这页放适合直接参考和复制改写的 URScript 片段。

## 1. 最小主程序

```urscript
def main():
  textmsg("start")
end
```

## 2. 设置 TCP 后做关节到线性运动

```urscript
def main():
  set_tcp(p[0, 0, 0.12, 0, 0, 0])
  movej([0, -1.57, 1.57, -1.57, -1.57, 0], a = 1.0, v = 1.0)
  movel(p[0.30, 0.10, 0.25, 0, 3.14159, 0], a = 0.5, v = 0.05)
end
```

## 3. 基于 feature 的位姿变换

```urscript
def main():
  feature = p[0.2, 0.1, 0.1, 0, 0, 0]
  local_target = p[0.05, 0.00, 0.00, 0, 0, 0]
  target = pose_trans(feature, local_target)
  movel(target, a = 0.2, v = 0.03)
end
```

## 4. 看门狗线程

```urscript
def main():
  global stop_flag = False

  thread watchdog():
    while not stop_flag:
      textmsg("watchdog alive")
      sleep(0.1)
    end
    return None
  end

  th = run watchdog()
  sleep(0.5)
  stop_flag = True
  join th
end
```

## 5. Secondary Program 只做 I/O

```urscript
sec io_helper():
  set_digital_out(0, True)
end
```

## 6. 速度控制后平稳停止

```urscript
def main():
  speedl([0.0, 0.0, -0.02, 0.0, 0.0, 0.0], 0.5, 0.5)
  stopl(1.0)
end
```

## 7. 命名参数示例

```urscript
def blend_move(v = 0.25, a = 1.2):
  return [v, a]
end

def main():
  cfg = blend_move(a = 0.8, v = 0.2)
  textmsg(cfg[0], cfg[1])
end
```

## 8. 相关阅读

- [语法基础](./grammar.md)
- [运动指令](./motion.md)
- [位姿与数学](./pose-math.md)
- [常见坑](./pitfalls.md)
