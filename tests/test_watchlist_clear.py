"""The clear-watchlist action must reset widget state, not only the URL."""
import ast
from pathlib import Path
from types import SimpleNamespace


def test_clear_watchlist_resets_both_player_types_and_share_parameters():
    module = ast.parse(Path("app.py").read_text(encoding="utf-8"))
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "clear_report_query")
    query = {"page": "球探報告", "watchlist": ["123"], "report_type": "打者",
             "report_team": "全部", "report_threshold": "50", "report_focus": "綜合"}
    session = {"report_watchlist_打者": ["A"], "report_watchlist_投手": ["B"], "unrelated": "keep"}
    namespace = {"st": SimpleNamespace(query_params=query, session_state=session)}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "app.py", "exec"), namespace)
    namespace["clear_report_query"]()
    assert query == {"page": "球探報告"}
    assert session == {"unrelated": "keep"}


def test_clear_button_uses_a_pre_render_callback():
    module = ast.parse(Path("app.py").read_text(encoding="utf-8"))
    buttons = [node for node in ast.walk(module) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Attribute) and node.func.attr == "button"
               and node.args and isinstance(node.args[0], ast.Constant)
               and node.args[0].value == "清除觀察名單"]
    assert len(buttons) == 1
    assert any(keyword.arg == "on_click" and isinstance(keyword.value, ast.Name)
               and keyword.value.id == "clear_report_query" for keyword in buttons[0].keywords)
