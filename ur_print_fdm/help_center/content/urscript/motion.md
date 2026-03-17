# URScript 运动指令

这页整理最常用的 URScript 运动、伺服、速度和停止相关指令。

## 1. 常用指令总览

| 指令 | 典型目标 | 说明 |
| --- | --- | --- |
| `movej` | 关节角或 pose | 关节空间运动 |
| `movel` | pose | TCP 直线运动 |
| `movep` | pose | 平滑路径运动 |
| `movec` | via pose + target pose | 圆弧运动 |
| `servoj` | 关节角 | 高频关节伺服 |
| `servoc` | pose | 笛卡尔伺服 |
| `speedj` | 关节速度 | 给关节速度 |
| `speedl` | TCP 速度 | 给笛卡尔速度 |
| `stopj` | 减速度 | 停止关节运动 |
| `stopl` | 减速度 | 停止笛卡尔运动 |

## 2. movej

```urscript
movej(q, a = 1.4, v = 1.05, t = 0, r = 0)
```

用途:

- 关节空间运动
- 适合大姿态切换、快速到位、避障过渡

参数:

- `q`: 目标关节角列表，也可能是由控制器解 IK 的 pose
- `a`: 关节加速度
- `v`: 关节速度
- `t`: 指定运动时间
- `r`: blend 半径

## 3. movel

```urscript
movel(pose, a = 1.2, v = 0.25, t = 0, r = 0)
```

用途:

- TCP 直线运动
- 打印、点胶、焊缝、路径跟随最常用

## 4. movep

```urscript
movep(pose, a = 1.2, v = 0.25, r = 0)
```

用途:

- 平滑路径运动
- 适合要求速度连续性的工艺段

## 5. movec

```urscript
movec(pose_via, pose_to, a = 1.2, v = 0.25, r = 0, mode = 0)
```

参数:

- `pose_via`: 过渡点
- `pose_to`: 终点
- `mode`: 圆弧模式参数

工程建议:

- 离线回放不要把它简化成一条直线
- 最好按起点、`pose_via`、终点构造圆弧近似

## 6. servoj

```urscript
servoj(q, a, v, t = 0.002, lookahead_time = 0.1, gain = 300)
```

用途:

- 高频关节伺服
- 外部实时控制常用

关键参数:

- `t`: 控制步长
- `lookahead_time`: 前瞻时间
- `gain`: 伺服增益

## 7. servoc

```urscript
servoc(pose, a = 1.2, v = 0.25, r = 0)
```

用途:

- 对笛卡尔目标进行伺服式控制

## 8. speedj

```urscript
speedj(qd, a, t)
```

用途:

- 直接给关节速度

参数:

- `qd`: 关节速度向量
- `a`: 加速度
- `t`: 维持时间

## 9. speedl

```urscript
speedl(xd, a, t, aRot = "a")
```

用途:

- 直接给 TCP 速度

参数:

- `xd`: `[vx, vy, vz, wx, wy, wz]`
- `a`: 平移加速度
- `t`: 维持时间
- `aRot`: 旋转方向相关参数

## 10. stopj / stopl

```urscript
stopj(a)
stopl(a, aRot = "a")
```

用途:

- 让当前速度控制或伺服动作平稳收敛停止

## 11. 常见参数说明

### `a`

通常表示加速度:

- `movej / speedj / stopj` 中更偏关节侧量
- `movel / speedl / stopl` 中更偏笛卡尔侧量

### `v`

通常表示速度:

- `movej` 中常指关节速度
- `movel` 中常指 TCP 线速度

### `t`

通常表示动作时长或持续时间:

- 在 `movej / movel` 中常作为目标时长
- 在 `speedj / speedl` 中常作为维持速度命令的时间

### `r`

blend 半径，用于轨迹拼接和圆滑衔接。

## 12. 可视化与解析建议

如果你在做离线回放器:

- `movej` 更适合按关节空间插值
- `movel / movep` 更适合按 TCP 线性插值
- `movec` 应单独做圆弧近似
- `speedj / speedl` 应按时间步展开成多帧

## 13. 相关页面

- [位姿与数学](./pose-math.md)
- [示例脚本](./examples.md)
- [常见坑](./pitfalls.md)
