"""Qt process manager. No shell is used for php/artisan; validated tools run via QProcess."""
from __future__ import annotations
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from collections import deque
from typing import Callable
from PySide6.QtCore import QObject, QProcess, Signal


@dataclass
class Job:
    label: str
    tool: str
    args: list[str]
    cwd: str
    success: Callable[[str], None] | None = None
    failure: Callable[[str], None] | None = None
    sensitive: bool = False
    cancelled: Callable[[], None] | None = None


class TaskRunner(QObject):
    output = Signal(str)
    console_entry_created = Signal(str, str)
    console_output = Signal(str, str)
    busy_changed = Signal(bool)
    running_changed = Signal(str, bool)
    job_started = Signal(str)
    job_succeeded = Signal(str)
    job_failed = Signal(str, str)
    job_state_changed = Signal(object, str)
    def __init__(self, tools: dict, parent=None):
        super().__init__(parent)
        self.tools = tools
        self.queue = deque()
        self.active: QProcess | None = None
        self.active_job: Job | None = None
        self._cancelled_job: Job | None = None
        self.buffer = ''
        self.services: dict[str, QProcess] = {}
        self._next_console_id = 1
        self._job_console_keys: dict[int, str] = {}
        self._console_jobs: dict[str, Job] = {}

    def resolve(self, name: str) -> str:
        entry = str(self.tools.get(name, name)).strip()
        if not entry:
            raise ValueError(f'Please configure a path for {name} in Settings')
        if entry.startswith('"') and entry.endswith('"'):
            entry = entry[1:-1]
        if Path(entry).is_file():
            return str(Path(entry))
        found = shutil.which(entry)
        if found:
            return found
        raise FileNotFoundError(f'{name} not found: {entry}. Configure it in Settings, or add it to PATH.')

    def _command(self, name: str, args: list[str]) -> tuple[str, list[str]]:
        executable = self.resolve(name)
        # composer installed as a PHP Archive on Windows or macOS
        if executable.lower().endswith('.phar'):
            return self.resolve('php'), [executable, *args]
        # Windows .bat/.cmd launch with an explicit cmd wrapper. Quote every argument so
        # Composer constraints such as ^12.0 remain literal instead of being parsed by cmd.
        if os.name == 'nt' and executable.lower().endswith(('.cmd', '.bat')):
            values = [executable, *args]
            # These characters cannot be safely represented in a cmd.exe /c command
            # string. Other metacharacters are protected by quoting each argument.
            if any(any(c in value for c in '%!"\r\n\x00') for value in values):
                raise ValueError('Windows batch-wrapper arguments contain unsupported cmd.exe characters.')
            command = ' '.join(f'"{value}"' for value in values)
            return 'cmd.exe', ['/d', '/s', '/c', f'"{command}"']
        return executable, args

    @staticmethod
    def _start_process(process: QProcess, executable: str, args: list[str]):
        # Preserve cmd.exe's /c payload verbatim. Normal Qt argv quoting escapes
        # the nested quotes for the Windows CRT, which cmd.exe does not understand.
        if os.name == 'nt' and executable.lower().endswith('cmd.exe') and len(args) == 4 and args[:3] == ['/d', '/s', '/c']:
            process.setProgram(executable)
            process.setArguments(args[:3])
            process.setNativeArguments(' ' + args[3])
            process.start()
        else:
            process.start(executable, args)

    def enqueue(self, job: Job):
        self.queue.append(job)
        key = f'job:{self._next_console_id}'
        self._next_console_id += 1
        self._job_console_keys[id(job)] = key
        self._console_jobs[key] = job
        self.console_entry_created.emit(key, job.label)
        self.job_state_changed.emit(job, 'queued')
        if self.active is None:
            self._next()

    def cancel_job(self, job: Job):
        """Cancel one queued or active job without affecting other work."""
        queued_index = next((index for index, queued in enumerate(self.queue) if queued is job), None)
        if queued_index is not None:
            del self.queue[queued_index]
            self._job_output(job, f'\n■ Canceled: {job.label}\n')
            if job.cancelled:
                job.cancelled()
            self.job_state_changed.emit(job, 'cancelled')
            return
        if self.active_job is job and self.active and self.active.state() != QProcess.ProcessState.NotRunning:
            self._cancelled_job = job
            self._terminate_tree(self.active)

    def console_entry_state(self, key: str) -> str:
        job = self._console_jobs.get(key)
        if job is not None:
            if self.active_job is job and self.active and self.active.state() != QProcess.ProcessState.NotRunning:
                return 'running'
            if any(queued is job for queued in self.queue):
                return 'queued'
            return 'finished'
        if key.startswith('service:'):
            process = self.services.get(key[len('service:'):])
            if process and process.state() != QProcess.ProcessState.NotRunning:
                return 'running'
        return 'finished'

    def stop_console_entry(self, key: str):
        job = self._console_jobs.get(key)
        if job is not None:
            self.cancel_job(job)
        elif key.startswith('service:'):
            self.service_stop(key[len('service:'):])

    def _next(self):
        if self.active is not None:
            return
        if not self.queue:
            self.active = None
            self.active_job = None
            self.busy_changed.emit(False)
            return
        job = self.queue.popleft()
        self.active_job = job
        self._cancelled_job = None
        try:
            exe, args = self._command(job.tool, job.args)
            if not Path(job.cwd).is_dir():
                raise FileNotFoundError('Working directory does not exist')
        except (ValueError, FileNotFoundError) as err:
            self._job_output(job, f'✖ {job.label}: {err}\n')
            self.job_failed.emit(job.label, str(err))
            self.job_state_changed.emit(job, 'failed')
            if job.failure:
                job.failure(str(err))
            self._next()
            return
        self.busy_changed.emit(True)
        self.buffer = ''
        self._job_output(job, f'\n▶ {job.label}  ·  {job.cwd}\n')
        self.job_started.emit(job.label)
        self.job_state_changed.emit(job, 'running')
        process = QProcess(self)
        process.setWorkingDirectory(job.cwd)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(lambda p=process: self._collect(p))
        process.finished.connect(lambda code, status, p=process: self._finished(p, code))
        process.errorOccurred.connect(lambda error, p=process: self._on_job_error(p, error))
        self.active = process
        self._start_process(process, exe, args)

    def _collect(self, process: QProcess):
        data = bytes(process.readAllStandardOutput()).decode('utf-8', errors='replace')
        self.buffer = (self.buffer + data)[-2_000_000:]
        if self.active_job:
            if self.active_job.sensitive:
                self._job_output(self.active_job, '[Sensitive command output hidden]\n')
            else:
                self._job_output(self.active_job, data)

    def _job_console_key(self, job: Job) -> str:
        return self._job_console_keys.get(id(job), f'job:{self._next_console_id}')

    def _job_output(self, job: Job, text: str):
        self.output.emit(text)
        self.console_output.emit(self._job_console_key(job), text)

    def _service_output_message(self, key: str, text: str):
        self.output.emit(text)
        self.console_output.emit(f'service:{key}', text)

    def _on_job_error(self, process: QProcess, error):
        if error == QProcess.ProcessError.FailedToStart and self.active is process:
            job = self.active_job
            error = process.errorString()
            self._job_output(job, f'✖ Could not start {job.label}: {error}\n')
            self.active = None
            self.active_job = None
            cancelled = self._cancelled_job is job
            self._cancelled_job = None
            process.deleteLater()
            if cancelled:
                self._job_output(job, f'■ Canceled: {job.label}\n')
                if job.cancelled:
                    job.cancelled()
                self.job_state_changed.emit(job, 'cancelled')
            else:
                self.job_failed.emit(job.label, error)
                self.job_state_changed.emit(job, 'failed')
                if job.failure:
                    job.failure(error)
            self._next()

    def _finished(self, process: QProcess, code: int):
        if self.active is not process:
            return
        job = self.active_job
        self._collect(process)
        text = self.buffer
        cancelled = self._cancelled_job is job
        self._cancelled_job = None
        self._job_output(job, f'\n{ "■ Canceled" if cancelled else "✔ Completed" if code == 0 else "✖ Failed" }: {job.label} (exit {code})\n')
        self.active = None
        self.active_job = None
        process.deleteLater()
        if cancelled:
            if job.cancelled:
                job.cancelled()
            self.job_state_changed.emit(job, 'cancelled')
        elif code == 0:
            self.job_succeeded.emit(job.label)
            if job.success:
                job.success(text)
            self.job_state_changed.emit(job, 'succeeded')
        else:
            self.job_failed.emit(job.label, '' if job.sensitive else text)
            if job.failure:
                job.failure(text)
            self.job_state_changed.emit(job, 'failed')
        self._next()

    def cancel(self):
        for job in tuple(self.queue):
            self.cancel_job(job)
        if self.active_job:
            self.cancel_job(self.active_job)
        else:
            message = '\n■ Pending tasks canceled\n'
            self.output.emit(message)
            self.console_output.emit('activity', message)

    def service_start(self, key: str, name: str, args: list[str], cwd: str):
        old = self.services.get(key)
        if old and old.state() != QProcess.ProcessState.NotRunning:
            raise ValueError(f'{key} is already running')
        exe, argv = self._command(name, args)
        if not Path(cwd).is_dir():
            raise ValueError('Project directory does not exist')
        proc = QProcess(self)
        proc.setWorkingDirectory(cwd)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda p=proc, k=key: self._service_output(p, k))
        proc.finished.connect(lambda code, status, p=proc, k=key: self._service_finished(p, k, code))
        proc.errorOccurred.connect(lambda error, p=proc, k=key: self._on_service_error(p, k, error))
        self.services[key] = proc
        self.console_entry_created.emit(f'service:{key}', key.split('|', 1)[0].replace('_', ' ').title())
        self._start_process(proc, exe, argv)
        self.running_changed.emit(key, True)
        self._service_output_message(key, f'\n▶ Starting {key}: {name} {" ".join(args)}\n')

    def _on_service_error(self, proc: QProcess, key: str, error):
        if error == QProcess.ProcessError.FailedToStart and self.services.get(key) is proc:
            self._service_output_message(key, f'✖ {key}: {proc.errorString()}\n')
            del self.services[key]
            self.running_changed.emit(key, False)
            proc.deleteLater()

    def _service_output(self, proc: QProcess, key: str):
        data = bytes(proc.readAllStandardOutput()).decode('utf-8', errors='replace')
        if data:
            self._service_output_message(key, data)

    def _service_finished(self, proc: QProcess, key: str, code: int):
        self._service_output(proc, key)
        self._service_output_message(key, f'\n■ {key} stopped (exit {code})\n')
        self.running_changed.emit(key, False)
        if self.services.get(key) is proc:
            del self.services[key]
        proc.deleteLater()

    def _terminate_tree(self, proc: QProcess):
        if proc.state() == QProcess.ProcessState.NotRunning:
            return
        if os.name == 'nt' and proc.processId():
            try:
                subprocess.run(['taskkill', '/PID', str(proc.processId()), '/T', '/F'],
                               timeout=6, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except (OSError, subprocess.TimeoutExpired):
                proc.kill()
        else:
            proc.kill()

    def service_stop(self, key: str):
        proc = self.services.get(key)
        if proc:
            self._terminate_tree(proc)

    def stop_all(self):
        self.cancel()
        for p in list(self.services.values()):
            self._terminate_tree(p)
