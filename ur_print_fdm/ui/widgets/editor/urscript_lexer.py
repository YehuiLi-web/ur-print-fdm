"""
URScript 自定义词法分析器
提供更完整的 URScript 语法高亮与补全数据导出。
"""

from PyQt6.QtGui import QColor, QFont

try:
    from PyQt6.Qsci import QsciLexerCustom
except ImportError:
    QsciLexerCustom = None

from .urscript_metadata import (
    ALL_URSCRIPT_COMMANDS,
    DECLARATION_KEYWORDS,
    URSCRIPT_CONTAINER_FUNCTIONS,
    URSCRIPT_FORCE_COMMANDS,
    URSCRIPT_IO_COMMANDS,
    URSCRIPT_KEYWORDS,
    URSCRIPT_MATH_FUNCTIONS,
    URSCRIPT_MOTION_COMMANDS,
    URSCRIPT_POSE_FUNCTIONS,
    URSCRIPT_ROBOT_COMMANDS,
    URSCRIPT_RUNTIME_COMMANDS,
    URSCRIPT_TYPES,
    get_urscript_completions,
)


def _style_for_word(word: str) -> int | None:
    if word in URSCRIPT_KEYWORDS:
        return URScriptLexer.Keyword
    if word in URSCRIPT_TYPES:
        return URScriptLexer.Type
    if word in URSCRIPT_MOTION_COMMANDS:
        return URScriptLexer.MotionCommand
    if word in URSCRIPT_IO_COMMANDS:
        return URScriptLexer.IOCommand
    if word in URSCRIPT_ROBOT_COMMANDS:
        return URScriptLexer.RobotCommand
    if word in URSCRIPT_MATH_FUNCTIONS:
        return URScriptLexer.MathFunction
    if word in URSCRIPT_POSE_FUNCTIONS:
        return URScriptLexer.PoseFunction
    if word in URSCRIPT_FORCE_COMMANDS:
        return URScriptLexer.ForceCommand
    if word in URSCRIPT_RUNTIME_COMMANDS:
        return URScriptLexer.RuntimeCommand
    if word in URSCRIPT_CONTAINER_FUNCTIONS:
        return URScriptLexer.ContainerFunction
    return None


if QsciLexerCustom is not None:
    class URScriptLexer(QsciLexerCustom):
        """URScript 自定义词法分析器。"""

        Default = 0
        Comment = 1
        Keyword = 2
        Type = 3
        MotionCommand = 4
        IOCommand = 5
        RobotCommand = 6
        MathFunction = 7
        PoseFunction = 8
        String = 9
        Number = 10
        Operator = 11
        Identifier = 12
        ForceCommand = 13
        RuntimeCommand = 14
        ContainerFunction = 15
        DefinitionName = 16
        ProgramLabel = 17

        def __init__(self, parent=None):
            super().__init__(parent)
            self._font = QFont("Consolas", 11)
            self._font.setFixedPitch(True)

            self._colors = {
                self.Default: QColor("#e0e0e0"),
                self.Comment: QColor("#6A9955"),
                self.Keyword: QColor("#569CD6"),
                self.Type: QColor("#4EC9B0"),
                self.MotionCommand: QColor("#DCDCAA"),
                self.IOCommand: QColor("#C586C0"),
                self.RobotCommand: QColor("#9CDCFE"),
                self.MathFunction: QColor("#B5CEA8"),
                self.PoseFunction: QColor("#4FC1FF"),
                self.String: QColor("#CE9178"),
                self.Number: QColor("#B5CEA8"),
                self.Operator: QColor("#858585"),
                self.Identifier: QColor("#e0e0e0"),
                self.ForceCommand: QColor("#FF8C00"),
                self.RuntimeCommand: QColor("#DCDCAA"),
                self.ContainerFunction: QColor("#4EC9B0"),
                self.DefinitionName: QColor("#DCDCAA"),
                self.ProgramLabel: QColor("#6A9955"),
            }
            self._paper = QColor("#1e1e1e")

        def language(self):
            return "URScript"

        def description(self, style):
            descriptions = {
                self.Default: "Default",
                self.Comment: "Comment",
                self.Keyword: "Keyword",
                self.Type: "Type",
                self.MotionCommand: "Motion Command",
                self.IOCommand: "IO Command",
                self.RobotCommand: "Robot Command",
                self.MathFunction: "Math Function",
                self.PoseFunction: "Pose Function",
                self.String: "String",
                self.Number: "Number",
                self.Operator: "Operator",
                self.Identifier: "Identifier",
                self.ForceCommand: "Force Command",
                self.RuntimeCommand: "Runtime Command",
                self.ContainerFunction: "Container Function",
                self.DefinitionName: "Definition Name",
                self.ProgramLabel: "Program Label",
            }
            return descriptions.get(style, "")

        def defaultColor(self, style):
            return self._colors.get(style, self._colors[self.Default])

        def defaultPaper(self, style):
            return self._paper

        def defaultFont(self, style):
            return self._font

        def setColors(self, colors_dict):
            self._colors.update(colors_dict)
            for style, color in colors_dict.items():
                super().setColor(color, style)

        def setPaper(self, color, style=None):
            self._paper = color
            for style_index in range(self.ProgramLabel + 1):
                super().setPaper(color, style_index)

        def setFont(self, font):
            self._font = font
            for style_index in range(self.ProgramLabel + 1):
                super().setFont(font, style_index)

        def styleText(self, start, end):
            editor = self.editor()
            if not editor:
                return

            full_text = editor.text()
            if not full_text:
                return

            text_bytes = full_text.encode("utf-8")
            start = max(0, min(start, len(text_bytes)))
            end = max(start, min(end, len(text_bytes)))

            portion_bytes = text_bytes[start:end]
            try:
                text = portion_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = full_text
                start = 0

            if not text:
                return

            self.startStyling(start)

            i = 0
            length = len(text)
            expect_definition_name = False

            while i < length:
                ch = text[i]

                if ch == "#":
                    j = i + 1
                    while j < length and text[j] != "\n":
                        j += 1
                    self.setStyling(len(text[i:j].encode("utf-8")), self.Comment)
                    i = j
                    continue

                if ch == "$":
                    j = i + 1
                    while j < length and text[j] != "\n":
                        j += 1
                    self.setStyling(len(text[i:j].encode("utf-8")), self.ProgramLabel)
                    i = j
                    continue

                if ch in {'"', "'"}:
                    quote = ch
                    j = i + 1
                    while j < length:
                        if text[j] == "\\" and j + 1 < length:
                            j += 2
                            continue
                        if text[j] == quote:
                            j += 1
                            break
                        j += 1
                    self.setStyling(len(text[i:j].encode("utf-8")), self.String)
                    i = j
                    continue

                is_negative_start = (
                    ch == "-"
                    and i + 1 < length
                    and text[i + 1].isdigit()
                    and (i == 0 or text[i - 1] in " \t\n\r=([,<>!&|^~:+*/%")
                )
                if ch.isdigit() or is_negative_start:
                    j = i + 1 if ch == "-" else i
                    while j < length and (text[j].isdigit() or text[j] in ".eE+-"):
                        j += 1
                    self.setStyling(len(text[i:j].encode("utf-8")), self.Number)
                    i = j
                    expect_definition_name = False
                    continue

                if ch.isalpha() or ch == "_":
                    j = i + 1
                    while j < length and (text[j].isalnum() or text[j] == "_"):
                        j += 1
                    word = text[i:j]
                    byte_len = len(word.encode("utf-8"))

                    if expect_definition_name:
                        self.setStyling(byte_len, self.DefinitionName)
                        expect_definition_name = False
                    else:
                        style = _style_for_word(word)
                        if style is None:
                            self.setStyling(byte_len, self.Identifier)
                        else:
                            self.setStyling(byte_len, style)
                            if word in DECLARATION_KEYWORDS:
                                expect_definition_name = True

                    i = j
                    continue

                if ch in "+-*/%=<>!&|^~:,()[]{}.":
                    self.setStyling(1, self.Operator)
                    if not ch.isspace():
                        if expect_definition_name and ch not in " \t":
                            expect_definition_name = False
                    i += 1
                    continue

                self.setStyling(len(ch.encode("utf-8")), self.Default)
                i += 1

else:
    class URScriptLexer:
        """QScintilla 不可用时的占位类。"""

        def __init__(self, parent=None):
            pass
