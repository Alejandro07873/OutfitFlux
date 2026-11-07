"""Window-owned export jobs with per-costume stage progress."""
import json
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets as W
from workers.task_worker import TaskWorker
from ui.outfit_translations import tr_text


class ExportQueue(W.QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.jobs, self.worker, self.closing = window, [], None, False
        layout = W.QVBoxLayout(self)
        layout.setSpacing(14)
        self.title = W.QLabel()
        self.title.setObjectName('ShelfTitle')
        layout.addWidget(self.title)
        self.subtitle = W.QLabel()
        self.subtitle.setObjectName('Muted')
        layout.addWidget(self.subtitle)
        self.empty = W.QFrame()
        self.empty.setObjectName('WelcomeHero')
        empty_layout = W.QVBoxLayout(self.empty)
        empty_layout.setContentsMargins(32, 32, 32, 32)
        empty_layout.addStretch()
        self.empty_title = W.QLabel()
        self.empty_title.setObjectName('ShelfTitle')
        empty_layout.addWidget(self.empty_title)
        self.empty_help = W.QLabel()
        self.empty_help.setWordWrap(True)
        empty_layout.addWidget(self.empty_help)
        self.import_button = W.QPushButton()
        self.import_button.setObjectName('Primary')
        self.import_button.clicked.connect(window.pick_mod)
        empty_layout.addWidget(self.import_button, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        empty_layout.addStretch()
        layout.addWidget(self.empty, 1)
        self.scroll = W.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(W.QFrame.Shape.NoFrame)
        body = W.QWidget()
        self.rows = W.QVBoxLayout(body)
        self.rows.setSpacing(16)
        self.rows.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(body)
        layout.addWidget(self.scroll, 1)
        self.total = W.QProgressBar()
        layout.addWidget(self.total)
        self.notice = W.QLabel()
        self.notice.setWordWrap(True)
        self.notice.setObjectName('Muted')
        layout.addWidget(self.notice)
        self.refresh()

    def text(self, es, en):
        return en if self.window.preferences.get('language') == 'en' else es

    def add(self, name, image, function, targets):
        card = W.QFrame()
        card.setObjectName('StepCard')
        box = W.QVBoxLayout(card)
        box.setContentsMargins(20, 16, 20, 16)
        box.setSpacing(12)
        row = W.QHBoxLayout()
        art = W.QLabel()
        art.setFixedSize(46, 56)
        art.setPixmap(QtGui.QPixmap(image).scaled(46, 56, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        row.addWidget(art)
        title = W.QLabel(name)
        title.setWordWrap(True)
        title.setObjectName('SelectionName')
        row.addWidget(title, 1)
        cancel = W.QPushButton()
        row.addWidget(cancel)
        box.addLayout(row)
        state = W.QLabel()
        state.setWordWrap(True)
        state.setObjectName('Muted')
        box.addWidget(state)
        bar = W.QProgressBar()
        box.addWidget(bar)
        target_rows = []
        for target in targets:
            record = dict(target) if isinstance(target, dict) else {'name': str(target)}
            target_row = W.QHBoxLayout()
            preview = W.QLabel()
            preview.setFixedSize(54, 66)
            preview.setPixmap(QtGui.QPixmap(record.get('image', '')).scaled(54, 66, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
            target_row.addWidget(preview)
            detail = W.QVBoxLayout()
            costume = W.QLabel(record.get('name', ''))
            costume.setObjectName('SelectionName')
            costume.setWordWrap(True)
            detail.addWidget(costume)
            info = W.QLabel()
            info.setObjectName('Muted')
            detail.addWidget(info)
            target_row.addLayout(detail, 1)
            progress = W.QProgressBar()
            progress.setFixedWidth(150)
            progress.setRange(0, 5)
            progress.setValue(0)
            progress.setTextVisible(False)
            target_row.addWidget(progress)
            box.addLayout(target_row)
            target_rows.append(dict(record=record, label=info, bar=progress, step=0, state='waiting'))
        job = dict(name=name, function=function, bar=bar, state=state, cancel=cancel,
                   status='waiting', result=None, error=None, targets=target_rows)
        cancel.clicked.connect(lambda: self.cancel(job))
        self.jobs.append(job)
        self.rows.addWidget(card)
        self.refresh()
        self.start_next()

    def cancel(self, job):
        if job['status'] == 'running' and self.worker:
            self.worker.cancel()
        elif job['status'] == 'waiting':
            job['status'] = 'cancelled'
            for target in job['targets']:
                target['state'] = 'cancelled'
            job['cancel'].setEnabled(False)
        self.refresh()

    def start_next(self):
        if self.worker or self.closing:
            return
        job = next((j for j in self.jobs if j['status'] == 'waiting'), None)
        if not job:
            return
        job['status'] = 'running'
        worker = TaskWorker(job['function'], self)
        self.worker = worker
        worker.progress.connect(lambda current, total, text: self.progress(job, current, total, text))
        worker.result.connect(lambda result: job.update(result=result))
        worker.error.connect(lambda error: job.update(error=error))
        worker.cancelled.connect(lambda: job.update(status='cancelled'))
        worker.finished.connect(lambda: self.finished(job, worker))
        worker.start()
        self.refresh()

    def progress(self, job, current, total, text):
        if text.startswith('outfitflux-target:'):
            event = json.loads(text.partition(':')[2])
            index = event['index']
            if 0 <= index < len(job['targets']):
                target = job['targets'][index]
                target.update(step=max(0, min(5, event['step'])), state=event['state'])
        else:
            job['progress_text'] = text
        self.refresh()

    def finished(self, job, worker):
        self.worker = None
        worker.deleteLater()
        result = job['result'] or {}
        completed, failed = result.get('completed', []), result.get('failed', [])
        cancelled = job['status'] == 'cancelled' or result.get('cancelled', False)
        job['status'] = 'cancelled' if cancelled else ('failed' if job['error'] or failed else 'done')
        outcomes = {row.get('target'): row for row in completed + failed}
        for target in job['targets']:
            outcome = outcomes.get(target['record'].get('skin_path'))
            if outcome:
                target['state'] = 'done' if outcome in completed else 'failed'
                target['step'] = 5 if outcome in completed else target['step']
                target['label'].setToolTip(outcome.get('output') or outcome.get('error', ''))
            elif target['state'] != 'done':
                target['state'] = 'cancelled' if cancelled else ('done' if job['status'] == 'done' else 'failed')
                if target['state'] == 'done':
                    target['step'] = 5
        job['cancel'].setEnabled(False)
        outputs = [row.get('output', '') for row in completed]
        if outputs and outputs[0]:
            job['cancel'].clicked.disconnect()
            job['cancel'].clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(Path(outputs[0]).parent))))
            job['cancel'].setEnabled(True)
            job['state'].setToolTip('\n'.join(outputs))
        self.refresh()
        self.notice.setText(job['name'] + '\n' + job['state'].text())
        self.window.statusBar().showMessage(job['name'] + ' · ' + job['state'].text(), 12000)
        W.QApplication.beep()
        if self.closing:
            self.window.close()
        else:
            QtCore.QTimer.singleShot(0, self.start_next)

    def refresh(self):
        en = self.window.preferences.get('language') == 'en'
        states = {
            'waiting': self.text('En espera', 'Waiting'),
            'preparing': self.text('Preparando archivos', 'Preparing files'),
            'reading': self.text('Leyendo malla', 'Reading mesh'),
            'converting': self.text('Convirtiendo malla', 'Converting mesh'),
            'rebuilding': self.text('Reconstruyendo asset', 'Rebuilding asset'),
            'packing': self.text('Empaquetando y verificando', 'Packing and verifying'),
            'done': self.text('Terminado', 'Complete'),
            'failed': self.text('Falló', 'Failed'),
            'cancelled': self.text('Cancelado', 'Cancelled'),
        }
        all_targets = [t for job in self.jobs for t in job['targets']]
        ended = sum(t['state'] in ('done', 'failed', 'cancelled') for t in all_targets)
        self.title.setText(self.text('Cola de intercambios', 'Swap queue') + f' · {ended}/{len(all_targets)}')
        self.subtitle.setText(self.text('Cada traje, paso a paso. Puedes preparar otro mod mientras esperas.', 'Every costume, step by step. Prepare another mod while these run.'))
        self.empty_title.setText(self.text('Tu próximo intercambio empieza aquí', 'Your next swap starts here'))
        self.empty_help.setText(self.text('Importa un mod y elige sus destinos. Aquí verás cada traje con su imagen y avance.', 'Import a mod and choose destinations. Each costume will appear here with its preview and progress.'))
        self.import_button.setText(self.text('+ Importar mod', '+ Import mod'))
        self.empty.setVisible(not self.jobs)
        self.scroll.setVisible(bool(self.jobs))
        self.total.setVisible(bool(self.jobs))
        self.total.setRange(0, max(1, len(all_targets) * 5))
        self.total.setFormat(self.text('Etapas procesadas · %p%', 'Stages processed · %p%'))
        self.total.setValue(sum(5 if t['state'] in ('done','failed','cancelled') else t['step'] for t in all_targets))
        for job in self.jobs:
            targets = job['targets']
            finished = sum(t['state'] in ('done', 'failed', 'cancelled') for t in targets)
            job['bar'].setRange(0, max(1, len(targets) * 5))
            job['bar'].setFormat(self.text('Etapas procesadas · %p%', 'Stages processed · %p%'))
            job['bar'].setValue(sum(5 if t['state'] in ('done','failed','cancelled') else t['step'] for t in targets))
            for target in targets:
                status = states.get(target['state'], target['state'])
                if target['state'] not in ('waiting','done','failed','cancelled'):
                    status += self.text(f" · {5-target['step']} etapas restantes", f" · {5-target['step']} stages remaining")
                target['label'].setText(status)
                target['bar'].setValue(target['step'])
            if job['status'] in ('waiting', 'running'):
                summary = states['waiting'] if job['status'] == 'waiting' else tr_text(job.get('progress_text', 'Preparando…'), en)
                active = next((target for target in targets if target['state'] not in ('waiting','done','failed','cancelled')), None)
                if active:
                    summary = states[active['state']] + ' · ' + active['record'].get('name', '')
                summary += f' · {finished}/{len(targets)}'
            else:
                result = job.get('result') or {}
                count, errors = len(result.get('completed', [])), len(result.get('failed', []))
                summary = self.text(f'{count} terminados · {errors} fallidos', f'{count} completed · {errors} failed')
                if job['status'] == 'cancelled':
                    summary = states['cancelled'] + ' · ' + summary
                error = job.get('error') or (result.get('failed') or [{}])[0].get('error', '')
                if error:
                    summary += ' · ' + tr_text(error, en)
            job['state'].setText(summary)
            has_outputs = bool((job.get('result') or {}).get('completed'))
            job['cancel'].setText(self.text('Abrir carpeta', 'Open folder') if has_outputs else self.text('Cancelar', 'Cancel'))
        if not self.jobs:
            self.notice.clear()
