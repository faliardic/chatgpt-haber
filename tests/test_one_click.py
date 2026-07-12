from __future__ import annotations

import inspect
from pathlib import Path

from chatgpt_haber import one_click


class Status:
    def __init__(self) -> None:
        self.values: list[str] = []

    def set(self, value: str) -> None:
        self.values.append(value)


class Done:
    def __init__(self) -> None:
        self.called = False

    def set(self) -> None:
        self.called = True


def test_one_click_uses_run_build_service_function():
    source = inspect.getsource(one_click)

    assert "from chatgpt_haber.cli import run_build" in source
    assert "from chatgpt_haber.cli import build" not in source


def test_build_today_issue_passes_explicit_full_mode(monkeypatch, tmp_path):
    calls: dict[str, object] = {}

    monkeypatch.setattr(one_click, "desktop_dir", lambda: tmp_path)

    def fake_run_build(**kwargs):
        calls.update(kwargs)
        Path(kwargs["out"]).parent.mkdir(parents=True, exist_ok=True)
        Path(kwargs["out"]).write_bytes(b"%PDF-1.4\n")
        return {"pdf": kwargs["out"]}

    monkeypatch.setattr(one_click, "run_build", fake_run_build)
    status = Status()
    done = Done()
    result: dict[str, object] = {}

    one_click.build_today_issue(status, done, result)

    assert done.called is True
    assert result["out"] == calls["out"]
    assert calls["paper_size"] == "A3"
    assert calls["input_json"] is None
    assert calls["live"] is True
    assert calls["portable_html"] is False
    assert calls["mode"] == "full"


def test_build_today_issue_writes_error_log(monkeypatch, tmp_path):
    monkeypatch.setattr(one_click, "desktop_dir", lambda: tmp_path)

    def fake_run_build(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(one_click, "run_build", fake_run_build)
    status = Status()
    done = Done()
    result: dict[str, object] = {}

    one_click.build_today_issue(status, done, result)

    assert done.called is True
    assert isinstance(result["error"], RuntimeError)
    assert Path(result["log_path"]).name == "son-hata.txt"
    assert Path(result["log_path"]).exists()
