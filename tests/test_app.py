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


def prom_val(value):
    return [{'metric': {}, 'value': [1, str(value)]}]


class TestHelpers:
    def test_get_load_parses_prometheus(self, monkeypatch):
        load_data = [
            {'metric': {'__name__': 'node_load1'}, 'value': [0, '0.10']},
            {'metric': {'__name__': 'node_load5'}, 'value': [0, '0.20']},
            {'metric': {'__name__': 'node_load15'}, 'value': [0, '0.30']},
        ]
        monkeypatch.setattr(app_mod, 'query_prometheus_metrics', _side_effect_sequence([load_data, prom_val(8.0)]))
        averages, cores = app_mod.get_load()
        assert (averages, cores) == ([0.10, 0.20, 0.30], 8.0)

    def test_get_cpu_parses_prometheus(self, monkeypatch):
        cpu_data = [
            {'metric': {'mode': 'user'}, 'value': [0, '0.0']},
            {'metric': {'mode': 'system'}, 'value': [0, '4.8']},
            {'metric': {'mode': 'idle'}, 'value': [0, '95.2']},
        ]
        monkeypatch.setattr(app_mod, 'query_prometheus_metrics', lambda *_, **__: cpu_data)
        user, system, idle = app_mod.get_cpu()
        assert (user, system, idle) == (0.0, 4.8, 95.2)

    def test_get_memory_parses_prometheus(self, monkeypatch):
        total_bytes = 8 * 1024 * 1024 * 1024
        avail_bytes = 4 * 1024 * 1024 * 1024
        monkeypatch.setattr(app_mod, 'query_prometheus_metrics', _side_effect_sequence([prom_val(total_bytes), prom_val(avail_bytes)]))
        total, used, free_mem = app_mod.get_memory()
        assert (total, used, free_mem) == (8192.0, 4096.0, 4096.0)

    def test_get_disk_parses_prometheus(self, monkeypatch):
        responses = [prom_val(10.5), prom_val(5.2), prom_val(0.1), prom_val(0), prom_val(100)]
        monkeypatch.setattr(app_mod, 'query_prometheus_metrics', _side_effect_sequence(responses))
        data = app_mod.get_network_metrics()
        assert (data['receive_rate'], data['transmit_rate'], data['tcp_retrans'], data['drops'], data['tcp_est']) == (
            10.5,
            5.2,
            0.1,
            0,
            100.0,
        )


class TestCLI:
    def test_monitor_unknown_option_errors(self, runner):
        result = runner.invoke(app_mod.app, ['monitor', '--not-a-real-flag'])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_monitor_unexpected_extra_argument_errors(self, runner):
        result = runner.invoke(app_mod.app, ['monitor', 'unexpected'])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2

    def test_monitor_empty_flag(self, runner):
        result = runner.invoke(app_mod.app, ['monitor', ''])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
