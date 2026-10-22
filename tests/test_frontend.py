"""Run the chart calculations with Node's built-in test runner when available."""
import shutil
import subprocess

import pytest

from sulteng.config import ROOT


def test_fire_chart_calculations():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node is not installed')
    subprocess.run([node, '--test', 'tests/fire-data.test.cjs'], cwd=ROOT, check=True, capture_output=True, text=True)
