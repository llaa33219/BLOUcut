"""
BLOUcut 속성 패널
선택된 클립의 속성을 편집할 수 있는 패널
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
                           QComboBox, QPushButton, QGroupBox, QLineEdit,
                           QColorDialog, QFileDialog, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QIcon

class PropertiesPanel(QWidget):
    """속성 패널"""
    
    # 시그널
    property_changed = pyqtSignal(str, object)  # 속성명, 값
    keyframe_added = pyqtSignal(str, int, object)  # 속성명, 프레임, 값
    keyframe_removed = pyqtSignal(str, int)  # 속성명, 프레임
    
    def __init__(self):
        super().__init__()
        self.current_clip = None
        self.current_frame = 0  # 현재 타임라인 프레임
        self.keyframe_buttons = {}  # 키프레임 버튼들 저장
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 현재 프레임 표시
        frame_layout = QHBoxLayout()
        frame_layout.addWidget(QLabel("현재 프레임:"))
        self.current_frame_label = QLabel("0")
        self.current_frame_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        frame_layout.addWidget(self.current_frame_label)
        frame_layout.addStretch()
        layout.addLayout(frame_layout)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 클립 정보
        self.clip_info_group = self.create_clip_info_group()
        scroll_layout.addWidget(self.clip_info_group)
        
        # 변형 속성
        self.transform_group = self.create_transform_group()
        scroll_layout.addWidget(self.transform_group)
        
        # 오디오 속성
        self.audio_group = self.create_audio_group()
        scroll_layout.addWidget(self.audio_group)
        
        # 비디오 속성
        self.video_group = self.create_video_group()
        scroll_layout.addWidget(self.video_group)
        
        # 자막 속성
        self.subtitle_group = self.create_subtitle_group()
        scroll_layout.addWidget(self.subtitle_group)
        
        # 효과 속성
        self.effects_group = self.create_effects_group()
        scroll_layout.addWidget(self.effects_group)
        
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.apply_styles()
        
    def create_clip_info_group(self):
        """클립 정보 그룹"""
        group = QGroupBox("클립 정보")
        layout = QVBoxLayout(group)
        
        # 클립 이름
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("이름:"))
        self.clip_name_edit = QLineEdit()
        self.clip_name_edit.textChanged.connect(lambda text: self.emit_property_change("name", text))
        name_layout.addWidget(self.clip_name_edit)
        layout.addLayout(name_layout)
        
        # 시작 시간
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("시작:"))
        self.start_time_spin = QDoubleSpinBox()
        self.start_time_spin.setRange(0, 3600)
        self.start_time_spin.setSuffix("초")
        self.start_time_spin.valueChanged.connect(lambda val: self.emit_property_change("start_time", val))
        start_layout.addWidget(self.start_time_spin)
        layout.addLayout(start_layout)
        
        # 지속 시간
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("길이:"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 3600)
        self.duration_spin.setSuffix("초")
        self.duration_spin.valueChanged.connect(lambda val: self.emit_property_change("duration", val))
        duration_layout.addWidget(self.duration_spin)
        layout.addLayout(duration_layout)
        
        return group
        
    def create_transform_group(self):
        """변형 속성 그룹"""
        group = QGroupBox("변형")
        layout = QVBoxLayout(group)
        
        # 위치 X
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X:"))
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-9999, 9999)
        self.x_spin.valueChanged.connect(lambda val: self.emit_property_change("x", val))
        x_layout.addWidget(self.x_spin)
        
        # 키프레임 버튼
        keyframe_btn_x = self.create_keyframe_button('position_x')
        x_layout.addWidget(keyframe_btn_x)
        
        layout.addLayout(x_layout)
        
        # 위치 Y
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y:"))
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-9999, 9999)
        self.y_spin.valueChanged.connect(lambda val: self.emit_property_change("y", val))
        y_layout.addWidget(self.y_spin)
        
        # 키프레임 버튼
        keyframe_btn_y = self.create_keyframe_button('position_y')
        y_layout.addWidget(keyframe_btn_y)
        
        layout.addLayout(y_layout)
        
        # 크기 조절
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("크기:"))
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(10, 500)  # 10% ~ 500%
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        scale_layout.addWidget(self.scale_slider)
        
        self.scale_label = QLabel("100%")
        scale_layout.addWidget(self.scale_label)
        
        # 스케일 키프레임 버튼들
        keyframe_btn_scale = self.create_keyframe_button('scale_x')  # 스케일은 X,Y 동시 제어
        scale_layout.addWidget(keyframe_btn_scale)
        
        layout.addLayout(scale_layout)
        
        # 회전
        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("회전:"))
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(-360, 360)
        self.rotation_spin.setSuffix("°")
        self.rotation_spin.valueChanged.connect(lambda val: self.emit_property_change("rotation", val))
        rotation_layout.addWidget(self.rotation_spin)
        
        # 키프레임 버튼
        keyframe_btn_rotation = self.create_keyframe_button('rotation')
        rotation_layout.addWidget(keyframe_btn_rotation)
        
        layout.addLayout(rotation_layout)
        
        # 불투명도
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("불투명도:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("100%")
        opacity_layout.addWidget(self.opacity_label)
        
        # 키프레임 버튼
        keyframe_btn_opacity = self.create_keyframe_button('opacity')
        opacity_layout.addWidget(keyframe_btn_opacity)
        
        layout.addLayout(opacity_layout)
        
        return group
        
    def create_audio_group(self):
        """오디오 속성 그룹"""
        group = QGroupBox("오디오")
        layout = QVBoxLayout(group)
        
        # 볼륨
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("볼륨:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 200)  # 0% ~ 200%
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        volume_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("100%")
        volume_layout.addWidget(self.volume_label)
        layout.addLayout(volume_layout)
        
        # 음소거
        self.mute_checkbox = QCheckBox("음소거")
        self.mute_checkbox.toggled.connect(lambda checked: self.emit_property_change("muted", checked))
        layout.addWidget(self.mute_checkbox)
        
        # 페이드 인
        fade_in_layout = QHBoxLayout()
        fade_in_layout.addWidget(QLabel("페이드 인:"))
        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setRange(0, 10)
        self.fade_in_spin.setSuffix("초")
        self.fade_in_spin.valueChanged.connect(lambda val: self.emit_property_change("fade_in", val))
        fade_in_layout.addWidget(self.fade_in_spin)
        layout.addLayout(fade_in_layout)
        
        # 페이드 아웃
        fade_out_layout = QHBoxLayout()
        fade_out_layout.addWidget(QLabel("페이드 아웃:"))
        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setRange(0, 10)
        self.fade_out_spin.setSuffix("초")
        self.fade_out_spin.valueChanged.connect(lambda val: self.emit_property_change("fade_out", val))
        fade_out_layout.addWidget(self.fade_out_spin)
        layout.addLayout(fade_out_layout)
        
        return group
        
    def create_video_group(self):
        """비디오 속성 그룹"""
        group = QGroupBox("비디오")
        layout = QVBoxLayout(group)
        
        # 속도
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("속도:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(25, 400)  # 0.25x ~ 4.0x
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel("1.0x")
        speed_layout.addWidget(self.speed_label)
        layout.addLayout(speed_layout)
        
        # 뒤집기
        flip_layout = QHBoxLayout()
        self.flip_h_checkbox = QCheckBox("좌우 뒤집기")
        self.flip_h_checkbox.toggled.connect(lambda checked: self.emit_property_change("flip_horizontal", checked))
        flip_layout.addWidget(self.flip_h_checkbox)
        
        self.flip_v_checkbox = QCheckBox("상하 뒤집기")
        self.flip_v_checkbox.toggled.connect(lambda checked: self.emit_property_change("flip_vertical", checked))
        flip_layout.addWidget(self.flip_v_checkbox)
        layout.addLayout(flip_layout)
        
        # 색상 조정
        color_layout = QVBoxLayout()
        
        # 밝기
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("밝기:"))
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(lambda val: self.emit_property_change("brightness", val))
        brightness_layout.addWidget(self.brightness_slider)
        color_layout.addLayout(brightness_layout)
        
        # 대비
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("대비:"))
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(-100, 100)
        self.contrast_slider.setValue(0)
        self.contrast_slider.valueChanged.connect(lambda val: self.emit_property_change("contrast", val))
        contrast_layout.addWidget(self.contrast_slider)
        color_layout.addLayout(contrast_layout)
        
        # 채도
        saturation_layout = QHBoxLayout()
        saturation_layout.addWidget(QLabel("채도:"))
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(-100, 100)
        self.saturation_slider.setValue(0)
        self.saturation_slider.valueChanged.connect(lambda val: self.emit_property_change("saturation", val))
        saturation_layout.addWidget(self.saturation_slider)
        color_layout.addLayout(saturation_layout)
        
        layout.addLayout(color_layout)
        
        return group
        
    def create_subtitle_group(self):
        """자막 속성 그룹"""
        group = QGroupBox("자막")
        layout = QVBoxLayout(group)
        
        # 자막 활성화
        self.subtitle_enabled = QCheckBox("자막 표시")
        self.subtitle_enabled.toggled.connect(lambda checked: self.emit_property_change("subtitle_enabled", checked))
        layout.addWidget(self.subtitle_enabled)
        
        # 자막 텍스트
        text_layout = QVBoxLayout()
        text_layout.addWidget(QLabel("텍스트:"))
        self.subtitle_text = QLineEdit()
        self.subtitle_text.textChanged.connect(lambda text: self.emit_property_change("subtitle_text", text))
        text_layout.addWidget(self.subtitle_text)
        layout.addLayout(text_layout)
        
        # 폰트 크기
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("크기:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 128)
        self.font_size_spin.setValue(24)
        self.font_size_spin.valueChanged.connect(lambda val: self.emit_property_change("font_size", val))
        font_size_layout.addWidget(self.font_size_spin)
        layout.addLayout(font_size_layout)
        
        # 폰트 색상
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("색상:"))
        self.font_color_button = QPushButton("선택")
        self.font_color_button.clicked.connect(self.choose_font_color)
        self.font_color = QColor(255, 255, 255)  # 기본 흰색
        color_layout.addWidget(self.font_color_button)
        layout.addLayout(color_layout)
        
        # 자막 위치
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("위치:"))
        self.subtitle_position = QComboBox()
        self.subtitle_position.addItems(["하단", "중앙", "상단"])
        self.subtitle_position.currentTextChanged.connect(lambda text: self.emit_property_change("subtitle_position", text))
        position_layout.addWidget(self.subtitle_position)
        layout.addLayout(position_layout)
        
        return group
        
    def create_effects_group(self):
        """효과 속성 그룹"""
        group = QGroupBox("효과")
        layout = QVBoxLayout(group)
        
        # 블러 효과
        blur_layout = QHBoxLayout()
        blur_layout.addWidget(QLabel("블러:"))
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(0, 50)
        self.blur_slider.setValue(0)
        self.blur_slider.valueChanged.connect(lambda val: self.emit_property_change("blur", val))
        blur_layout.addWidget(self.blur_slider)
        layout.addLayout(blur_layout)
        
        # 크로마키
        chroma_layout = QVBoxLayout()
        self.chroma_enabled = QCheckBox("크로마키")
        self.chroma_enabled.toggled.connect(lambda checked: self.emit_property_change("chroma_enabled", checked))
        chroma_layout.addWidget(self.chroma_enabled)
        
        chroma_color_layout = QHBoxLayout()
        chroma_color_layout.addWidget(QLabel("키 색상:"))
        self.chroma_color_button = QPushButton("선택")
        self.chroma_color_button.clicked.connect(self.choose_chroma_color)
        self.chroma_color = QColor(0, 255, 0)  # 기본 녹색
        chroma_color_layout.addWidget(self.chroma_color_button)
        chroma_layout.addLayout(chroma_color_layout)
        layout.addLayout(chroma_layout)
        
        # 필터 프리셋
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("필터:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["없음", "세피아", "흑백", "비네팅", "영화"])
        self.filter_combo.currentTextChanged.connect(lambda text: self.emit_property_change("filter", text))
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)
        
        return group
        
    def create_keyframes_group(self):
        """키프레임 관리 그룹"""
        group = QGroupBox("키프레임")
        layout = QVBoxLayout(group)
        
        # 키프레임 버튼들
        self.keyframe_buttons = {}
        self.keyframe_buttons['position_x'] = self.create_keyframe_button('position_x')
        self.keyframe_buttons['position_y'] = self.create_keyframe_button('position_y')
        self.keyframe_buttons['scale_x'] = self.create_keyframe_button('scale_x')
        self.keyframe_buttons['scale_y'] = self.create_keyframe_button('scale_y')
        self.keyframe_buttons['rotation'] = self.create_keyframe_button('rotation')
        self.keyframe_buttons['opacity'] = self.create_keyframe_button('opacity')
        self.keyframe_buttons['volume'] = self.create_keyframe_button('volume')
        
        for property_name, button in self.keyframe_buttons.items():
            layout.addWidget(button)
        
        return group
        
    def create_keyframe_button(self, property_name):
        """키프레임 버튼 생성"""
        button = QPushButton()
        button.setFixedSize(20, 20)
        button.setCheckable(True)
        button.setToolTip(f"{property_name} 키프레임")
        
        # 초기 상태는 키프레임 없음
        self.update_keyframe_button(button, property_name, False)
        
        # 클릭 이벤트
        button.clicked.connect(lambda: self.toggle_keyframe(property_name))
        
        self.keyframe_buttons[property_name] = button
        return button
        
    def update_keyframe_button(self, button, property_name, has_keyframe):
        """키프레임 버튼 상태 업데이트"""
        if has_keyframe:
            button.setText("◆")  # 다이아몬드 (키프레임 있음)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #FFA500;
                    color: white;
                    border: 1px solid #FF8C00;
                    border-radius: 10px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #FF8C00;
                }
            """)
        else:
            button.setText("◇")  # 빈 다이아몬드 (키프레임 없음)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: #CCC;
                    border: 1px solid #777;
                    border-radius: 10px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
            
    def toggle_keyframe(self, property_name):
        """키프레임 토글"""
        if not self.current_clip:
            return
            
        # 현재 프레임에서의 키프레임 존재 여부 확인
        has_keyframe = self.current_clip.keyframes.has_keyframes_at_frame(self.current_frame)
        properties_at_frame = self.current_clip.keyframes.get_properties_with_keyframes_at_frame(self.current_frame)
        
        if property_name in properties_at_frame:
            # 키프레임 제거
            self.current_clip.remove_keyframe(property_name, self.current_frame)
            self.keyframe_removed.emit(property_name, self.current_frame)
            print(f"[키프레임 제거] {property_name} @ 프레임 {self.current_frame}")
        else:
            # 키프레임 추가 - 현재 속성 값 사용
            current_value = self.get_current_property_value(property_name)
            if current_value is not None:
                from ..core.keyframe import InterpolationType
                self.current_clip.add_keyframe(property_name, self.current_frame, current_value, InterpolationType.LINEAR)
                self.keyframe_added.emit(property_name, self.current_frame, current_value)
                print(f"[키프레임 추가] {property_name} @ 프레임 {self.current_frame}: {current_value}")
                
        # 버튼 상태 업데이트
        self.update_keyframe_buttons()
        
    def get_current_property_value(self, property_name):
        """현재 속성 값 가져오기"""
        if not self.current_clip:
            return None
            
        # 속성 매핑
        property_mapping = {
            'position_x': lambda: self.x_spin.value(),
            'position_y': lambda: self.y_spin.value(),
            'scale_x': lambda: self.scale_slider.value() / 100.0,
            'scale_y': lambda: self.scale_slider.value() / 100.0,
            'rotation': lambda: self.rotation_spin.value(),
            'opacity': lambda: self.opacity_slider.value() / 100.0,
            'volume': lambda: self.volume_slider.value() / 100.0,
        }
        
        if property_name in property_mapping:
            try:
                return property_mapping[property_name]()
            except:
                return None
        else:
            # 직접 클립 속성에서 가져오기
            return getattr(self.current_clip, property_name, None)
            
    def update_keyframe_buttons(self):
        """모든 키프레임 버튼 상태 업데이트"""
        if not self.current_clip:
            return
            
        for property_name, button in self.keyframe_buttons.items():
            properties_at_frame = self.current_clip.keyframes.get_properties_with_keyframes_at_frame(self.current_frame)
            has_keyframe = property_name in properties_at_frame
            self.update_keyframe_button(button, property_name, has_keyframe)
        
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
                margin: 10px 0;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
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
            
            QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #555;
                border: 1px solid #777;
                border-radius: 3px;
                padding: 5px;
            }
            
            QComboBox {
                background-color: #555;
                border: 1px solid #777;
                border-radius: 3px;
                padding: 5px;
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
        """)
        
    def set_clip(self, clip):
        """클립 설정"""
        print(f"[속성패널] set_clip 호출: {clip.name if clip else 'None'}")
        if clip:
            print(f"[속성패널] 클립 길이: {clip.duration}")
        
        self.current_clip = clip
        
        if clip is None:
            self.clear_properties()
            return
            
        # 개별 위젯의 시그널 일시 차단
        widgets_to_block = [
            self.clip_name_edit, self.start_time_spin, self.duration_spin,
            self.x_spin, self.y_spin, self.scale_slider, self.rotation_spin, self.opacity_slider,
            self.volume_slider, self.mute_checkbox, self.speed_slider,
            self.subtitle_enabled, self.subtitle_text
        ]
        
        # 각 위젯의 시그널 차단 상태 저장
        old_blocked_states = {}
        for widget in widgets_to_block:
            old_blocked_states[widget] = widget.signalsBlocked()
            widget.blockSignals(True)
        
        try:
            # 클립 정보 업데이트
            self.clip_name_edit.setText(clip.name)
            self.start_time_spin.setValue(clip.start_frame / 30.0)  # 30fps 기준
            self.duration_spin.setValue(clip.duration / 30.0)
            
            # 변형 속성 (기본값 설정)
            self.x_spin.setValue(getattr(clip, 'x', 0))
            self.y_spin.setValue(getattr(clip, 'y', 0))
            self.scale_slider.setValue(int(getattr(clip, 'scale', 100)))
            self.rotation_spin.setValue(int(getattr(clip, 'rotation', 0)))
            self.opacity_slider.setValue(int(getattr(clip, 'opacity', 100)))
            
            # 오디오 속성
            self.volume_slider.setValue(int(getattr(clip, 'volume', 100)))
            self.mute_checkbox.setChecked(getattr(clip, 'muted', False))
            
            # 비디오 속성
            self.speed_slider.setValue(int(getattr(clip, 'speed', 100)))
            
            # 자막 속성
            self.subtitle_enabled.setChecked(getattr(clip, 'subtitle_enabled', False))
            self.subtitle_text.setText(getattr(clip, 'subtitle_text', ''))
            
            # 업데이트 레이블들
            self.update_labels()
            
        finally:
            # 각 위젯의 시그널 복원
            for widget in widgets_to_block:
                widget.blockSignals(old_blocked_states[widget])
            
        print(f"[속성패널] set_clip 완료: 길이 {clip.duration}")
        
    def clear_properties(self):
        """속성 초기화"""
        self.clip_name_edit.clear()
        self.start_time_spin.setValue(0)
        self.duration_spin.setValue(0)
        
        self.x_spin.setValue(0)
        self.y_spin.setValue(0)
        self.scale_slider.setValue(100)
        self.rotation_spin.setValue(0)
        self.opacity_slider.setValue(100)
        
        self.volume_slider.setValue(100)
        self.mute_checkbox.setChecked(False)
        
        self.speed_slider.setValue(100)
        self.flip_h_checkbox.setChecked(False)
        self.flip_v_checkbox.setChecked(False)
        
        self.subtitle_enabled.setChecked(False)
        self.subtitle_text.clear()
        
        self.update_labels()
        
    def update_labels(self):
        """라벨 업데이트"""
        self.scale_label.setText(f"{self.scale_slider.value()}%")
        self.opacity_label.setText(f"{self.opacity_slider.value()}%")
        self.volume_label.setText(f"{self.volume_slider.value()}%")
        self.speed_label.setText(f"{self.speed_slider.value() / 100.0:.1f}x")
        
    def on_scale_changed(self, value):
        """크기 변경"""
        self.scale_label.setText(f"{value}%")
        self.emit_property_change("scale", value)
        
    def on_opacity_changed(self, value):
        """불투명도 변경"""
        self.opacity_label.setText(f"{value}%")
        self.emit_property_change("opacity", value)
        
    def on_volume_changed(self, value):
        """볼륨 변경"""
        self.volume_label.setText(f"{value}%")
        self.emit_property_change("volume", value)
        
    def on_speed_changed(self, value):
        """속도 변경"""
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")
        self.emit_property_change("speed", speed)
        
    def choose_font_color(self):
        """폰트 색상 선택"""
        color = QColorDialog.getColor(self.font_color, self)
        if color.isValid():
            self.font_color = color
            self.emit_property_change("font_color", color)
            
    def choose_chroma_color(self):
        """크로마키 색상 선택"""
        color = QColorDialog.getColor(self.chroma_color, self)
        if color.isValid():
            self.chroma_color = color
            self.emit_property_change("chroma_color", color)
            
    def emit_property_change(self, property_name, value):
        """속성 변경 시그널 방출"""
        if self.current_clip:
            self.property_changed.emit(property_name, value)
        
    def set_current_frame(self, frame):
        """현재 프레임 설정"""
        self.current_frame = frame
        self.current_frame_label.setText(str(frame))
        
        # 키프레임 버튼 상태 업데이트
        self.update_keyframe_buttons()
        
        # 키프레임이 있는 속성들의 값 업데이트
        if self.current_clip:
            self.update_animated_values()
            
    def update_animated_values(self):
        """키프레임이 있는 속성들의 값을 현재 프레임에 맞게 업데이트"""
        if not self.current_clip:
            return
            
        # 애니메이션된 속성들 가져오기
        animated_properties = self.current_clip.keyframes.get_animated_properties()
        
        for property_name in animated_properties:
            # 현재 프레임에서의 값 계산
            animated_value = self.current_clip.get_animated_value(property_name, self.current_frame)
            
            if animated_value is not None:
                # UI 컨트롤 업데이트 (시그널 차단하여 무한 루프 방지)
                self.update_ui_control(property_name, animated_value, block_signals=True)
                
    def update_ui_control(self, property_name, value, block_signals=False):
        """UI 컨트롤 값 업데이트"""
        if property_name == 'position_x':
            if hasattr(self, 'x_spin'):
                if block_signals:
                    self.x_spin.blockSignals(True)
                self.x_spin.setValue(int(value))
                if block_signals:
                    self.x_spin.blockSignals(False)
                    
        elif property_name == 'position_y':
            if hasattr(self, 'y_spin'):
                if block_signals:
                    self.y_spin.blockSignals(True)
                self.y_spin.setValue(int(value))
                if block_signals:
                    self.y_spin.blockSignals(False)
                    
        elif property_name in ['scale_x', 'scale_y']:
            if hasattr(self, 'scale_slider'):
                if block_signals:
                    self.scale_slider.blockSignals(True)
                self.scale_slider.setValue(int(value * 100))
                self.scale_label.setText(f"{int(value * 100)}%")
                if block_signals:
                    self.scale_slider.blockSignals(False)
                    
        elif property_name == 'rotation':
            if hasattr(self, 'rotation_spin'):
                if block_signals:
                    self.rotation_spin.blockSignals(True)
                self.rotation_spin.setValue(int(value))
                if block_signals:
                    self.rotation_spin.blockSignals(False)
                    
        elif property_name == 'opacity':
            if hasattr(self, 'opacity_slider'):
                if block_signals:
                    self.opacity_slider.blockSignals(True)
                self.opacity_slider.setValue(int(value * 100))
                self.opacity_label.setText(f"{int(value * 100)}%")
                if block_signals:
                    self.opacity_slider.blockSignals(False)
                    
        elif property_name == 'volume':
            if hasattr(self, 'volume_slider'):
                if block_signals:
                    self.volume_slider.blockSignals(True)
                self.volume_slider.setValue(int(value * 100))
                self.volume_label.setText(f"{int(value * 100)}%")
                if block_signals:
                    self.volume_slider.blockSignals(False) 