import ast
from pathlib import Path


SCRIPT = Path(__file__).parents[2] / "maixcam2" / "main.py"


def test_maixcam2_defaults_to_stable_rtsp_transport():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    mode_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "MODE" for target in node.targets)
    )

    assert ast.literal_eval(mode_assignment.value) == "rtsp"


def test_uvc_mode_does_not_require_local_display():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))

    display_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "display"
        and node.func.attr == "Display"
    ]

    assert display_calls == [], "UVC 模式不应占用 MaixCAM2 本地显示资源"


def test_uvc_mode_creates_its_own_uvc_server():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    constructors = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "uvc"
    }

    assert "UvcServer" in constructors
    assert "UvcStreamer" not in constructors
