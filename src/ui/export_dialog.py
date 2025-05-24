"""
BLOUcut 내보내기 다이얼로그
비디오 내보내기를 위한 사용자 인터페이스
"""

import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                            QLabel, QComboBox, QPushButton, QLineEdit, QSpinBox,
                            QProgressBar, QTextEdit, QGroupBox, QCheckBox,
                            QFileDialog, QMessageBox, QFrame, QSlider,
                            QDoubleSpinBox, QTabWidget, QWidget, QFormLayout,
                            QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette

from ..export.export_manager import ExportManager

class ExportDialog(QDialog):
    """내보내기 다이얼로그"""
    
    def __init__(self, timeline, parent=None):
        super().__init__(parent)
        self.timeline = timeline
        self.export_manager = ExportManager()
        self.output_path = ""
        
        self.setWindowTitle("비디오 내보내기")
        self.setFixedSize(700, 800)
        self.setModal(True)
        
        # UI 초기화
        self.setup_ui()
        self.setup_connections()
        self.load_presets()
        
        # 스타일 적용
        self.apply_styles()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title_label = QLabel("비디오 내보내기")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 기본 설정 탭
        self.create_basic_tab()
        
        # 고급 설정 탭
        self.create_advanced_tab()
        
        # 출력 파일 설정
        self.create_output_section(layout)
        
        # 진행률 표시
        self.create_progress_section(layout)
        
        # 버튼들
        self.create_buttons(layout)
        
    def create_basic_tab(self):
        """기본 설정 탭"""
        basic_widget = QWidget()
        layout = QVBoxLayout(basic_widget)
        layout.setSpacing(15)
        
        # 프리셋 선택
        preset_group = QGroupBox("프리셋 선택")
        preset_layout = QFormLayout(preset_group)
        
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumHeight(35)
        preset_layout.addRow("프리셋:", self.preset_combo)
        
        self.preset_description = QLabel("")
        self.preset_description.setWordWrap(True)
        self.preset_description.setStyleSheet("color: #666; font-style: italic;")
        preset_layout.addRow("설명:", self.preset_description)
        
        layout.addWidget(preset_group)
        
        # 빠른 설정
        quick_group = QGroupBox("빠른 설정")
        quick_layout = QFormLayout(quick_group)
        
        # 해상도
        resolution_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(64, 7680)
        self.width_spin.setValue(1920)
        self.width_spin.setSuffix(" px")
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(64, 4320)
        self.height_spin.setValue(1080)
        self.height_spin.setSuffix(" px")
        
        resolution_layout.addWidget(self.width_spin)
        resolution_layout.addWidget(QLabel("×"))
        resolution_layout.addWidget(self.height_spin)
        resolution_layout.addStretch()
        
        quick_layout.addRow("해상도:", resolution_layout)
        
        # 프레임레이트
        self.framerate_combo = QComboBox()
        self.framerate_combo.addItems(["23.976", "24", "25", "29.97", "30", "50", "59.94", "60"])
        self.framerate_combo.setCurrentText("30")
        quick_layout.addRow("프레임레이트:", self.framerate_combo)
        
        # 품질
        quality_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(15, 35)
        self.quality_slider.setValue(23)
        self.quality_label = QLabel("23 (고품질)")
        
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        
        quick_layout.addRow("품질 (CRF):", quality_layout)
        
        layout.addWidget(quick_group)
        
        # 미리보기 정보
        preview_group = QGroupBox("미리보기")
        preview_layout = QFormLayout(preview_group)
        
        self.preview_size = QLabel("약 50MB")
        self.preview_duration = QLabel("00:00:30")
        self.preview_bitrate = QLabel("5.5 Mbps")
        
        preview_layout.addRow("예상 파일 크기:", self.preview_size)
        preview_layout.addRow("예상 길이:", self.preview_duration)
        preview_layout.addRow("비트레이트:", self.preview_bitrate)
        
        layout.addWidget(preview_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(basic_widget, "기본 설정")
        
    def create_advanced_tab(self):
        """고급 설정 탭"""
        advanced_widget = QWidget()
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(advanced_widget)
        
        layout = QVBoxLayout(advanced_widget)
        layout.setSpacing(15)
        
        # 비디오 코덱 설정
        video_group = QGroupBox("비디오 설정")
        video_layout = QFormLayout(video_group)
        
        self.video_codec_combo = QComboBox()
        self.video_codec_combo.addItems(["libx264", "libx265", "libvpx-vp9", "prores"])
        video_layout.addRow("비디오 코덱:", self.video_codec_combo)
        
        self.video_bitrate = QLineEdit("8M")
        video_layout.addRow("비디오 비트레이트:", self.video_bitrate)
        
        self.preset_combo_adv = QComboBox()
        self.preset_combo_adv.addItems(["ultrafast", "superfast", "veryfast", "faster", 
                                        "fast", "medium", "slow", "slower", "veryslow"])
        self.preset_combo_adv.setCurrentText("medium")
        video_layout.addRow("인코딩 프리셋:", self.preset_combo_adv)
        
        layout.addWidget(video_group)
        
        # 오디오 설정
        audio_group = QGroupBox("오디오 설정")
        audio_layout = QFormLayout(audio_group)
        
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(["aac", "mp3", "flac", "opus"])
        audio_layout.addRow("오디오 코덱:", self.audio_codec_combo)
        
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems(["96k", "128k", "192k", "256k", "320k"])
        self.audio_bitrate_combo.setCurrentText("128k")
        audio_layout.addRow("오디오 비트레이트:", self.audio_bitrate_combo)
        
        self.audio_samplerate_combo = QComboBox()
        self.audio_samplerate_combo.addItems(["44100", "48000", "96000"])
        self.audio_samplerate_combo.setCurrentText("48000")
        audio_layout.addRow("샘플레이트:", self.audio_samplerate_combo)
        
        layout.addWidget(audio_group)
        
        # 필터 설정
        filter_group = QGroupBox("필터 설정")
        filter_layout = QFormLayout(filter_group)
        
        self.deinterlace_check = QCheckBox("디인터레이스")
        filter_layout.addRow(self.deinterlace_check)
        
        self.denoise_check = QCheckBox("노이즈 제거")
        filter_layout.addRow(self.denoise_check)
        
        self.stabilize_check = QCheckBox("손떨림 보정")
        filter_layout.addRow(self.stabilize_check)
        
        layout.addWidget(filter_group)
        
        # 하드웨어 가속
        hardware_group = QGroupBox("하드웨어 가속")
        hardware_layout = QFormLayout(hardware_group)
        
        self.hardware_accel_combo = QComboBox()
        self.hardware_accel_combo.addItems(["없음", "NVENC (NVIDIA)", "QuickSync (Intel)", "AMF (AMD)"])
        hardware_layout.addRow("하드웨어 가속:", self.hardware_accel_combo)
        
        layout.addWidget(hardware_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(scroll, "고급 설정")
        
    def create_output_section(self, layout):
        """출력 파일 설정"""
        output_group = QGroupBox("출력 파일")
        output_layout = QHBoxLayout(output_group)
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("출력 파일 경로를 선택하세요...")
        output_layout.addWidget(self.output_path_edit)
        
        self.browse_button = QPushButton("찾아보기")
        self.browse_button.setMinimumWidth(100)
        output_layout.addWidget(self.browse_button)
        
        layout.addWidget(output_group)
        
    def create_progress_section(self, layout):
        """진행률 표시 섹션"""
        progress_group = QGroupBox("진행 상황")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
    def create_buttons(self, layout):
        """버튼 생성"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("취소")
        self.cancel_button.setMinimumSize(100, 35)
        button_layout.addWidget(self.cancel_button)
        
        self.export_button = QPushButton("내보내기")
        self.export_button.setMinimumSize(100, 35)
        self.export_button.setDefault(True)
        button_layout.addWidget(self.export_button)
        
        layout.addLayout(button_layout)
        
    def setup_connections(self):
        """시그널 연결"""
        # 버튼 연결
        self.browse_button.clicked.connect(self.browse_output_file)
        self.export_button.clicked.connect(self.start_export)
        self.cancel_button.clicked.connect(self.close)
        
        # 프리셋 변경
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        
        # 품질 슬라이더
        self.quality_slider.valueChanged.connect(self.update_quality_label)
        
        # 내보내기 관리자 연결
        self.export_manager.export_started.connect(self.on_export_started)
        self.export_manager.export_finished.connect(self.on_export_finished)
        self.export_manager.export_progress.connect(self.on_export_progress)
        self.export_manager.export_status.connect(self.on_export_status)
        
    def load_presets(self):
        """프리셋 로드"""
        presets = self.export_manager.get_preset_names()
        for preset_name in presets:
            preset = self.export_manager.get_preset(preset_name)
            self.preset_combo.addItem(preset.name, preset_name)
            
        # 기본 프리셋 선택
        if presets:
            self.preset_combo.setCurrentIndex(0)
            self.on_preset_changed()
            
    def on_preset_changed(self):
        """프리셋 변경 시"""
        preset_key = self.preset_combo.currentData()
        if preset_key:
            preset = self.export_manager.get_preset(preset_key)
            if preset:
                self.preset_description.setText(preset.description)
                self.load_preset_settings(preset)
                
    def load_preset_settings(self, preset):
        """프리셋 설정 로드"""
        settings = preset.settings
        
        # 기본 설정 탭
        if 'resolution' in settings:
            width, height = settings['resolution']
            self.width_spin.setValue(width)
            self.height_spin.setValue(height)
            
        if 'framerate' in settings:
            self.framerate_combo.setCurrentText(str(settings['framerate']))
            
        if 'crf' in settings:
            self.quality_slider.setValue(settings['crf'])
            
        # 고급 설정 탭
        if 'video_codec' in settings:
            self.video_codec_combo.setCurrentText(settings['video_codec'])
            
        if 'video_bitrate' in settings:
            self.video_bitrate.setText(settings['video_bitrate'])
            
        if 'preset' in settings:
            self.preset_combo_adv.setCurrentText(settings['preset'])
            
        if 'audio_codec' in settings:
            self.audio_codec_combo.setCurrentText(settings['audio_codec'])
            
        if 'audio_bitrate' in settings:
            self.audio_bitrate_combo.setCurrentText(settings['audio_bitrate'])
            
    def update_quality_label(self):
        """품질 라벨 업데이트"""
        value = self.quality_slider.value()
        if value <= 18:
            quality_text = "최고품질"
        elif value <= 23:
            quality_text = "고품질"
        elif value <= 28:
            quality_text = "표준품질"
        else:
            quality_text = "저품질"
            
        self.quality_label.setText(f"{value} ({quality_text})")
        
    def browse_output_file(self):
        """출력 파일 선택"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "내보낼 파일 저장",
            f"output.mp4",
            "비디오 파일 (*.mp4 *.mov *.avi *.mkv);;모든 파일 (*)"
        )
        
        if file_path:
            self.output_path = file_path
            self.output_path_edit.setText(file_path)
            
    def start_export(self):
        """내보내기 시작"""
        if not self.output_path:
            QMessageBox.warning(self, "경고", "출력 파일 경로를 선택해주세요.")
            return
            
        # 현재 설정 수집
        custom_settings = self.collect_current_settings()
        
        # 선택된 프리셋
        preset_key = self.preset_combo.currentData()
        
        # 내보내기 시작
        self.export_manager.export_video(
            self.timeline,
            self.output_path,
            preset_key,
            custom_settings
        )
        
    def collect_current_settings(self):
        """현재 설정 수집"""
        return {
            'resolution': [self.width_spin.value(), self.height_spin.value()],
            'framerate': float(self.framerate_combo.currentText()),
            'crf': self.quality_slider.value(),
            'video_codec': self.video_codec_combo.currentText(),
            'video_bitrate': self.video_bitrate.text(),
            'preset': self.preset_combo_adv.currentText(),
            'audio_codec': self.audio_codec_combo.currentText(),
            'audio_bitrate': self.audio_bitrate_combo.currentText(),
        }
        
    def on_export_started(self, output_path):
        """내보내기 시작됨"""
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.export_button.setText("내보내기 취소")
        self.export_button.clicked.disconnect()
        self.export_button.clicked.connect(self.cancel_export)
        
    def on_export_finished(self, success, message):
        """내보내기 완료"""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.export_button.setText("내보내기")
        self.export_button.clicked.disconnect()
        self.export_button.clicked.connect(self.start_export)
        
        if success:
            QMessageBox.information(self, "완료", f"내보내기가 완료되었습니다.\n{message}")
            self.close()
        else:
            QMessageBox.critical(self, "오류", f"내보내기 실패:\n{message}")
            
    def on_export_progress(self, progress):
        """내보내기 진행률 업데이트"""
        self.progress_bar.setValue(progress)
        
    def on_export_status(self, status):
        """내보내기 상태 업데이트"""
        self.status_label.setText(status)
        
    def cancel_export(self):
        """내보내기 취소"""
        self.export_manager.cancel_export()
        
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 10px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333333;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
            QComboBox, QSpinBox, QLineEdit {
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 5px;
                background-color: white;
            }
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
                border-color: #4CAF50;
            }
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 8px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 6px;
            }
        """) 