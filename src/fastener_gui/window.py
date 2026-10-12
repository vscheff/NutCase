"""Import, source-bound configuration, asynchronous generation and release review."""
import copy
import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QSplitter, QTabWidget, QScrollArea, QGroupBox, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QFileDialog, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QAbstractItemView)

from fastener_drawing.configuration import bind_config, read_config
from fastener_drawing.layout import SHEETS
from .controller import BackendController
from .outputs import export_copy, history_entries
from .preview import PdfPreview
from .file_opener import FileOpener
from .state import ROOT, ConfigStore, ModelState, atomic_json, read_json, completion_status


class MainWindow(QMainWindow):
    def __init__(self, freecad_python='', poppler='', output=None, settings_directory=None, controller=None):
        super().__init__()
        self.setWindowTitle('Fastener Drawing Generator')
        self.resize(1420, 940); self.setMinimumSize(940, 680)
        self.model = ModelState()
        self.store = ConfigStore(settings_directory or ROOT/'output'/'gui-state')
        self.settings_file = self.store.directory/'settings.json'
        try: settings = read_json(self.settings_file) if self.settings_file.exists() else {}
        except (OSError, ValueError): settings = {}
        self.settings = settings
        self.release = None; self.action = None; self._loading = False; self._closing = False
        self.backend = controller or BackendController(self)
        self.backend.stage.connect(self._stage)
        self.backend.log.connect(self._log)
        self.backend.busyChanged.connect(self._busy_changed)
        self.backend.completed.connect(self._completed)
        self.file_opener=FileOpener(self)
        self.file_opener.failed.connect(self._error)
        self.file_opener.accepted.connect(lambda message:self.status.setText(message))
        self._build(freecad_python or settings.get('freecad_python',''), poppler or settings.get('poppler',''),
                    str(output or settings.get('output',ROOT/'output'/'gui')))
        self._apply_config()
        if settings.get('source'): self.set_source(settings['source'])
        self._busy_changed(False)

    def _button(self, text, slot):
        button = QPushButton(text); button.clicked.connect(slot); return button

    def _build(self, freecad_python, poppler, output):
        central = QWidget(); root = QVBoxLayout(central); root.setContentsMargins(14,12,14,12)
        heading = QLabel('Fastener Drawing Generator'); heading.setObjectName('Heading')
        root.addWidget(heading)
        notice = QLabel('Preliminary Drawings - CAD Verification Does Not Constitute Engineering Approval')
        notice.setObjectName('Notice'); notice.setWordWrap(True); root.addWidget(notice)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget(); left.setMinimumWidth(380)
        left_layout = QVBoxLayout(left); left_layout.setContentsMargins(0,0,8,0)
        self.import_group = QGroupBox('1. Import STEP Model'); form = QVBoxLayout(self.import_group)
        self.source_edit = QLineEdit(); self.source_edit.setPlaceholderText('Choose Any .stp Or .step File')
        self.source_edit.editingFinished.connect(lambda:self.set_source(self.source_edit.text()))
        browse_row = QHBoxLayout(); browse_row.addWidget(self.source_edit,1)
        browse_row.addWidget(self._button('Browse…', self.browse_source)); form.addLayout(browse_row)
        self.recent = QComboBox(); self.recent.addItem('Recent STEP Files')
        self.recent.addItems(self.settings.get('recent',[])); self.recent.activated.connect(self._recent_source)
        form.addWidget(self.recent)
        self.analyze_button = self._button('Analyze Geometry', self.analyze); form.addWidget(self.analyze_button)
        self.summary = QLabel('No Model Analyzed'); self.summary.setWordWrap(True); form.addWidget(self.summary)
        left_layout.addWidget(self.import_group)
        self.config_tabs = QTabWidget(); left_layout.addWidget(self.config_tabs,1)
        self.config_tabs.addTab(self._configuration(), '2. Configure')
        self.table = QTableWidget(0,5); self.table.setHorizontalHeaderLabels(
            ['Draw','Characteristic','Value','Units','Source Status'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True); self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1,200)
        self.table.itemChanged.connect(self._selection_changed)
        self.table.itemSelectionChanged.connect(self._candidate_details)
        candidate_panel = QWidget(); candidate_layout = QVBoxLayout(candidate_panel)
        hint = QLabel('Custom Mode Uses Explicit Selections. Values Are Read-Only. Source Verification Still Applies.')
        hint.setWordWrap(True); candidate_layout.addWidget(hint); candidate_layout.addWidget(self.table,1)
        self.candidate_detail=QPlainTextEdit();self.candidate_detail.setReadOnly(True);self.candidate_detail.setMaximumHeight(125)
        self.candidate_detail.setPlaceholderText('Select A Characteristic To Read Its Evidence Or Unresolved Reason')
        candidate_layout.addWidget(self.candidate_detail)
        self.config_tabs.addTab(candidate_panel, 'Dimensions')
        config_buttons = QHBoxLayout()
        self.save_button = self._button('Save Configuration', self.save_configuration)
        self.load_button = self._button('Load JSON…', self.load_configuration)
        config_buttons.addWidget(self.save_button); config_buttons.addWidget(self.load_button)
        left_layout.addLayout(config_buttons)
        self.fresh_button = self._button('Start New Configuration', self.fresh_configuration)
        left_layout.addWidget(self.fresh_button)
        self.generate_button = self._button('3. Generate Drawing', self.generate)
        self.generate_button.setObjectName('Primary'); left_layout.addWidget(self.generate_button)
        self.splitter.addWidget(left)
        right = QWidget(); right_layout = QVBoxLayout(right); right_layout.setContentsMargins(8,0,0,0)
        self.result_tabs = QTabWidget(); right_layout.addWidget(self.result_tabs,1)
        self.preview = PdfPreview(); self.preview.failed.connect(self._preview_failed)
        self.result_tabs.addTab(self.preview,'4. Drawing Preview')
        self.review_text = QPlainTextEdit(); self.review_text.setReadOnly(True)
        self.review_text.setPlaceholderText('Geometry Warnings, Unresolved Characteristics And CAD Verification Appear Here')
        self.result_tabs.addTab(self.review_text,'Engineering Review')
        self.release_label = QLabel('No Verified Release Selected'); self.release_label.setWordWrap(True)
        right_layout.addWidget(self.release_label)
        actions = QHBoxLayout()
        self.pdf_button = self._button('Open PDF',lambda:self.open_artifact('pdf'))
        self.project_button = self._button('Open In FreeCAD',self.open_project)
        self.export_pdf_button = self._button('Save PDF As…',lambda:self.export_artifact('pdf'))
        self.export_project_button = self._button('Save Project As…',lambda:self.export_artifact('project'))
        self.output_buttons = [self.pdf_button,self.project_button,self.export_pdf_button,self.export_project_button]
        for button in self.output_buttons: actions.addWidget(button)
        right_layout.addLayout(actions)
        history = QHBoxLayout()
        self.history = QComboBox(); self.history.addItem('Select A Previous Release')
        history.addWidget(self.history,1)
        self.history_button = self._button('Open Previous Release',self.open_history)
        history.addWidget(self.history_button)
        self.current_button = self._button('Open Current Release',self.open_current)
        history.addWidget(self.current_button); right_layout.addLayout(history)
        self.splitter.addWidget(right); self.splitter.setSizes([480,900]); root.addWidget(self.splitter,1)
        status_row = QHBoxLayout()
        self.status = QLabel('Ready'); self.status.setWordWrap(True); status_row.addWidget(self.status,1)
        self.cancel_button = self._button('Cancel Processing', self.backend.cancel); status_row.addWidget(self.cancel_button)
        self.log_toggle = self._button('Show Logs', self._toggle_logs); status_row.addWidget(self.log_toggle)
        root.addLayout(status_row)
        self.progress = QProgressBar(); self.progress.setRange(0,0); self.progress.setMaximumHeight(8)
        root.addWidget(self.progress)
        self.logs = QPlainTextEdit(); self.logs.setReadOnly(True); self.logs.setMaximumHeight(150)
        self.logs.document().setMaximumBlockCount(3000); self.logs.hide(); root.addWidget(self.logs)
        self.setCentralWidget(central)
        self.setStyleSheet('''
            QMainWindow { background: #f3f5f7; } QWidget { font-family: Segoe UI; font-size: 10pt; }
            QLabel#Heading { font-size: 20pt; font-weight: 600; color: #173447; }
            QLabel#Notice { color: #754c09; padding: 6px; background: #fff1cf; border-radius: 4px; }
            QGroupBox { font-weight: 600; border: 1px solid #c9d1d8; border-radius: 5px; margin-top: 10px; padding-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 9px; }
            QLineEdit,QComboBox,QSpinBox { min-height: 26px; }
            QPushButton { padding: 6px 9px; } QPushButton#Primary { background: #176278; color: white; font-weight: 600; }
            QPushButton#Primary:disabled { background: #a5b4bc; }
            QTabWidget::pane { border: 1px solid #c9d1d8; background: white; }
            QHeaderView::section { padding: 6px; background: #e5ebef; }
        ''')
        self.freecad_edit.setText(freecad_python); self.poppler_edit.setText(poppler); self.output_edit.setText(output)

    def _configuration(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); layout = QVBoxLayout(body)
        policy = QGroupBox('Drawing Settings'); form = QFormLayout(policy)
        self.mode = QComboBox(); self.mode.addItems(['Basic','Comprehensive','Custom'])
        self.mode.currentTextChanged.connect(self._mode_changed); form.addRow('Dimensioning Mode',self.mode)
        self.sheet = QComboBox(); self.sheet.addItems(['Automatic',*SHEETS]); form.addRow('Paper Size',self.sheet)
        self.scale = QComboBox(); self.scale.setEditable(True)
        self.scale.addItems(['Automatic','0.5','1','2','2.5','3','5','10']); form.addRow('Scale (Paper / Model)',self.scale)
        self.views = {}
        for key,text in [('isometric','Isometric View'),('opposite_end','Opposite-End View'),
                         ('section','Sectional View'),('opening_detail','Opening-Profile Detail')]:
            box = QCheckBox(text); self.views[key]=box; form.addRow(box)
        info = QLabel('Changing Mode Clears Explicit Selections. Optional Views Require Supporting Geometry.')
        info.setWordWrap(True); form.addRow(info); layout.addWidget(policy)
        metadata = QGroupBox('Drawing Metadata'); form = QFormLayout(metadata); self.metadata={}
        for key,label,limit in [('title','Drawing Title',65),('drawing_number','Drawing Number',32),('revision','Revision',12),('date','Date (YYYY-MM-DD)',10)]:
            edit=QLineEdit(); edit.setMaxLength(limit); self.metadata[key]=edit; form.addRow(label,edit)
        self.metadata['date'].setPlaceholderText('Blank Uses Generation Date'); layout.addWidget(metadata)
        orientation=QGroupBox('Orientation Overrides'); form=QFormLayout(orientation); self.orientation={}
        for key,label in [('axis','Longitudinal Axis (X, Y, Z)'),('up','View Up (X, Y, Z)')]:
            edit=QLineEdit(); edit.setPlaceholderText('Automatic'); self.orientation[key]=edit; form.addRow(label,edit)
        caption=QLabel('Overrides Are Verified Against Source Geometry. Blank Keeps Automatic Orientation.')
        caption.setWordWrap(True); form.addRow(caption); layout.addWidget(orientation)
        runtime=QGroupBox('Runtime And Output'); form=QFormLayout(runtime)
        self.output_edit=QLineEdit(); self.freecad_edit=QLineEdit(); self.poppler_edit=QLineEdit()
        for label,edit,folder,filter_text in [('Output Directory',self.output_edit,True,''),
                ('FreeCAD Python',self.freecad_edit,False,'Python (python.exe)'),
                ('Poppler Renderer',self.poppler_edit,False,'Poppler (pdftoppm.exe)')]:
            row=QWidget(); bar=QHBoxLayout(row); bar.setContentsMargins(0,0,0,0); bar.addWidget(edit,1)
            bar.addWidget(self._button('…',lambda checked=False,e=edit,d=folder,f=filter_text:self._browse_runtime(e,d,f)))
            form.addRow(label,row)
        layout.addWidget(runtime); layout.addStretch(); scroll.setWidget(body)
        for widget in [self.sheet,self.scale,*self.views.values(),*self.metadata.values(),*self.orientation.values()]:
            signal = (widget.currentTextChanged if isinstance(widget,QComboBox) else
                      widget.toggled if isinstance(widget,QCheckBox) else widget.textChanged)
            signal.connect(self._changed)
        return scroll

    def _browse_runtime(self,edit,directory,filter_text):
        options=QFileDialog.Option.DontUseNativeDialog
        path = (QFileDialog.getExistingDirectory(self,'Select Output Directory',edit.text(),options=options) if directory
                else QFileDialog.getOpenFileName(self,'Select Runtime Executable',edit.text(),filter_text,options=options)[0])
        if path: edit.setText(path)

    def browse_source(self):
        path,_=QFileDialog.getOpenFileName(self,'Import STEP Model',self.source_edit.text(),'STEP Models (*.stp *.step)',
                                        options=QFileDialog.Option.DontUseNativeDialog)
        if path: self.set_source(path)

    def _recent_source(self,index):
        if index: self.set_source(self.recent.itemText(index))

    def set_source(self,path):
        if self.backend.busy: return
        normalized=Path(path).resolve() if path else None
        if normalized==self.model.source: return
        self.model=ModelState(); self.model.source=normalized
        self.source_edit.setText(str(normalized) if normalized else '')
        self.source_edit.setToolTip(self.source_edit.text())
        self.summary.setText('Analyze Geometry Before Restoring Saved Selections')
        self.table.setRowCount(0); self.review_text.clear(); self._clear_release('New Source - Analyze And Generate To Preview')
        self._refresh_history(); self._busy_changed(False)

    def _request(self,action):
        if self.model.source is None: raise ValueError('Choose a STEP source file')
        return {'action':action,'source':str(self.model.source),'output':str(Path(self.output_edit.text()).resolve()),
                'freecad_python':self.freecad_edit.text(),'poppler':self.poppler_edit.text()}

    def _settings_save(self):
        if self.model.source:
            recent=[str(self.model.source),*[x for x in self.settings.get('recent',[]) if x!=str(self.model.source)]][:12]
        else: recent=self.settings.get('recent',[])
        self.settings={'source':str(self.model.source or ''),'recent':recent,'output':self.output_edit.text(),
                       'freecad_python':self.freecad_edit.text(),'poppler':self.poppler_edit.text()}
        atomic_json(self.settings_file,self.settings)

    def analyze(self):
        try:
            request=self._request('analyze'); self._settings_save(); self.action='analyze'
            self._clear_release('Analyzing Source - No New Drawing Yet')
            self.model.catalog=None; self.table.setRowCount(0)
            self.backend.start(request)
        except Exception as error: self._error(error)

    def _read_controls(self):
        config=copy.deepcopy(self.model.config)
        config['dimensioning']['mode']=self.mode.currentText().lower()
        config['sheet']['size']='auto' if self.sheet.currentText()=='Automatic' else self.sheet.currentText()
        config['scale']='auto' if self.scale.currentText()=='Automatic' else float(self.scale.currentText())
        config['views']={key:widget.isChecked() for key,widget in self.views.items()}
        config['metadata']={key:widget.text() or (None if key=='date' else '') for key,widget in self.metadata.items()}
        for key,widget in self.orientation.items():
            text=widget.text().strip()
            config['orientation'][key]=[float(x.strip()) for x in text.split(',')] if text else None
        from fastener_drawing.configuration import validate_config
        validate_config(config)
        if self.model.catalog: config=bind_config(config,self.model.catalog)
        self.model.config=config
        return self.model.checked_config()

    def _apply_config(self):
        self._loading=True
        config=self.model.config
        self.mode.setCurrentText(config['dimensioning']['mode'].title())
        self.sheet.setCurrentText('Automatic' if config['sheet']['size']=='auto' else config['sheet']['size'])
        self.scale.setCurrentText('Automatic' if config['scale']=='auto' else str(config['scale']))
        for key,widget in self.views.items(): widget.setChecked(config['views'][key])
        for key,widget in self.metadata.items(): widget.setText(config['metadata'][key] or '')
        for key,widget in self.orientation.items(): widget.setText(', '.join(map(str,config['orientation'][key])) if config['orientation'][key] else '')
        self._loading=False; self._populate_candidates()

    def _mode_changed(self,text):
        if self._loading: return
        self.model.config['dimensioning']={'mode':text.lower(),'include':[],'exclude':[]}
        self._populate_candidates(); self._changed()

    def _changed(self,*args):
        if not self._loading and self.release:
            self.preview.message.setText('Preview From Previous Generation - Regenerate To Apply Configuration Changes')

    def _populate_candidates(self):
        self._loading=True; self.table.setRowCount(0);self.candidate_detail.clear()
        if self.model.catalog and not self.model.binding_problem:
            decisions=self.model.decisions()
            rows=self.model.catalog['candidates']; self.table.setRowCount(len(rows))
            for index,row in enumerate(rows):
                item=QTableWidgetItem('')
                flags=Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable
                if self.mode.currentText()=='Custom': flags|=Qt.ItemFlag.ItemIsUserCheckable
                item.setFlags(flags); item.setData(Qt.ItemDataRole.UserRole,row['stable_id'])
                item.setCheckState(Qt.CheckState.Checked if decisions[row['candidate_id']]['selected'] else Qt.CheckState.Unchecked)
                item.setToolTip('Source-Bound Identity: '+row['stable_id']); self.table.setItem(index,0,item)
                value='Unresolved' if row['value'] is None else f"{row['value']:.8g}"
                status={'source_measured':'Measured','unsupported':'Unsupported'}.get(row['verification_status'],row['verification_status'])
                values=[row['label'],value,row['units'],status]
                for column,value in enumerate(values,1):
                    cell=QTableWidgetItem(str(value)); cell.setToolTip(str(value)); self.table.setItem(index,column,cell)
            self.table.resizeRowsToContents()
        self._loading=False

    def _candidate_details(self):
        if self._loading or self.model.catalog is None:return
        index=self.table.currentRow()
        if index<0:return
        row=self.model.catalog['candidates'][index]
        source=next(c for c in self.model.analysis['components'][0]['feature_discovery']['dimension_candidates'] if c['id']==row['candidate_id'])
        reason=source.get('reason') or 'Source geometry measured. Drawing associativity and independent measurements are verified during generation.'
        self.candidate_detail.setPlainText(row['label']+'\nSource Status: '+row['verification_status']+'\n'+reason)

    def _selection_changed(self,item):
        if self._loading or item.column()!=0: return
        try:
            self.model.set_selected(item.data(Qt.ItemDataRole.UserRole),item.checkState()==Qt.CheckState.Checked)
            self._changed()
        except Exception as error:self._error(error)

    def fresh_configuration(self):
        try:
            self.model.fresh_configuration(); self._apply_config(); self._busy_changed(False)
            self.status.setText('New Source-Bound Configuration - Previous Saved Policy Preserved Until Save')
        except Exception as error:self._error(error)

    def save_configuration(self):
        try:
            config=self._read_controls(); path=self.store.save(self.model.source,config)
            self._settings_save(); self.status.setText('Configuration Saved'); self._log('Saved '+str(path))
        except Exception as error:self._error(error)

    def load_configuration(self):
        path,_=QFileDialog.getOpenFileName(self,'Load Drawing Configuration','','JSON Configuration (*.json)',
                                        options=QFileDialog.Option.DontUseNativeDialog)
        if not path:return
        try:
            if self.model.catalog is None: raise ValueError('Analyze the current STEP file before loading selections')
            config=read_config(path)
            try: self.model.config=bind_config(config,self.model.catalog); self.model.binding_problem=None
            except ValueError as error:
                self.model.config=config; self.model.binding_problem=str(error)
                self.summary.setText('Configuration Requires Review: '+str(error))
            self._apply_config(); self._busy_changed(False)
        except Exception as error:self._error(error)

    def generate(self):
        try:
            request=self._request('generate'); request['config']=str(self.store.save(self.model.source,self._read_controls()))
            self._settings_save(); self.action='generate'
            self._clear_release('Generating A New Drawing - Previous Release Remains On Disk')
            self.backend.start(request)
        except Exception as error:self._error(error)

    def open_current(self):
        try:
            request=self._request('open_release')
            request['manifest']=str(Path(request['output'])/(self.model.source.stem+'.current.json'))
            self.action='open_release'; self._clear_release('Checking The Previously Published Release')
            self.backend.start(request)
        except Exception as error:self._error(error)

    def open_history(self):
        try:
            path=self.history.currentData()
            if not path:raise ValueError('Select a previous release first')
            request=self._request('open_history'); request['history']=path
            self.action='open_history'; self._clear_release('Checking An Explicitly Selected Historical Release')
            self.backend.start(request)
        except Exception as error:self._error(error)

    def _refresh_history(self):
        self.history.clear(); self.history.addItem('Select A Previous Release',None)
        if self.model.source:
            for run,path in history_entries(self.output_edit.text(),self.model.source): self.history.addItem(run,path)

    def _clear_release(self,message):
        self.release=None; self.preview.clear(message); self.release_label.setText('No Verified Release Selected')
        self.review_text.setPlainText(message+'\n\nNo Drawing Verification Report Is Selected. '
            'Open A Retained Release Explicitly To Review Its Evidence. Engineering Approval Is Not Assigned.')
        for button in self.output_buttons:button.setEnabled(False)

    def _stage(self,message):
        self.status.setText(message); self._log(message)
        if message=='Publishing The Complete Release': self.cancel_button.setEnabled(False)

    def _log(self,message):
        self.logs.appendPlainText(str(message))

    def _error(self,error):
        self.status.setText('Action Requires Review: '+str(error)); self._log(str(error))
        self.logs.show(); self.log_toggle.setText('Hide Logs')

    def _preview_failed(self,message):
        self._log(message); self.status.setText('Drawing Published - Embedded Preview Requires Review')

    def _busy_changed(self,busy):
        for widget in (self.import_group,self.config_tabs,self.save_button,self.load_button,self.fresh_button,
                       self.current_button,self.history_button,self.history):widget.setEnabled(not busy)
        self.generate_button.setEnabled(not busy and self.model.catalog is not None and not self.model.binding_problem)
        self.fresh_button.setEnabled(not busy and self.model.catalog is not None)
        self.save_button.setEnabled(not busy and self.model.catalog is not None and not self.model.binding_problem)
        self.cancel_button.setEnabled(busy); self.progress.setVisible(busy)
        for button in self.output_buttons:button.setEnabled(not busy and self.release is not None)

    def _completed(self,code,result):
        self.status.setText(completion_status(code,result))
        if code in (0,2) and result:
            try:
                if self.action=='analyze':
                    catalog=read_json(result['catalog']); analysis=read_json(result['analysis'])
                    try:saved=self.store.load(self.model.source)
                    except (OSError,ValueError) as error:
                        saved=None
                        self.model.accept_analysis(self.model.source,catalog,analysis)
                        self.model.binding_problem='Saved JSON Requires Review: '+str(error)
                    else:self.model.accept_analysis(self.model.source,catalog,analysis,saved)
                    discovery=analysis['components'][0]['feature_discovery']
                    boolean=analysis['validation']['boolean_check']
                    count=boolean.get('message','').count('Error in ')
                    self.summary.setText(f"{len(discovery['features'])} Recognized Geometric Features; {len(catalog['candidates'])} Dimension Candidates.\n"
                        f"Extended Boolean Check: {boolean['status']}; {count} Reported Problems.\n"
                        +(self.model.binding_problem or 'Saved Selections Restored Only After Source Binding Validation.'))
                    self.review_text.setPlainText('SOURCE GEOMETRY REVIEW\n\nPRELIMINARY - ENGINEERING VERIFICATION REQUIRED\n\n'
                        +'Feature Functions Are Inferences; Candidate Values Are Source Geometry Measurements.\n\n'
                        +json.dumps({'source_validation':analysis['validation'],'recognition':analysis['components'][0]['recognition'],
                                     'limitations':discovery.get('limitations',[]),'unmapped_faces':discovery['unmapped_faces']},indent=2))
                    self._apply_config()
                else:
                    self.release=result['release']
                    run=self.release['manifest']['run_id']
                    label='Historical Release' if self.action=='open_history' else 'Published Release'
                    mode=self.release['report']['configuration']['dimensioning']['mode'].title()
                    self.release_label.setText(label+': '+run+' | Drawing Mode: '+mode+'\n'+self.release['directory'])
                    self.preview.load(self.release['pdf'])
                    self._show_release_review()
                    self.result_tabs.setCurrentIndex(0)
                    if self.action in ('open_release','open_history'):self.status.setText(label+' Opened - Preliminary, Engineering Review Required')
            except Exception as error:
                self._clear_release('Output Validation Or Preview Failed'); self._error(error)
        else:
            self._clear_release('No New Drawing - Generation Cancelled Or Failed. Previous Releases Remain Available Through History.')
            self._log(self.backend.last_error or self.status.text()); self.logs.show(); self.log_toggle.setText('Hide Logs')
        self._refresh_history(); self._busy_changed(False)
        if self._closing: QTimer.singleShot(0,self.close)

    def _show_release_review(self):
        review=self.release['review']; report=self.release['report']
        created=[r for r in report['dimensions'].values() if r['status']=='created']
        checks=report['reopen_checks'].get('dimension_checks',{})
        verified=sum(bool(checks.get(key,{}).get('measurement_verified') and checks.get(key,{}).get('references_verified'))
                     for key,r in report['dimensions'].items() if r['status']=='created')
        lines=['PRELIMINARY - ENGINEERING APPROVAL NOT ASSIGNED', '',
               'PDF Generation: Published, Normalized And Independently Verified',
               f'CAD Dimension Measurement And Associativity: {verified} / {len(created)} Created Dimensions Verified',
               'Source Geometry: '+('Requires Review' if report['geometry_requires_review'] else 'Validation Recorded'),
               'Selected Dimensions Needing Review: '+str(len(report['unresolved_dimensions'])),
               'Source Candidates With Unsupported Evidence: '+str(sum(r['source_verification']!='source_measured' for r in review['characteristics'])),
               'Unrecognized Semantic Dimension Roles: '+str(sum(r['status']!='recognized' for r in review['semantic_recognition']['dimensions'].values())),
               'Thread Classification: '+review['semantic_recognition']['threads']['status'], '',
               'Recognized Source Characteristics (Selection Does Not Guarantee A Drawable Dimension)', '']
        for row in review['characteristics']:
            value='Unresolved' if row['measured_value'] is None else f"{row['measured_value']:.8g} {row['units']}"
            lines.append(f"{row['label']}: {value} | {'Selected' if row['selected'] else 'Suppressed'} | {row['drawing_status']} | {row['source_verification']}")
            lines.append('  '+str(row['reason']))
        lines += ['', 'Source Geometry Validation', json.dumps(review['source_validation'],indent=2),
                  '', 'Inferred Feature Classification',json.dumps(review['semantic_recognition'],indent=2),
                  '', 'Unmapped Faces',json.dumps(review['unmapped_faces'],indent=2),
                  '', 'Section Material Diagnostics',json.dumps(review['section_diagnostics'],indent=2)]
        self.review_text.setPlainText('\n'.join(lines))

    def open_artifact(self,key):
        if self.release:
            try:
                self.file_opener.open(self.release[key])
                self.status.setText('Requesting The System PDF Viewer - Embedded Preview Remains Available')
            except Exception as error:self._error(error)

    def open_project(self):
        if not self.release:return
        executable=Path(self.freecad_edit.text()).parent/'freecad.exe'
        if not executable.is_file():self._error('FreeCAD GUI Executable Not Found Beside Its Configured Python');return
        from PySide6.QtCore import QProcess, QProcessEnvironment
        process=QProcess(self); environment=QProcessEnvironment.systemEnvironment()
        for key in ('PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH','QML2_IMPORT_PATH','QT_QPA_PLATFORM'):environment.remove(key)
        process.setProcessEnvironment(environment)
        process.setProgram(str(executable));process.setArguments([self.release['project']])
        if not process.startDetached()[0]:self._error('FreeCAD Could Not Be Launched')

    def export_artifact(self,key):
        if not self.release:return
        suffix='pdf' if key=='pdf' else 'FCStd'
        path,_=QFileDialog.getSaveFileName(self,'Save '+('PDF' if key=='pdf' else 'FreeCAD Project')+' As',
            str(Path.home()/Path(self.release[key]).name),f'{suffix} Files (*.{suffix})',
            options=QFileDialog.Option.DontUseNativeDialog)
        if not path:return
        try:export_copy(self.release,key,path);self.status.setText('Export Copy Saved And Checksum Verified')
        except Exception as error:self._error(error)

    def _toggle_logs(self):
        self.logs.setVisible(not self.logs.isVisible());self.log_toggle.setText('Hide Logs' if self.logs.isVisible() else 'Show Logs')

    def closeEvent(self,event):
        if self.backend.busy:
            self._closing=True;self.backend.cancel();event.ignore()
        else:
            self.file_opener.stop_helpers()
            try:self._settings_save()
            except OSError:pass
            self.preview.document.close();event.accept()
