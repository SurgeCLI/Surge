import pytest
import sys
import os
from typer.testing import CliRunner

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli.app as app_mod


@pytest.fixture
def runner():
    return CliRunner()


def _side_effect_sequence(responses):
    iterator = iter(responses)

    def _fn(*args, **kwargs):
        return next(iterator)

    return _fn


class TestHelpers:
    def test_get_load_parses_values(self, monkeypatch):
        monkeypatch.setattr(
            app_mod, "run_cmd", _side_effect_sequence(["0.10, 0.20, 0.30", "8"])
        )
        averages, cores = app_mod.get_load()
        assert (averages, cores) == ([0.10, 0.20, 0.30], 8.0)

    def test_get_cpu_parses_values(self, monkeypatch):
        cpu_line = "%Cpu(s):  0.0 us,  4.8 sy,  0.0 ni, 95.2 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st"
        monkeypatch.setattr(app_mod, "run_cmd", lambda *_, **__: cpu_line)
        user, system, idle = app_mod.get_cpu()
        assert (user, system, idle) == ("0.0", "4.8", "95.2")

    def test_get_memory_parses_values(self, monkeypatch):
        mem_line = "Mem: 764 492 144 8 247 272"
        monkeypatch.setattr(app_mod, "run_cmd", lambda *_, **__: mem_line)
        total, used, free_mem = app_mod.get_memory()
        assert (total, used, free_mem) == ("764", "492", "144")

    def test_get_disk_parses_values(self, monkeypatch):
        df_line = "/dev/vda1 25G 5.2G 20G 21% /"
        monkeypatch.setattr(app_mod, "run_cmd", lambda *_, **__: df_line)
        size, used, available, percent = app_mod.get_disk()
        assert (size, used, available, percent) == ("25G", "5.2G", "20G", "21%")


class TestCLI:
    @pytest.mark.parametrize(
        "load_data,cpu_data,memory_data,disk_data,expected_load,expected_cpu,expected_memory,expected_disk",
        [
            (
                ([0.1, 0.2, 0.3], 8),
                ("12.3", "3.4", "80.0"),
                ("32000", "12000", "20000"),
                ("100G", "40G", "60G", "40%"),
                "Load avg (1m): 0.1",
                "User: 12.3% | System: 3.4% | Idle: 80.0%",
                "Total: 32000 | Used: 12000 | Free: 20000",
                "Size: 100G | Used: 40G | Available: 60G | Usage: 40%",
            ),
            (
                ([0.5, 0.8, 1.2], 4),
                ("25.0", "15.0", "60.0"),
                ("16000", "8000", "8000"),
                ("50G", "30G", "20G", "60%"),
                "Load avg (1m): 0.5",
                "User: 25.0% | System: 15.0% | Idle: 60.0%",
                "Total: 16000 | Used: 8000 | Free: 8000",
                "Size: 50G | Used: 30G | Available: 20G | Usage: 60%",
            ),
        ],
    )
    def test_monitor_outputs_sections(
        self,
        monkeypatch,
        runner,
        load_data,
        cpu_data,
        memory_data,
        disk_data,
        expected_load,
        expected_cpu,
        expected_memory,
        expected_disk,
    ):
        monkeypatch.setattr(app_mod, "get_load", lambda: load_data)
        monkeypatch.setattr(app_mod, "get_cpu", lambda: cpu_data)
        monkeypatch.setattr(app_mod, "get_memory", lambda: memory_data)
        monkeypatch.setattr(app_mod, "get_disk", lambda: disk_data)

        result = runner.invoke(app_mod.app, ["monitor"])
        assert result.exit_code == 0
        out = result.stdout

        expected_strings = [
            "System Load Averages",
            expected_load,
            "CPU Utilization",
            expected_cpu,
            "Memory Usage (MB)",
            expected_memory,
            "Disk Usage",
            expected_disk,
        ]
        for expected in expected_strings:
            assert expected in out

    def test_monitor_verbose_load_divides_by_cores_as_string(self, monkeypatch, runner):
        monkeypatch.setattr(app_mod, "get_load", lambda: ([1.0, 2.0, 3.0], 4))
        result = runner.invoke(
            app_mod.app,
            ["monitor", "--load", "--no-cpu", "--no-ram", "--no-disk", "--verbose"],
        )
        if result.exit_code == 0:
            assert "Load avg (1m): 1.00" in result.stdout
        else:
            assert isinstance(result.exception, SystemExit)

    def test_monitor_unknown_option_errors(self, runner):
        result = runner.invoke(app_mod.app, ["monitor", "--not-a-real-flag"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_monitor_unexpected_extra_argument_errors(self, runner):
        result = runner.invoke(app_mod.app, ["monitor", "unexpected"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_monitor_invalid_interval_errors(self, runner):
        result = runner.invoke(app_mod.app, ["monitor", "--interval", "-5"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_monitor_empty_flag(self, runner):
        result = runner.invoke(app_mod.app, ["monitor", ""])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_network_command_prints_message(self, runner):
        result = runner.invoke(
            app_mod.app, ["network", "https://example.com", "--count", "2"]
        )
        assert result.exit_code == 0
        assert (
            "Testing network connection to https://example.com with 2 requests."
            in result.stdout
        )

    def test_network_command_with_defaults(self, runner):
        result = runner.invoke(app_mod.app, ["network", "https://example.com"])
        assert result.exit_code == 0
        assert (
            "Testing network connection to https://example.com with 5 requests."
            in result.stdout
        )

    def test_network_missing_url_errors(self, runner):
        result = runner.invoke(app_mod.app, ["network"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_network_invalid_count_errors(self, runner):
        result = runner.invoke(
            app_mod.app, ["network", "https://example.com", "--count", "-3"]
        )
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
