import asyncio
from pathlib import Path
import shutil

from src.monitoring.celsius_hourly_reporter import CelsiusHourlyReporter


def test_save_report_file_creates_txt(tmp_path):
    reporter = CelsiusHourlyReporter(report_interval=999999)
    # point data_dir to tmp_path
    reporter.data_dir = tmp_path

    report_text = "Test hourly report content"

    # run the async writer
    asyncio.run(reporter.save_report_file(report_text))

    # look for files in tmp_path / 'reports'
    reports_dir = tmp_path / "reports"
    assert reports_dir.exists()
    files = list(reports_dir.glob("celsius_hourly_report_*.txt"))
    assert len(files) >= 1
    content = files[0].read_text(encoding="utf-8")
    assert "Test hourly report content" in content
