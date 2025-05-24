"""
BLOUcut 프리뷰 위젯
영상 미리보기 및 재생 컨트롤
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QSlider, QLabel, QFrame, QButtonGroup, QSpinBox,
                           QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QPixmap, QColor, QFont, QPen, QBrush

from ..core.media_analyzer import MediaAnalyzer

class PreviewWidget(QWidget):
    """프리뷰 위젯"""
    
    # 시그널
    frame_changed = pyqtSignal(int)  # 프레임 변경
    play_state_changed = pyqtSignal(bool)  # 재생 상태 변경
    
    def __init__(self):
        super().__init__()
        
        # 상태 변수
        self.current_frame = 0
        self.total_frames = 900  # 30초 (30fps)
        self.is_playing = False
        self.playback_speed = 1.0
        self.fps = 30
        
        # 표시 옵션
        self.show_safe_zone = False
        self.show_grid = False
        self.grid_type = "thirds"  # thirds, 4x4
        
        # 인/아웃 포인트
        self.in_point = None
        self.out_point = None
        self.loop_mode = False
        
        # 현재 미디어
        self.current_media_path = None
        self.current_media_info = None
        self.current_timeline_clips = []
        
        self.init_ui()
        
        # 재생 타이머
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.advance_frame)
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 프리뷰 화면
        self.preview_frame = PreviewFrame()
        self.preview_frame.setMinimumSize(640, 360)
        layout.addWidget(self.preview_frame, 1)
        
        # 컨트롤 패널
        controls_layout = self.create_controls()
        layout.addLayout(controls_layout)
        
        # 표시 옵션 패널
        display_layout = self.create_display_options()
        layout.addLayout(display_layout)
        
        self.apply_styles()
        
    def create_controls(self):
        """재생 컨트롤 생성"""
        layout = QHBoxLayout()
        
        # 재생 컨트롤
        self.play_button = QPushButton("▶")
        self.play_button.setMaximumWidth(40)
        self.play_button.clicked.connect(self.toggle_play)
        layout.addWidget(self.play_button)
        
        # 정지 버튼
        stop_button = QPushButton("⏹")
        stop_button.setMaximumWidth(40)
        stop_button.clicked.connect(self.stop)
        layout.addWidget(stop_button)
        
        # 이전/다음 프레임
        prev_frame_button = QPushButton("⏮")
        prev_frame_button.setMaximumWidth(40)
        prev_frame_button.clicked.connect(self.previous_frame)
        layout.addWidget(prev_frame_button)
        
        next_frame_button = QPushButton("⏭")
        next_frame_button.setMaximumWidth(40)
        next_frame_button.clicked.connect(self.next_frame)
        layout.addWidget(next_frame_button)
        
        layout.addWidget(QLabel("|"))
        
        # 인 포인트 설정
        in_point_button = QPushButton("I")
        in_point_button.setMaximumWidth(30)
        in_point_button.clicked.connect(self.set_in_point)
        layout.addWidget(in_point_button)
        
        # 아웃 포인트 설정
        out_point_button = QPushButton("O")
        out_point_button.setMaximumWidth(30)
        out_point_button.clicked.connect(self.set_out_point)
        layout.addWidget(out_point_button)
        
        # 루프 모드
        self.loop_checkbox = QCheckBox("Loop")
        self.loop_checkbox.toggled.connect(self.toggle_loop)
        layout.addWidget(self.loop_checkbox)
        
        layout.addWidget(QLabel("|"))
        
        # 재생 속도
        layout.addWidget(QLabel("속도:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(25, 200)  # 0.25x ~ 2.0x
        self.speed_slider.setValue(100)  # 1.0x
        self.speed_slider.setMaximumWidth(100)
        self.speed_slider.valueChanged.connect(self.change_speed)
        layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel("1.0x")
        self.speed_label.setMinimumWidth(35)
        layout.addWidget(self.speed_label)
        
        layout.addStretch()
        
        # 현재 시간 표시
        self.time_label = QLabel("00:00:00:00 / 00:30:00:00")
        layout.addWidget(self.time_label)
        
        return layout
        
    def create_display_options(self):
        """표시 옵션 생성"""
        layout = QHBoxLayout()
        
        # Safe Zone 토글
        self.safe_zone_button = QPushButton("Safe Zone")
        self.safe_zone_button.setCheckable(True)
        self.safe_zone_button.toggled.connect(self.toggle_safe_zone)
        layout.addWidget(self.safe_zone_button)
        
        # 격자 토글
        self.grid_button = QPushButton("Grid")
        self.grid_button.setCheckable(True)
        self.grid_button.toggled.connect(self.toggle_grid)
        layout.addWidget(self.grid_button)
        
        # 해상도 정보
        resolution_label = QLabel("1920x1080")
        layout.addWidget(resolution_label)
        
        layout.addStretch()
        
        # 재생 품질
        layout.addWidget(QLabel("품질:"))
        self.quality_combo = QButtonGroup()
        
        full_button = QPushButton("Full")
        full_button.setCheckable(True)
        full_button.setChecked(True)
        self.quality_combo.addButton(full_button, 0)
        layout.addWidget(full_button)
        
        half_button = QPushButton("Half")
        half_button.setCheckable(True)
        self.quality_combo.addButton(half_button, 1)
        layout.addWidget(half_button)
        
        quarter_button = QPushButton("1/4")
        quarter_button.setCheckable(True)
        self.quality_combo.addButton(quarter_button, 2)
        layout.addWidget(quarter_button)
        
        return layout
        
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QWidget {
                background-color: #3c3c3c;
                color: white;
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
            
            QPushButton:checked {
                background-color: #4CAF50;
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
        
    def toggle_play(self):
        """재생/정지 토글"""
        if self.is_playing:
            self.pause()
        else:
            self.play()
            
    def play(self):
        """재생 시작"""
        self.is_playing = True
        self.play_button.setText("⏸")
        
        # 타이머 간격 계산 (속도 고려)
        interval = int(1000 / (self.fps * self.playback_speed))
        self.play_timer.start(interval)
        
        self.play_state_changed.emit(True)
        
    def pause(self):
        """재생 일시정지"""
        self.is_playing = False
        self.play_button.setText("▶")
        self.play_timer.stop()
        
        self.play_state_changed.emit(False)
        
    def stop(self):
        """재생 정지"""
        self.pause()
        self.seek_to_frame(0)
        
    def advance_frame(self):
        """다음 프레임으로 이동"""
        next_frame = self.current_frame + 1
        
        # 아웃 포인트 체크
        if self.out_point is not None and next_frame >= self.out_point:
            if self.loop_mode and self.in_point is not None:
                next_frame = self.in_point
            else:
                self.pause()
                return
        elif next_frame >= self.total_frames:
            if self.loop_mode:
                next_frame = self.in_point if self.in_point is not None else 0
            else:
                self.pause()
                return
                
        self.seek_to_frame(next_frame)
        
    def previous_frame(self):
        """이전 프레임으로 이동"""
        new_frame = max(0, self.current_frame - 1)
        self.seek_to_frame(new_frame)
        
    def next_frame(self):
        """다음 프레임으로 이동"""
        new_frame = min(self.total_frames - 1, self.current_frame + 1)
        self.seek_to_frame(new_frame)
        
    def seek_to_frame(self, frame):
        """지정된 프레임으로 이동"""
        self.current_frame = max(0, min(frame, self.total_frames - 1))
        self.update_time_display()
        self.preview_frame.update()
        self.frame_changed.emit(self.current_frame)
        
    def set_in_point(self):
        """인 포인트 설정"""
        self.in_point = self.current_frame
        self.preview_frame.update()
        
    def set_out_point(self):
        """아웃 포인트 설정"""
        self.out_point = self.current_frame
        self.preview_frame.update()
        
    def toggle_loop(self, checked):
        """루프 모드 토글"""
        self.loop_mode = checked
        
    def change_speed(self, value):
        """재생 속도 변경"""
        self.playback_speed = value / 100.0
        self.speed_label.setText(f"{self.playback_speed:.1f}x")
        
        # 재생 중이면 타이머 재시작
        if self.is_playing:
            interval = int(1000 / (self.fps * self.playback_speed))
            self.play_timer.start(interval)
            
    def toggle_safe_zone(self, checked):
        """Safe Zone 표시 토글"""
        self.show_safe_zone = checked
        self.preview_frame.show_safe_zone = checked
        self.preview_frame.update()
        
    def toggle_grid(self, checked):
        """격자 표시 토글"""
        self.show_grid = checked
        self.preview_frame.show_grid = checked
        self.preview_frame.update()
        
    def update_time_display(self):
        """시간 표시 업데이트"""
        # 현재 시간
        current_seconds = self.current_frame / self.fps
        current_hours = int(current_seconds // 3600)
        current_minutes = int((current_seconds % 3600) // 60)
        current_secs = int(current_seconds % 60)
        current_frames = int(self.current_frame % self.fps)
        
        # 전체 시간
        total_seconds = self.total_frames / self.fps
        total_hours = int(total_seconds // 3600)
        total_minutes = int((total_seconds % 3600) // 60)
        total_secs = int(total_seconds % 60)
        
        time_str = f"{current_hours:02d}:{current_minutes:02d}:{current_secs:02d}:{current_frames:02d} / {total_hours:02d}:{total_minutes:02d}:{total_secs:02d}:00"
        self.time_label.setText(time_str)
        
    def load_media(self, media_path):
        """미디어 파일 로드"""
        if not os.path.exists(media_path):
            return False
            
        try:
            # 미디어 정보 분석
            self.current_media_info = MediaAnalyzer.get_media_info(media_path)
            self.current_media_path = media_path
            
            # 프레임 정보 업데이트
            self.total_frames = self.current_media_info['duration_frames']
            self.fps = self.current_media_info['fps']
            
            # 프리뷰 프레임에 미디어 설정
            self.preview_frame.set_media(media_path, self.current_media_info)
            
            # 시간 표시 업데이트
            self.update_time_display()
            
            return True
            
        except Exception as e:
            print(f"미디어 로드 실패: {e}")
            return False
            
    def set_timeline_clips(self, clips):
        """타임라인 클립 설정"""
        self.current_timeline_clips = clips
        self.preview_frame.set_timeline_clips(clips)
        
    def render_frame_at_position(self, frame_position):
        """특정 프레임 위치의 이미지 렌더링"""
        self.current_frame = frame_position
        
        # 해당 프레임에서 활성 클립 찾기
        active_clips = []
        for clip in self.current_timeline_clips:
            if clip.start_frame <= frame_position < clip.start_frame + clip.duration:
                active_clips.append(clip)
                
        if active_clips:
            # 가장 위쪽 트랙의 클립 사용 (간단한 구현)
            top_clip = min(active_clips, key=lambda c: c.track)
            
            # 클립 내 상대 프레임 계산
            relative_frame = frame_position - top_clip.start_frame
            
            # 미디어 로드 및 표시
            if top_clip.media_path != self.current_media_path:
                self.load_media(top_clip.media_path)
                
            # 프리뷰 프레임 업데이트
            self.preview_frame.set_current_frame(relative_frame)
        else:
            # 활성 클립이 없으면 빈 화면
            self.preview_frame.clear_frame()
            
        self.update_time_display()
        self.preview_frame.update()
        
    def keyPressEvent(self, event):
        """키보드 이벤트"""
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play()
        elif event.key() == Qt.Key.Key_I:
            self.set_in_point()
        elif event.key() == Qt.Key.Key_O:
            self.set_out_point()
        elif event.key() == Qt.Key.Key_Left:
            self.previous_frame()
        elif event.key() == Qt.Key.Key_Right:
            self.next_frame()
        elif event.key() == Qt.Key.Key_J:
            # J - 역방향 재생 (간단 구현)
            self.previous_frame()
        elif event.key() == Qt.Key.Key_K:
            # K - 정지
            self.pause()
        elif event.key() == Qt.Key.Key_L:
            # L - 정방향 재생
            self.next_frame()
        else:
            super().keyPressEvent(event)

class PreviewFrame(QFrame):
    """프리뷰 프레임 (실제 영상이 표시되는 영역)"""
    
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.Box)
        self.setMinimumSize(640, 360)
        
        # 표시 옵션
        self.show_safe_zone = False
        self.show_grid = False
        
        # 인/아웃 포인트 (부모에서 전달받음)
        self.in_point = None
        self.out_point = None
        
        # 미디어 정보
        self.current_media_path = None
        self.current_media_info = None
        self.current_frame = 0
        self.timeline_clips = []
        self.thumbnail_cache = {}
        
    def paintEvent(self, event):
        """페인트 이벤트"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 배경 (비디오 영역)
        video_rect = self.get_video_rect()
        painter.fillRect(video_rect, QColor(20, 20, 20))
        
        # 비디오 프레임
        if self.current_media_path:
            self.draw_media_frame(painter, video_rect)
        else:
            self.draw_dummy_video(painter, video_rect)
        
        # Safe Zone 표시
        if self.show_safe_zone:
            self.draw_safe_zone(painter, video_rect)
            
        # 격자 표시
        if self.show_grid:
            self.draw_grid(painter, video_rect)
            
    def get_video_rect(self):
        """비디오 표시 영역 계산 (16:9 비율 유지)"""
        widget_rect = self.rect()
        aspect_ratio = 16.0 / 9.0
        
        # 위젯 비율 계산
        widget_aspect = widget_rect.width() / widget_rect.height()
        
        if widget_aspect > aspect_ratio:
            # 위젯이 더 넓음 - 높이 기준
            video_height = widget_rect.height() - 20
            video_width = int(video_height * aspect_ratio)
            x = (widget_rect.width() - video_width) // 2
            y = 10
        else:
            # 위젯이 더 높음 - 너비 기준
            video_width = widget_rect.width() - 20
            video_height = int(video_width / aspect_ratio)
            x = 10
            y = (widget_rect.height() - video_height) // 2
            
        return QRect(x, y, video_width, video_height)
        
    def draw_dummy_video(self, painter, rect):
        """더미 비디오 프레임 그리기"""
        # 그라데이션 배경
        painter.fillRect(rect, QColor(60, 60, 60))
        
        # 중앙에 플레이스홀더 텍스트
        painter.setPen(QPen(QColor(200, 200, 200)))
        font = QFont("Arial", 16)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "영상 미리보기")
        
        # 프레임 번호 표시
        frame_text = f"Frame: {getattr(self.parent(), 'current_frame', 0)}"
        painter.drawText(rect.adjusted(10, 10, -10, -10), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, frame_text)
        
    def draw_safe_zone(self, painter, rect):
        """Safe Zone 그리기"""
        painter.setPen(QPen(QColor(255, 255, 0, 150), 1))
        
        # TV Safe Zone (90%)
        margin_x = int(rect.width() * 0.05)
        margin_y = int(rect.height() * 0.05)
        tv_safe = rect.adjusted(margin_x, margin_y, -margin_x, -margin_y)
        painter.drawRect(tv_safe)
        
        # Mobile Safe Zone (80%)
        margin_x = int(rect.width() * 0.1)
        margin_y = int(rect.height() * 0.1)
        mobile_safe = rect.adjusted(margin_x, margin_y, -margin_x, -margin_y)
        painter.setPen(QPen(QColor(255, 0, 255, 150), 1))
        painter.drawRect(mobile_safe)
        
    def draw_grid(self, painter, rect):
        """격자 그리기"""
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        
        # Rule of Thirds
        third_x1 = rect.x() + rect.width() // 3
        third_x2 = rect.x() + 2 * rect.width() // 3
        third_y1 = rect.y() + rect.height() // 3
        third_y2 = rect.y() + 2 * rect.height() // 3
        
        # 세로선
        painter.drawLine(third_x1, rect.y(), third_x1, rect.y() + rect.height())
        painter.drawLine(third_x2, rect.y(), third_x2, rect.y() + rect.height())
        
        # 가로선
        painter.drawLine(rect.x(), third_y1, rect.x() + rect.width(), third_y1)
        painter.drawLine(rect.x(), third_y2, rect.x() + rect.width(), third_y2)
        
    def set_media(self, media_path, media_info):
        """미디어 설정"""
        self.current_media_path = media_path
        self.current_media_info = media_info
        self.current_frame = 0
        
    def set_timeline_clips(self, clips):
        """타임라인 클립 설정"""
        self.timeline_clips = clips
        
    def set_current_frame(self, frame):
        """현재 프레임 설정"""
        self.current_frame = frame
        
    def clear_frame(self):
        """프레임 지우기"""
        self.current_media_path = None
        self.current_media_info = None
        
    def draw_media_frame(self, painter, rect):
        """실제 미디어 프레임 그리기"""
        if not self.current_media_info:
            self.draw_dummy_video(painter, rect)
            return
            
        media_type = self.current_media_info['media_type']
        
        if media_type == 'image':
            self.draw_image_frame(painter, rect)
        elif media_type == 'video':
            self.draw_video_frame(painter, rect)
        elif media_type == 'audio':
            self.draw_audio_frame(painter, rect)
        else:
            self.draw_dummy_video(painter, rect)
            
    def draw_image_frame(self, painter, rect):
        """이미지 프레임 그리기"""
        try:
            # 이미지 로드
            pixmap = QPixmap(self.current_media_path)
            if not pixmap.isNull():
                # 비율 유지하며 크기 조정
                scaled_pixmap = pixmap.scaled(
                    rect.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # 중앙 정렬로 그리기
                x = rect.x() + (rect.width() - scaled_pixmap.width()) // 2
                y = rect.y() + (rect.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
            else:
                self.draw_placeholder(painter, rect, "이미지 로드 실패")
        except Exception as e:
            self.draw_placeholder(painter, rect, f"이미지 오류: {str(e)}")
            
    def draw_video_frame(self, painter, rect):
        """비디오 프레임 그리기 (썸네일 기반)"""
        try:
            # 썸네일 생성 시도
            time_seconds = self.current_frame / self.current_media_info.get('fps', 30)
            thumbnail_path = MediaAnalyzer.get_thumbnail_path(self.current_media_path, time_seconds)
            
            if thumbnail_path and os.path.exists(thumbnail_path):
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    # 비율 유지하며 크기 조정
                    scaled_pixmap = pixmap.scaled(
                        rect.size(), 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    
                    # 중앙 정렬로 그리기
                    x = rect.x() + (rect.width() - scaled_pixmap.width()) // 2
                    y = rect.y() + (rect.height() - scaled_pixmap.height()) // 2
                    painter.drawPixmap(x, y, scaled_pixmap)
                    return
                    
            # 썸네일 로드 실패시 플레이스홀더
            self.draw_placeholder(painter, rect, f"비디오 프레임 {self.current_frame}")
            
        except Exception as e:
            self.draw_placeholder(painter, rect, f"비디오 오류: {str(e)}")
            
    def draw_audio_frame(self, painter, rect):
        """오디오 파형 그리기"""
        # 오디오 파형 시각화 (간단한 구현)
        painter.fillRect(rect, QColor(40, 40, 40))
        
        # 중앙에 오디오 아이콘
        painter.setPen(QPen(QColor(100, 200, 100), 2))
        font = QFont("Arial", 48)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🎵")
        
        # 파일 이름 표시
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.setPen(QPen(QColor(200, 200, 200)))
        file_name = os.path.basename(self.current_media_path)
        painter.drawText(rect.adjusted(10, -30, -10, -10), 
                        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, 
                        file_name)
                        
    def draw_placeholder(self, painter, rect, text="미디어 미리보기"):
        """플레이스홀더 그리기"""
        # 그라데이션 배경
        painter.fillRect(rect, QColor(60, 60, 60))
        
        # 중앙에 텍스트
        painter.setPen(QPen(QColor(200, 200, 200)))
        font = QFont("Arial", 16)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        
        # 미디어 정보 표시
        if self.current_media_info:
            info_text = f"{self.current_media_info['width']}x{self.current_media_info['height']} @ {self.current_media_info['fps']:.1f}fps"
            font = QFont("Arial", 10)
            painter.setFont(font)
            painter.drawText(rect.adjusted(10, 10, -10, -10), 
                           Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, 
                           info_text) 