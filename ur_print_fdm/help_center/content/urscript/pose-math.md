# 位姿、运动学与数学

这页整理 URScript 中和 `pose`、位姿变换、运动学以及常见数学运算相关的内容。

## 1. Pose 表示

URScript 位姿格式:

```urscript
p[x, y, z, ax, ay, az]
```

含义:

- `x, y, z`: TCP 位置
- `ax, ay, az`: 轴角旋转向量

最重要的提醒:

- 它不是 RPY
- 它不是四元数
- 解析、可视化、插值时都不能把后三项按欧拉角处理

## 2. 常见位姿函数

### pose_trans

```urscript
out = pose_trans(p_from, p_from_to)
```

用途:

- 位姿复合
- 最适合做 feature 坐标系下的目标点生成

### pose_add

```urscript
out = pose_add(p1, p2)
```

用途:

- 简化位姿叠加

注意:

- 它不等同于严格的 SE(3) 乘法语义

### pose_sub

```urscript
out = pose_sub(p_to, p_from)
```

用途:

- 求位姿差

### pose_inv

```urscript
out = pose_inv(p)
```

用途:

- 位姿求逆

### pose_dist / point_dist

```urscript
d1 = pose_dist(p1, p2)
d2 = point_dist(p1, p2)
```

用途:

- `pose_dist`: 位姿距离
- `point_dist`: 点位置距离

### interpolate_pose

```urscript
mid = interpolate_pose(p_from, p_to, alpha)
```

用途:

- 在两个 pose 之间插值

## 3. 运动学函数

### get_forward_kin

```urscript
p = get_forward_kin()
p = get_forward_kin(q)
```

用途:

- 获取正运动学结果

工程用途:

- 作为控制器 FK 参考通道
- 与自写 FK 做误差对比

### get_inverse_kin

```urscript
q = get_inverse_kin(pose)
```

用途:

- 求逆运动学解

### get_inverse_kin_has_solution

```urscript
ok = get_inverse_kin_has_solution(pose)
```

用途:

- 判断某个位姿是否存在 IK 解

## 4. 常见数学函数

- `sin(x)`
- `cos(x)`
- `tan(x)`
- `atan2(y, x)`
- `sqrt(x)`
- `pow(x, y)`
- `norm(v)`
- `normalize(v)`
- `length(v)`
- `d2r(d)`
- `r2d(r)`

## 5. 工程建议

### 姿态内部表示

如果你在做解析器、可视化器、回放器:

- 内部统一用旋转矩阵或四元数
- 欧拉角只用于展示

### 姿态误差

建议直接比较旋转矩阵误差，而不是直接减后三项轴角向量。

### TCP 与法兰

一定要区分:

- 法兰位姿
- TCP 位姿
- 喷嘴或工艺点位姿

这对打印、点胶、焊接一类场景尤其关键。

## 6. 相关页面

- [运动指令](./motion.md)
- [系统、I/O 与 RPC](./io-and-runtime.md)
- [示例脚本](./examples.md)
