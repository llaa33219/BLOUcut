"""
BLOUcut 속성 패널
선택된 클립의 속성 편집
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QSlider, QSpinBox, QDoubleSpinBox, QGroupBox,
                           QComboBox, QCheckBox, QLineEdit, QScrollArea,
                           QColorDialog, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

class PropertiesPanel(QWidget):
    """속성 패널"""
    
    # 시그널
    property_changed = pyqtSignal(str, object)  # 속성 이름, 값
    
    def __init__(self):
        super().__init__()
        self.current_clips = []  # 현재 선택된 클립들
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        
        # 클립 정보 그룹
        self.info_group = self.create_info_group()
        self.scroll_layout.addWidget(self.info_group)
        
        # 변형 그룹
        self.transform_group = self.create_transform_group()
        self.scroll_layout.addWidget(self.transform_group)
        
        # 오디오 그룹
        self.audio_group = self.create_audio_group()
        self.scroll_layout.addWidget(self.audio_group)
        
        # 색상 보정 그룹
        self.color_group = self.create_color_group()
        self.scroll_layout.addWidget(self.color_group)
        
        # 효과 그룹
        self.effects_group = self.create_effects_group()
        self.scroll_layout.addWidget(self.effects_group)
        
        self.scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 초기에는 모든 그룹 숨김
        self.hide_all_groups()
        
        self.apply_styles()
        
    def create_info_group(self):
        """클립 정보 그룹"""
        group = QGroupBox("클립 정보")
        layout = QVBoxLayout(group)
        
        # 클립 이름
        self.clip_name_label = QLabel("클립 이름: -")
        layout.addWidget(self.clip_name_label)
        
        # 클립 타입
        self.clip_type_label = QLabel("타입: -")
        layout.addWidget(self.clip_type_label)
        
        # 지속시간
        self.duration_label = QLabel("길이: -")
        layout.addWidget(self.duration_label)
        
        # 시작/종료 시간
        self.time_range_label = QLabel("시간: -")
        layout.addWidget(self.time_range_label)
        
        return group
        
    def create_transform_group(self):
        """변형 그룹"""
        group = QGroupBox("변형")
        layout = QVBoxLayout(group)
        
        # 위치
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("위치:"))
        
        self.pos_x_spin = QDoubleSpinBox()
        self.pos_x_spin.setRange(-1000, 1000)
        self.pos_x_spin.setSingleStep(0.1)
        self.pos_x_spin.valueChanged.connect(lambda v: self.on_property_changed('position_x', v))
        pos_layout.addWidget(self.pos_x_spin)
        
        self.pos_y_spin = QDoubleSpinBox()
        self.pos_y_spin.setRange(-1000, 1000)
        self.pos_y_spin.setSingleStep(0.1)
        self.pos_y_spin.valueChanged.connect(lambda v: self.on_property_changed('position_y', v))
        pos_layout.addWidget(self.pos_y_spin)
        
        layout.addLayout(pos_layout)
        
        # 크기
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("크기:"))
        
        self.scale_x_spin = QDoubleSpinBox()
        self.scale_x_spin.setRange(0.1, 10.0)
        self.scale_x_spin.setSingleStep(0.1)
        self.scale_x_spin.setValue(1.0)
        self.scale_x_spin.valueChanged.connect(lambda v: self.on_property_changed('scale_x', v))
        scale_layout.addWidget(self.scale_x_spin)
        
        self.scale_y_spin = QDoubleSpinBox()
        self.scale_y_spin.setRange(0.1, 10.0)
        self.scale_y_spin.setSingleStep(0.1)
        self.scale_y_spin.setValue(1.0)
        self.scale_y_spin.valueChanged.connect(lambda v: self.on_property_changed('scale_y', v))
        scale_layout.addWidget(self.scale_y_spin)
        
        # 비율 유지 체크박스
        self.uniform_scale_check = QCheckBox("비율 유지")
        self.uniform_scale_check.setChecked(True)
        scale_layout.addWidget(self.uniform_scale_check)
        
        layout.addLayout(scale_layout)
        
        # 회전
        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("회전:"))
        
        self.rotation_slider = QSlider(Qt.Orientation.Horizontal)
        self.rotation_slider.setRange(0, 360)
        self.rotation_slider.valueChanged.connect(lambda v: self.on_property_changed('rotation', v))
        rotation_layout.addWidget(self.rotation_slider)
        
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(0, 360)
        self.rotation_spin.setSuffix("°")
        self.rotation_spin.valueChanged.connect(self.rotation_slider.setValue)
        self.rotation_slider.valueChanged.connect(self.rotation_spin.setValue)
        rotation_layout.addWidget(self.rotation_spin)
        
        layout.addLayout(rotation_layout)
        
        # 불투명도
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("불투명도:"))
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(lambda v: self.on_property_changed('opacity', v/100.0))
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(100)
        self.opacity_spin.setSuffix("%")
        self.opacity_spin.valueChanged.connect(self.opacity_slider.setValue)
        self.opacity_slider.valueChanged.connect(self.opacity_spin.setValue)
        opacity_layout.addWidget(self.opacity_spin)
        
        layout.addLayout(opacity_layout)
        
        return group
        
    def create_audio_group(self):
        """오디오 그룹"""
        group = QGroupBox("오디오")
        layout = QVBoxLayout(group)
        
        # 볼륨
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("볼륨:"))
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 200)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(lambda v: self.on_property_changed('volume', v/100.0))
        volume_layout.addWidget(self.volume_slider)
        
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(0, 200)
        self.volume_spin.setValue(100)
        self.volume_spin.setSuffix("%")
        self.volume_spin.valueChanged.connect(self.volume_slider.setValue)
        self.volume_slider.valueChanged.connect(self.volume_spin.setValue)
        volume_layout.addWidget(self.volume_spin)
        
        layout.addLayout(volume_layout)
        
        # 페이드 인
        fade_in_layout = QHBoxLayout()
        fade_in_layout.addWidget(QLabel("페이드 인:"))
        
        self.fade_in_spin = QSpinBox()
        self.fade_in_spin.setRange(0, 300)
        self.fade_in_spin.setSuffix(" 프레임")
        self.fade_in_spin.valueChanged.connect(lambda v: self.on_property_changed('fade_in', v))
        fade_in_layout.addWidget(self.fade_in_spin)
        
        layout.addLayout(fade_in_layout)
        
        # 페이드 아웃
        fade_out_layout = QHBoxLayout()
        fade_out_layout.addWidget(QLabel("페이드 아웃:"))
        
        self.fade_out_spin = QSpinBox()
        self.fade_out_spin.setRange(0, 300)
        self.fade_out_spin.setSuffix(" 프레임")
        self.fade_out_spin.valueChanged.connect(lambda v: self.on_property_changed('fade_out', v))
        fade_out_layout.addWidget(self.fade_out_spin)
        
        layout.addLayout(fade_out_layout)
        
        return group
        
    def create_color_group(self):
        """색상 보정 그룹"""
        group = QGroupBox("색상 보정")
        layout = QVBoxLayout(group)
        
        # 밝기
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("밝기:"))
        
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(lambda v: self.on_property_changed('brightness', v/100.0))
        brightness_layout.addWidget(self.brightness_slider)
        
        self.brightness_spin = QSpinBox()
        self.brightness_spin.setRange(-100, 100)
        self.brightness_spin.setValue(0)
        self.brightness_spin.valueChanged.connect(self.brightness_slider.setValue)
        self.brightness_slider.valueChanged.connect(self.brightness_spin.setValue)
        brightness_layout.addWidget(self.brightness_spin)
        
        layout.addLayout(brightness_layout)
        
        # 대비
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("대비:"))
        
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(-100, 100)
        self.contrast_slider.setValue(0)
        self.contrast_slider.valueChanged.connect(lambda v: self.on_property_changed('contrast', v/100.0))
        contrast_layout.addWidget(self.contrast_slider)
        
        self.contrast_spin = QSpinBox()
        self.contrast_spin.setRange(-100, 100)
        self.contrast_spin.setValue(0)
        self.contrast_spin.valueChanged.connect(self.contrast_slider.setValue)
        self.contrast_slider.valueChanged.connect(self.contrast_spin.setValue)
        contrast_layout.addWidget(self.contrast_spin)
        
        layout.addLayout(contrast_layout)
        
        # 채도
        saturation_layout = QHBoxLayout()
        saturation_layout.addWidget(QLabel("채도:"))
        
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(-100, 100)
        self.saturation_slider.setValue(0)
        self.saturation_slider.valueChanged.connect(lambda v: self.on_property_changed('saturation', v/100.0))
        saturation_layout.addWidget(self.saturation_slider)
        
        self.saturation_spin = QSpinBox()
        self.saturation_spin.setRange(-100, 100)
        self.saturation_spin.setValue(0)
        self.saturation_spin.valueChanged.connect(self.saturation_slider.setValue)
        self.saturation_slider.valueChanged.connect(self.saturation_spin.setValue)
        saturation_layout.addWidget(self.saturation_spin)
        
        layout.addLayout(saturation_layout)
        
        # 색조
        hue_layout = QHBoxLayout()
        hue_layout.addWidget(QLabel("색조:"))
        
        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setRange(-180, 180)
        self.hue_slider.setValue(0)
        self.hue_slider.valueChanged.connect(lambda v: self.on_property_changed('hue', v))
        hue_layout.addWidget(self.hue_slider)
        
        self.hue_spin = QSpinBox()
        self.hue_spin.setRange(-180, 180)
        self.hue_spin.setValue(0)
        self.hue_spin.setSuffix("°")
        self.hue_spin.valueChanged.connect(self.hue_slider.setValue)
        self.hue_slider.valueChanged.connect(self.hue_spin.setValue)
        hue_layout.addWidget(self.hue_spin)
        
        layout.addLayout(hue_layout)
        
        return group
        
    def create_effects_group(self):
        """효과 그룹"""
        group = QGroupBox("적용된 효과")
        layout = QVBoxLayout(group)
        
        # 효과 리스트
        self.effects_list = QLabel("적용된 효과가 없습니다.")
        self.effects_list.setWordWrap(True)
        layout.addWidget(self.effects_list)
        
        # 효과 제거 버튼
        remove_effects_button = QPushButton("모든 효과 제거")
        remove_effects_button.clicked.connect(self.remove_all_effects)
        layout.addWidget(remove_effects_button)
        
        return group
        
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QWidget {
                background-color: #3c3c3c;
                color: white;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #777;
                height: 6px;
                background: #555;
                border-radius: 3px;
            }
            
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #777;
                width: 12px;
                border-radius: 6px;
                margin: -3px 0;
            }
            
            QSlider::handle:horizontal:hover {
                background: #45a049;
            }
            
            QSpinBox, QDoubleSpinBox {
                background-color: #555;
                border: 1px solid #777;
                border-radius: 3px;
                padding: 2px;
                min-width: 60px;
            }
            
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #4CAF50;
            }
            
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
            }
            
            QCheckBox::indicator:unchecked {
                background-color: #555;
                border: 1px solid #777;
                border-radius: 3px;
            }
            
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 1px solid #777;
                border-radius: 3px;
            }
            
            QPushButton {
                background-color: #555;
                border: 1px solid #777;
                border-radius: 3px;
                padding: 5px 10px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #666;
            }
            
            QPushButton:pressed {
                background-color: #444;
            }
        """)
        
    def hide_all_groups(self):
        """모든 그룹 숨기기"""
        self.info_group.hide()
        self.transform_group.hide()
        self.audio_group.hide()
        self.color_group.hide()
        self.effects_group.hide()
        
    def update_properties(self, clips):
        """선택된 클립의 속성 업데이트"""
        self.current_clips = clips
        
        if not clips:
            self.hide_all_groups()
            return
            
        # 첫 번째 클립 기준으로 표시
        clip = clips[0]
        
        # 정보 그룹 업데이트
        self.update_info_group(clip)
        
        # 변형 그룹 업데이트
        self.update_transform_group(clip)
        
        # 오디오 그룹 업데이트 (비디오/오디오 클립만)
        if hasattr(clip, 'clip_type') and clip.clip_type.value in ['video', 'audio']:
            self.update_audio_group(clip)
            self.audio_group.show()
        else:
            self.audio_group.hide()
            
        # 색상 보정 그룹 업데이트 (비디오/이미지 클립만)
        if hasattr(clip, 'clip_type') and clip.clip_type.value in ['video', 'image']:
            self.update_color_group(clip)
            self.color_group.show()
        else:
            self.color_group.hide()
            
        # 효과 그룹 업데이트
        self.update_effects_group(clip)
        
        # 그룹들 표시
        self.info_group.show()
        self.transform_group.show()
        self.effects_group.show()
        
    def update_info_group(self, clip):
        """정보 그룹 업데이트"""
        self.clip_name_label.setText(f"클립 이름: {clip.name}")
        self.clip_type_label.setText(f"타입: {clip.clip_type.value if hasattr(clip, 'clip_type') else '알 수 없음'}")
        
        # 지속시간 (프레임을 시간으로 변환)
        total_seconds = clip.duration / 30  # 30fps 기준
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        frames = clip.duration % 30
        duration_str = f"{minutes:02d}:{seconds:02d}:{frames:02d}"
        self.duration_label.setText(f"길이: {duration_str}")
        
        # 시간 범위
        start_seconds = clip.start_frame / 30
        start_minutes = int(start_seconds // 60)
        start_secs = int(start_seconds % 60)
        start_frames = clip.start_frame % 30
        
        end_frame = clip.start_frame + clip.duration
        end_seconds = end_frame / 30
        end_minutes = int(end_seconds // 60)
        end_secs = int(end_seconds % 60)
        end_frame_remainder = end_frame % 30
        
        time_range = f"{start_minutes:02d}:{start_secs:02d}:{start_frames:02d} - {end_minutes:02d}:{end_secs:02d}:{end_frame_remainder:02d}"
        self.time_range_label.setText(f"시간: {time_range}")
        
    def update_transform_group(self, clip):
        """변형 그룹 업데이트"""
        # 시그널 연결 임시 해제
        self.disconnect_transform_signals()
        
        self.pos_x_spin.setValue(clip.position_x)
        self.pos_y_spin.setValue(clip.position_y)
        self.scale_x_spin.setValue(clip.scale_x)
        self.scale_y_spin.setValue(clip.scale_y)
        self.rotation_slider.setValue(int(clip.rotation))
        self.opacity_slider.setValue(int(clip.opacity * 100))
        
        # 시그널 다시 연결
        self.connect_transform_signals()
        
    def update_audio_group(self, clip):
        """오디오 그룹 업데이트"""
        # 시그널 연결 임시 해제
        self.disconnect_audio_signals()
        
        self.volume_slider.setValue(int(clip.volume * 100))
        self.fade_in_spin.setValue(clip.fade_in)
        self.fade_out_spin.setValue(clip.fade_out)
        
        # 시그널 다시 연결
        self.connect_audio_signals()
        
    def update_color_group(self, clip):
        """색상 보정 그룹 업데이트"""
        # 시그널 연결 임시 해제
        self.disconnect_color_signals()
        
        self.brightness_slider.setValue(int(clip.brightness * 100))
        self.contrast_slider.setValue(int(clip.contrast * 100))
        self.saturation_slider.setValue(int(clip.saturation * 100))
        self.hue_slider.setValue(int(clip.hue))
        
        # 시그널 다시 연결
        self.connect_color_signals()
        
    def update_effects_group(self, clip):
        """효과 그룹 업데이트"""
        if clip.effects:
            effects_text = "\n".join([f"• {effect}" for effect in clip.effects])
            self.effects_list.setText(effects_text)
        else:
            self.effects_list.setText("적용된 효과가 없습니다.")
            
    def disconnect_transform_signals(self):
        """변형 시그널 연결 해제"""
        self.pos_x_spin.valueChanged.disconnect()
        self.pos_y_spin.valueChanged.disconnect()
        self.scale_x_spin.valueChanged.disconnect()
        self.scale_y_spin.valueChanged.disconnect()
        self.rotation_slider.valueChanged.disconnect()
        self.opacity_slider.valueChanged.disconnect()
        
    def connect_transform_signals(self):
        """변형 시그널 연결"""
        self.pos_x_spin.valueChanged.connect(lambda v: self.on_property_changed('position_x', v))
        self.pos_y_spin.valueChanged.connect(lambda v: self.on_property_changed('position_y', v))
        self.scale_x_spin.valueChanged.connect(lambda v: self.on_property_changed('scale_x', v))
        self.scale_y_spin.valueChanged.connect(lambda v: self.on_property_changed('scale_y', v))
        self.rotation_slider.valueChanged.connect(lambda v: self.on_property_changed('rotation', v))
        self.opacity_slider.valueChanged.connect(lambda v: self.on_property_changed('opacity', v/100.0))
        
    def disconnect_audio_signals(self):
        """오디오 시그널 연결 해제"""
        self.volume_slider.valueChanged.disconnect()
        self.fade_in_spin.valueChanged.disconnect()
        self.fade_out_spin.valueChanged.disconnect()
        
    def connect_audio_signals(self):
        """오디오 시그널 연결"""
        self.volume_slider.valueChanged.connect(lambda v: self.on_property_changed('volume', v/100.0))
        self.fade_in_spin.valueChanged.connect(lambda v: self.on_property_changed('fade_in', v))
        self.fade_out_spin.valueChanged.connect(lambda v: self.on_property_changed('fade_out', v))
        
    def disconnect_color_signals(self):
        """색상 시그널 연결 해제"""
        self.brightness_slider.valueChanged.disconnect()
        self.contrast_slider.valueChanged.disconnect()
        self.saturation_slider.valueChanged.disconnect()
        self.hue_slider.valueChanged.disconnect()
        
    def connect_color_signals(self):
        """색상 시그널 연결"""
        self.brightness_slider.valueChanged.connect(lambda v: self.on_property_changed('brightness', v/100.0))
        self.contrast_slider.valueChanged.connect(lambda v: self.on_property_changed('contrast', v/100.0))
        self.saturation_slider.valueChanged.connect(lambda v: self.on_property_changed('saturation', v/100.0))
        self.hue_slider.valueChanged.connect(lambda v: self.on_property_changed('hue', v))
        
    def on_property_changed(self, property_name, value):
        """속성 변경 이벤트"""
        # 선택된 모든 클립에 적용
        for clip in self.current_clips:
            if hasattr(clip, property_name):
                setattr(clip, property_name, value)
                clip.properties_changed.emit()
                
        # 비율 유지 옵션 처리
        if property_name in ['scale_x', 'scale_y'] and self.uniform_scale_check.isChecked():
            if property_name == 'scale_x':
                self.scale_y_spin.setValue(value)
            else:
                self.scale_x_spin.setValue(value)
                
        self.property_changed.emit(property_name, value)
        
    def remove_all_effects(self):
        """모든 효과 제거"""
        for clip in self.current_clips:
            clip.clear_effects()
            
        self.update_effects_group(self.current_clips[0] if self.current_clips else None) 