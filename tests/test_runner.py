import os
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QProcess

from runner import Job, TaskRunner


@pytest.fixture(scope='module')
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def wait_until(predicate, timeout_ms=5000):
    deadline = time.monotonic() + timeout_ms / 1000
    while not predicate() and time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    QCoreApplication.processEvents()
    return predicate()


def test_service_rejects_duplicate_and_stops_process(qt_app, tmp_path):
    runner = TaskRunner({'python': sys.executable})
    key = 'test-service'
    process = None
    try:
        runner.service_start(key, 'python', ['-c', 'import time; time.sleep(60)'], str(tmp_path))
        process = runner.services[key]
        assert wait_until(lambda: key not in runner.services or process.state() == QProcess.ProcessState.Running)
        assert key in runner.services
        assert process.state() == QProcess.ProcessState.Running

        with pytest.raises(ValueError, match='already running'):
            runner.service_start(key, 'python', ['-c', 'pass'], str(tmp_path))

        runner.service_stop(key)
        assert wait_until(lambda: key not in runner.services, 7000), 'Service did not stop before timeout'
        assert key not in runner.services
    finally:
        if key in runner.services:
            runner.stop_all()
            wait_until(lambda: key not in runner.services, 7000)


def test_two_laravel_fixtures_keep_service_working_directories_independent(qt_app, tmp_path):
    runner = TaskRunner({'python': sys.executable})
    projects = {
        'project-a': tmp_path / 'Laravel ü A',
        'project-b': tmp_path / 'Laravel B',
    }
    for project in projects.values():
        project.mkdir()
        (project / 'artisan').write_text('<?php // fixture\n', encoding='utf-8')
        (project / 'composer.json').write_text(
            '{"require":{"laravel/framework":"^12.0"}}', encoding='utf-8'
        )

    script = (
        'import pathlib,time; '
        'pathlib.Path("service.cwd").write_text(str(pathlib.Path.cwd()), encoding="utf-8"); '
        'time.sleep(60)'
    )
    keys = {name: f'{name}-server' for name in projects}
    try:
        for name, project in projects.items():
            runner.service_start(keys[name], 'python', ['-c', script], str(project))

        assert wait_until(lambda: all((p / 'service.cwd').exists() for p in projects.values()))
        for project in projects.values():
            assert Path((project / 'service.cwd').read_text(encoding='utf-8')) == project.resolve()

        runner.service_stop(keys['project-a'])
        assert wait_until(lambda: keys['project-a'] not in runner.services)
        assert keys['project-b'] in runner.services
        assert runner.services[keys['project-b']].state() == QProcess.ProcessState.Running

        job_results = []
        write_cwd = 'import pathlib; pathlib.Path("job.cwd").write_text(str(pathlib.Path.cwd()), encoding="utf-8")'
        for name, project in projects.items():
            runner.enqueue(Job(
                f'artisan fixture {name}', 'python',
                ['-c', write_cwd], str(project),
                success=lambda output, key=name: job_results.append(key),
            ))
        assert wait_until(lambda: len(job_results) == 2)
        for name, project in projects.items():
            assert name in job_results
            assert Path((project / 'job.cwd').read_text(encoding='utf-8')) == project.resolve()
    finally:
        runner.stop_all()
        assert wait_until(lambda: not runner.services, 7000)


@pytest.mark.skipif(os.name != 'nt', reason='Windows batch wrapper behavior')
def test_batch_wrapper_preserves_composer_constraints_and_metacharacters(qt_app, tmp_path):
    wrapper = tmp_path / 'argument probe.cmd'
    wrapper.write_text('@echo off\r\necho [%*]\r\n', encoding='ascii')
    runner = TaskRunner({'probe': str(wrapper)})
    results = []
    runner.enqueue(Job(
        'batch argument probe', 'probe', ['^12.0', 'a&b'], str(tmp_path),
        success=results.append,
    ))
    assert wait_until(lambda: bool(results))
    assert '"^12.0"' in results[0]
    assert '"a&b"' in results[0]
