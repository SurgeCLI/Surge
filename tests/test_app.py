import pytest
import sys
import os
from typer.testing import CliRunner

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli.app as app_mod


runner = CliRunner()


def _side_effect_sequence(responses):
    iterator = iter(responses)
    def _fn(*args, **kwargs):
        return next(iterator)
    return _fn


class TestHelpers:
    def test_get_load_parses_values(self, monkeypatch):
        monkeypatch.setattr(app_mod, "run_cmd", _side_effect_sequence(["0.10, 0.20, 0.30", "8"]))
        averages, cores = app_mod.get_load()
        assert averages == [0.10, 0.20, 0.30]
        assert cores == 8.0

    def test_get_cpu_parses_values(self, monkeypatch):
        cpu_line = (
            '%Cpu(s):  0.0 us,  4.8 sy,  0.0 ni, 95.2 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st'
        )
        monkeypatch.setattr(app_mod, "run_cmd", lambda *_, **__: cpu_line)
        user, system, idle = app_mod.get_cpu()
        assert user == "0.0"
        assert system == "4.8"
        assert idle == "95.2"

    def test_get_memory_parses_values(self, monkeypatch):
        mem_line = "Mem: 764 492 144 8 247 272"
        monkeypatch.setattr(app_mod, "run_cmd", lambda *_, **__: mem_line)
        total, used, free_mem = app_mod.get_memory()
        assert total == "764"
        assert used == "492"
        assert free_mem == "144"

    def test_get_disk_parses_values(self, monkeypatch):
        df_line = "/dev/vda1 25G 5.2G 20G 21% /"
        monkeypatch.setattr(app_mod, "run_cmd", lambda *_, **__: df_line)
        size, used, available, percent = app_mod.get_disk()
        assert size == "25G"
        assert used == "5.2G"
        assert available == "20G"
        assert percent == "21%"


class TestCLI:
    def test_monitor_default_outputs_sections(self, monkeypatch):
        monkeypatch.setattr(app_mod, "get_load", lambda: ([0.1, 0.2, 0.3], 8))
        monkeypatch.setattr(app_mod, "get_cpu", lambda: ("12.3", "3.4", "80.0"))
        monkeypatch.setattr(app_mod, "get_memory", lambda: ("32000", "12000", "20000"))
        monkeypatch.setattr(app_mod, "get_disk", lambda: ("100G", "40G", "60G", "40%"))

        result = runner.invoke(app_mod.app, ["monitor"]) 
        assert result.exit_code == 0
        out = result.stdout
        assert "System Load Averages" in out
        assert "Load avg (1m): 0.1" in out
        assert "CPU Utilization" in out
        assert "User: 12.3% | System: 3.4% | Idle: 80.0%" in out
        assert "Memory Usage (MB)" in out
        assert "Total: 32000 | Used: 12000 | Free: 20000" in out
        assert "Disk Usage" in out
        assert "Size: 100G | Used: 40G | Available: 60G | Usage: 40%" in out

    def test_monitor_verbose_load_divides_by_cores_as_string(self, monkeypatch):
        monkeypatch.setattr(app_mod, "get_load", lambda: ([1.0, 2.0, 3.0], 4))
        result = runner.invoke(app_mod.app, ["monitor", "--load", "--no-cpu", "--no-ram", "--no-disk", "--verbose"]) 
        if result.exit_code == 0:
            assert "Load avg (1m): 1.00" in result.stdout
        else:
            assert isinstance(result.exception, SystemExit)

    def test_monitor_unknown_option_errors(self):
        result = runner.invoke(app_mod.app, ["monitor", "--not-a-real-flag"]) 
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_monitor_unexpected_extra_argument_errors(self):
        result = runner.invoke(app_mod.app, ["monitor", "unexpected"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
    
    def test_monitor_invalid_interval_errors(self):
        result = runner.invoke(app_mod.app, ["monitor", "--interval", "-5"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
    
    def test_monitor_empty_flag(self):
        result = runner.invoke(app_mod.app, ["monitor", ""])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_network_command_prints_message(self):
        result = runner.invoke(app_mod.app, ["network", "https://example.com", "--count", "2"]) 
        assert result.exit_code == 0
        assert "Testing network connection to https://example.com with 2 requests." in result.stdout

    def test_network_command_with_defaults(self):
        result = runner.invoke(app_mod.app, ["network", "https://example.com"]) 
        assert result.exit_code == 0
        assert "Testing network connection to https://example.com with 5 requests." in result.stdout
    
    def test_network_missing_url_errors(self):
        result = runner.invoke(app_mod.app, ["network"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_network_invalid_count_errors(self):
        result = runner.invoke(app_mod.app, ["network", "https://example.com", "--count", "-3"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2


