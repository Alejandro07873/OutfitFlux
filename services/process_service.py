"""Cancelable external commands with disk-backed output (no pipe deadlocks)."""
import subprocess
import tempfile
import time
from pathlib import Path


class ExportCancelled(Exception):
    pass


def raise_if_cancelled(callback=None):
    if callback and callback():
        raise ExportCancelled("Operación cancelada.")


def run_hidden_command(command, is_cancelled_callback=None, timeout=600, output_limit=16 * 1024 * 1024):
    raise_if_cancelled(is_cancelled_callback)
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen([str(x) for x in command], stdout=out, stderr=err,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        start = time.monotonic()
        try:
            while process.poll() is None:
                raise_if_cancelled(is_cancelled_callback)
                if time.monotonic() - start > timeout:
                    raise TimeoutError(f"Tiempo agotado: {Path(command[0]).name} ({timeout}s)")
                time.sleep(0.05)
            raise_if_cancelled(is_cancelled_callback)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        result = {}
        for key, stream in [("stdout", out), ("stderr", err)]:
            size = stream.seek(0, 2)
            if size > output_limit:
                raise RuntimeError(f"Salida de {Path(command[0]).name} supera el límite de diagnóstico.")
            stream.seek(0)
            result[key] = stream.read().decode("utf-8", errors="replace")
        if process.returncode:
            raise RuntimeError(f"{Path(command[0]).name} terminó con código {process.returncode}\n"
                               + result['stderr'][-8000:] + result['stdout'][-8000:])
        return result
