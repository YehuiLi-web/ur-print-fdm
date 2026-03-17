from __future__ import annotations

from datetime import datetime


_NOTE_TEMPLATES: tuple[dict[str, str], ...] = (
    {
        "id": "note_1",
        "category": "打印工艺",
        "title": "风扇防拖拽",
        "content": "纯预浸渍碳纤维打印用风扇对着吹可以防拖拽。",
    },
    {
        "id": "note_2",
        "category": "机械问题",
        "title": "喷头变角度打印",
        "content": (
            "打印喷头变角度，倾斜30度进行打印。变角度的关键是要把TCP标定好，"
            "因为是沿着工具坐标原点进行旋转的，绕y轴旋转角度就是将角度放在第二个位姿角度上，"
            "函数为pose_trans(原来的，改变角度)。"
        ),
    },
    {
        "id": "note_3",
        "category": "打印工艺",
        "title": "温度和速度设置",
        "content": (
            "温度设置为190度，速度为8mm到16mm/s，纤维线宽为0.8，线宽大概设置为0.6，"
            "但是存在覆盖的现象，最大的问题就是两边拖拽。"
        ),
    },
    {
        "id": "note_4",
        "category": "机械问题",
        "title": "Feature坐标含义",
        "content": (
            "Feature坐标的含义，是相对base坐标的变换。例如feature"
            "(0.2，0.1，0.2，0，0，1.57)含义是相对base坐标，X轴偏移0.2m，"
            "y轴偏移0.1m，z轴偏移0.2m，坐标旋转，绕Z轴旋转了1.57弧度（约90度）。"
        ),
    },
    {
        "id": "note_5",
        "category": "机械问题",
        "title": "Feature坐标Z轴调整",
        "content": (
            "例如在设置好的feature坐标系下本来可以正常打印，现在因为把打印喷头往下拧了，"
            "也就是说不更改的话就要产生碰撞。解决方法是将feature坐标的Z轴调高。"
        ),
    },
    {
        "id": "note_6",
        "category": "机械问题",
        "title": "相对运动理解",
        "content": (
            "如何理解：运动是相对运动，是相对feature坐标Z的偏移。例如本来Z=200，"
            "机械臂设置相对移动距离为100，则机械臂实际会走到300，这时改变Z为210，"
            "则机械臂实际会走到310，也就是相当于抬升了。"
        ),
    },
    {
        "id": "note_7",
        "category": "打印工艺",
        "title": "第一层打印高度",
        "content": (
            "打印第一层时，第一层的打印高度会严重影响打印质量及其重要，如果偏高的话就会导致"
            "线材不贴合，就产生类似波浪状的形状，如果偏低就会堆料，但是看起来的效果要好一点。"
        ),
    },
    {
        "id": "note_8",
        "category": "挤出问题",
        "title": "打印头出料困难",
        "content": (
            "打印头出料困难，尝试拧松大喷嘴，手动挤压线材，看是否出料，如果出料，"
            "大概率就是小喷嘴太大太长了压迫或者说是堵住出料了，使出料困难。"
        ),
    },
    {
        "id": "note_9",
        "category": "硬件问题",
        "title": "白色导管插入检查",
        "content": "打印头不出料的话强烈建议检查一下白色导管是否完全插入喉管。",
    },
    {
        "id": "note_10",
        "category": "维护保养",
        "title": "喷嘴安装",
        "content": "喷嘴得加热才能拧进去。",
    },
    {
        "id": "note_11",
        "category": "维护保养",
        "title": "挤出机齿轮声音",
        "content": "注意挤出机齿轮的声音，有响声的话证明阻力很大，需要注意打印头的问题，查看是哪里堵住了。",
    },
    {
        "id": "note_12",
        "category": "挤出问题",
        "title": "打印头堵住处理",
        "content": "打印头堵住，需要观察风扇是否在转，温度合适不。",
    },
    {
        "id": "note_13",
        "category": "硬件问题",
        "title": "转盘打印注意事项",
        "content": (
            "用到转盘打印时要注意必须开电源才能使用，而电源和是加热在一起的转盘打印同步问题不好解决，"
            "往往不是按照设定的步长去运行的，需要手动调，或者尝试一下多线程打印。"
        ),
    },
    {
        "id": "note_14",
        "category": "挤出问题",
        "title": "地线接触不良",
        "content": "挤出机出料不均匀一卡一卡的大概率就是地线接触不良拔了重新插，通过调成3000检验齿轮是否转动。",
    },
)


def default_printing_notes(timestamp: str | None = None) -> list[dict[str, str]]:
    stamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notes: list[dict[str, str]] = []
    for template in _NOTE_TEMPLATES:
        item = dict(template)
        item["created_at"] = stamp
        item["updated_at"] = stamp
        notes.append(item)
    return notes
