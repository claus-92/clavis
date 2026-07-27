from click import unstyle
from typer.testing import CliRunner

from clavis.daemon import app
from clavis.runtime import DEFAULT_UDS


runner = CliRunner()


def test_daemon_is_socket_only() -> None:
    result = runner.invoke(app, ["--help"])
    output = unstyle(result.output)

    assert result.exit_code == 0
    assert "--uds" in output
    assert "--host" not in output
    assert "--port" not in output


def test_daemon_uses_default_socket(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr("clavis.daemon.Path.mkdir", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("clavis.daemon.os.umask", lambda mode: captured.update(umask=mode))
    monkeypatch.setattr("clavis.daemon.uvicorn.run", lambda app_name, **kwargs: captured.update(app=app_name, **kwargs))

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert captured == {"umask": 0o007, "app": "clavis.api.app:app", "uds": DEFAULT_UDS}


def test_daemon_command_line_socket_overrides_environment(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr("clavis.daemon.Path.mkdir", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("clavis.daemon.os.umask", lambda _mode: None)
    monkeypatch.setattr("clavis.daemon.uvicorn.run", lambda _app_name, **kwargs: captured.update(kwargs))

    result = runner.invoke(
        app,
        ["--uds", "/tmp/command.sock"],
        env={"CLAVIS_UDS": "/tmp/environment.sock"},
    )

    assert result.exit_code == 0
    assert captured["uds"] == "/tmp/command.sock"
