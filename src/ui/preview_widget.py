"""
BLOUcut 프리뷰 위젯
영상 미리보기 및 재생 컨트롤
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QSlider, QLabel, QFrame, QButtonGroup, QSpinBox,
                           QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QCoreApplication
from PyQt6.QtGui import QPainter, QPixmap, QColor, QFont, QPen, QBrush

from ..core.media_analyzer import MediaAnalyzer
from ..audio.audio_engine import AudioEngine
from ..audio.pygame_audio_engine import PygameAudioEngine

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
        self.preview_mode = "single"  # "single" 또는 "timeline"
        
        # 안전장치용 플래그들
        self._user_seeking = False
        self._last_clip_count = 0
        self._last_timeline_length = 0.0
        
        # 오디오 엔진 (pygame 버전 우선 사용)
        try:
            self.audio_engine = PygameAudioEngine()
            print("Pygame 오디오 엔진 사용")
        except Exception as e:
            print(f"Pygame 오디오 엔진 실패, PyQt6 사용: {e}")
            self.audio_engine = AudioEngine()
        
        # 시그널 연결
        self.audio_engine.position_changed.connect(self._on_audio_position_changed)
        self.audio_engine.state_changed.connect(self._on_audio_state_changed)
        
        self.init_ui()
        
        # 재생 타이머
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.advance_frame)
        self.play_timer.setSingleShot(False)  # 반복 타이머
        
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
        
        layout.addWidget(QLabel("|"))
        
        # 볼륨 컨트롤
        layout.addWidget(QLabel("볼륨:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)  # 100%
        self.volume_slider.setMaximumWidth(80)
        self.volume_slider.valueChanged.connect(self.change_volume)
        layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("100%")
        self.volume_label.setMinimumWidth(35)
        layout.addWidget(self.volume_label)
        
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
        # 이미 재생 중이면 중복 실행 방지
        if self.is_playing:
            return
            
        self.is_playing = True
        self.play_button.setText("⏸")
        
        # 현재 프레임에서 오디오가 있는 클립 찾기
        audio_clips = self._get_audio_clips_at_frame(self.current_frame)
        
        # 오디오 재생 시도
        audio_started = False
        if audio_clips:
            # 타임라인에서 오디오 클립 재생
            audio_started = self._play_timeline_audio(audio_clips)
        elif (self.current_media_info and 
              self.current_media_info['media_type'] in ['audio', 'video'] and 
              self.current_media_path):
            # 단일 미디어 재생
            audio_started = self._play_single_media()
        
        # 오디오가 시작되지 않았어도 비디오 재생은 계속
        if not audio_started:
            print(f"[재생] 오디오 없이 비디오만 재생")
        
        # 타이머 간격 계산 (속도 고려)
        interval = int(1000 / (self.fps * self.playback_speed))
        interval = max(16, interval)  # 최소 16ms (60fps 상당)
        self.play_timer.start(interval)
        
        self.play_state_changed.emit(True)
        print(f"[재생] 시작: 프레임 {self.current_frame}, 타이머 간격: {interval}ms")
        
    def _get_audio_clips_at_frame(self, frame):
        """특정 프레임에서 오디오가 있는 클립들 찾기"""
        audio_clips = []
        for clip in self.current_timeline_clips:
            if (clip.start_frame <= frame < clip.start_frame + clip.duration and
                hasattr(clip, 'media_type') and clip.media_type in ['audio', 'video']):
                audio_clips.append(clip)
        return audio_clips
        
    def _play_timeline_audio(self, audio_clips):
        """타임라인 오디오 클립 재생 - 반환값 추가"""
        if not audio_clips:
            return False
            
        # 첫 번째 오디오 클립 재생 (다중 오디오 지원은 추후)
        clip = audio_clips[0]
        
        if self.audio_engine.current_file != clip.media_path:
            success = self.audio_engine.load_file(clip.media_path)
            if not success:
                print(f"[오디오] 로드 실패: {clip.media_path}")
                return False
                
        # 클립 내 상대 위치 계산
        relative_frame = self.current_frame - clip.start_frame
        
        # 프레임이 클립 범위를 벗어나는지 확인
        if relative_frame < 0 or relative_frame >= clip.duration:
            print(f"[오디오] 프레임이 클립 범위를 벗어남: {relative_frame}")
            return False
            
        position_ms = int((relative_frame / self.fps) * 1000)
        
        # 볼륨 설정 (클립 볼륨 적용)
        volume = getattr(clip, 'volume', 1.0)
        self.audio_engine.set_volume(volume)
        
        self.audio_engine.set_position(position_ms)
        self.audio_engine.play()
        print(f"[타임라인 오디오] {clip.name}: {relative_frame} 프레임부터")
        return True
        
    def _play_single_media(self):
        """단일 미디어 재생 - 반환값 추가"""
        if self.audio_engine.current_file != self.current_media_path:
            success = self.audio_engine.load_file(self.current_media_path)
            if not success:
                print(f"[오디오] 단일 미디어 로드 실패: {self.current_media_path}")
                return False
                
        position_ms = int((self.current_frame / self.fps) * 1000)
        
        # 위치가 유효한 범위인지 확인
        if position_ms >= self.audio_engine.total_duration:
            print(f"[오디오] 단일 미디어 재생 위치 초과: {position_ms}ms >= {self.audio_engine.total_duration}ms")
            return False
            
        self.audio_engine.set_position(position_ms)
        self.audio_engine.play()
        print(f"[단일 미디어 오디오] {os.path.basename(self.current_media_path)}: {self.current_frame} 프레임부터")
        return True
        
    def pause(self):
        """재생 일시정지"""
        if not self.is_playing:
            return
            
        self.is_playing = False
        self.play_button.setText("▶")
        self.play_timer.stop()
        
        # 오디오 일시정지
        self.audio_engine.pause()
        
        self.play_state_changed.emit(False)
        print(f"[일시정지] 프레임 {self.current_frame}")
        
    def stop(self):
        """재생 정지"""
        was_playing = self.is_playing
        self.pause()
        self.audio_engine.stop()
        self.seek_to_frame(0)
        
        if was_playing:
            print(f"[정지] 처음으로 이동")
        
    def advance_frame(self):
        """다음 프레임으로 이동 (개선된 로직)"""
        # 재생 중이 아니면 종료
        if not self.is_playing:
            return
            
        next_frame = self.current_frame + 1
        
        # 아웃 포인트 체크
        if self.out_point is not None and next_frame >= self.out_point:
            if self.loop_mode and self.in_point is not None:
                next_frame = self.in_point
                print(f"[루프] 아웃 포인트에서 인 포인트로: {self.out_point} -> {self.in_point}")
            else:
                print(f"[재생 종료] 아웃 포인트 도달: {self.out_point}")
                self.pause()
                return
        elif next_frame >= self.total_frames:
            if self.loop_mode:
                next_frame = self.in_point if self.in_point is not None else 0
                print(f"[루프] 끝에서 처음으로: {self.total_frames} -> {next_frame}")
            else:
                print(f"[재생 종료] 총 프레임 도달: {self.total_frames}")
                self.pause()
                return
                
        # 프레임 이동
        self.seek_to_frame(next_frame)
        
        # 오디오 동기화 확인 (5초마다 한 번씩만)
        if self.current_frame % (self.fps * 5) == 0:
            audio_pos_ms = self.audio_engine.get_position()
            expected_pos_ms = int((self.current_frame / self.fps) * 1000)
            
            # 동기화 오차가 1초 이상이면 조정
            if abs(audio_pos_ms - expected_pos_ms) > 1000:
                print(f"[동기화 조정] 오디오: {audio_pos_ms}ms, 예상: {expected_pos_ms}ms")
                self._sync_audio_to_frame()
        
    def previous_frame(self):
        """이전 프레임으로 이동"""
        new_frame = max(0, self.current_frame - 1)
        self.seek_to_frame(new_frame)
        
    def next_frame(self):
        """다음 프레임으로 이동"""
        new_frame = min(self.total_frames - 1, self.current_frame + 1)
        self.seek_to_frame(new_frame)
        
    def seek_to_frame(self, frame):
        """지정된 프레임으로 이동 (개선된 로직)"""
        old_frame = self.current_frame
        self.current_frame = max(0, min(frame, self.total_frames - 1))
        
        # 사용자 수동 조작 플래그 설정 (오디오 동기화 루프 방지)
        self._user_seeking = True
        
        # 오디오 동기화 (재생 중일 때만)
        if self.is_playing:
            self._sync_audio_to_frame()
        
        # 프리뷰 프레임 업데이트 (타임라인 모드에서)
        if self.preview_mode == "timeline":
            # 타임라인에서 현재 프레임에 해당하는 클립 찾기
            active_clips = []
            for clip in self.current_timeline_clips:
                if clip.start_frame <= self.current_frame < clip.start_frame + clip.duration:
                    active_clips.append(clip)
                    
            if active_clips:
                active_clips.sort(key=lambda c: c.track)
                top_clip = active_clips[0]
                relative_frame = self.current_frame - top_clip.start_frame
                
                # 미디어 정보 설정 (필요시에만)
                if top_clip.media_path != self.preview_frame.current_media_path:
                    try:
                        media_info = MediaAnalyzer.get_media_info(top_clip.media_path)
                        self.preview_frame.set_media(top_clip.media_path, media_info)
                    except:
                        pass
                        
                self.preview_frame.set_current_frame(relative_frame)
                self.preview_frame.set_active_clip(top_clip)
            else:
                self.preview_frame.clear_frame()
        
        # 플래그 해제
        self._user_seeking = False
        
        # UI 업데이트
        self.update_time_display()
        self.preview_frame.force_update()
        self.frame_changed.emit(self.current_frame)
        
        # 로그 출력 (초 단위 변경시에만)
        if int(old_frame / self.fps) != int(self.current_frame / self.fps):
            current_seconds = self.current_frame / self.fps
            print(f"[프레임 이동] {self.current_frame} ({current_seconds:.1f}초)")
        
    def _sync_audio_to_frame(self):
        """현재 프레임과 오디오 동기화"""
        # 재생 중이 아니면 동기화하지 않음
        if not self.is_playing:
            return
            
        # 타임라인 모드인지 단일 미디어 모드인지 확인
        audio_clips = self._get_audio_clips_at_frame(self.current_frame)
        
        if audio_clips:
            # 타임라인 오디오
            clip = audio_clips[0]
            relative_frame = self.current_frame - clip.start_frame
            position_ms = int((relative_frame / self.fps) * 1000)
            
            # 오디오 파일이 변경되었을 때만 로드
            if self.audio_engine.current_file != clip.media_path:
                success = self.audio_engine.load_file(clip.media_path)
                if not success:
                    print(f"[오디오 동기화] 로드 실패: {clip.media_path}")
                    return
                    
            # 위치가 유효한 범위 내에 있는지 확인
            if position_ms >= 0 and position_ms < self.audio_engine.total_duration:
                self.audio_engine.set_position(position_ms)
            else:
                # 범위를 벗어나면 오디오 일시정지
                self.audio_engine.pause()
                
        elif (self.current_media_info and 
              self.current_media_info['media_type'] in ['audio', 'video'] and
              self.current_media_path):
            # 단일 미디어
            position_ms = int((self.current_frame / self.fps) * 1000)
            
            # 오디오 파일이 변경되었을 때만 로드
            if self.audio_engine.current_file != self.current_media_path:
                success = self.audio_engine.load_file(self.current_media_path)
                if not success:
                    print(f"[오디오 동기화] 단일 미디어 로드 실패: {self.current_media_path}")
                    return
                    
            # 위치가 유효한 범위 내에 있는지 확인
            if position_ms >= 0 and position_ms < self.audio_engine.total_duration:
                self.audio_engine.set_position(position_ms)
            else:
                # 범위를 벗어나면 오디오 일시정지
                self.audio_engine.pause()
        else:
            # 오디오가 없는 구간 - 일시정지만 (루프 방지)
            if self.audio_engine.is_playing:
                self.audio_engine.pause()
        
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
        old_speed = self.playback_speed
        self.playback_speed = value / 100.0
        self.speed_label.setText(f"{self.playback_speed:.1f}x")
        
        # 재생 중이면 타이머 재시작
        if self.is_playing:
            interval = int(1000 / (self.fps * self.playback_speed))
            interval = max(16, interval)  # 최소 16ms
            self.play_timer.start(interval)
            
        # 속도 변경 로그 (0.1x 단위로만)
        if abs(old_speed - self.playback_speed) >= 0.1:
            print(f"[재생속도] {self.playback_speed:.1f}x")
            
    def change_volume(self, value):
        """볼륨 변경"""
        volume = value / 100.0
        self.volume_label.setText(f"{value}%")
        self.audio_engine.set_volume(volume)
        # 볼륨 로그 간소화 (10% 단위로만)
        if value % 10 == 0:
            print(f"[볼륨] {value}%")
            
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
            self.preview_mode = "single"
            
            # 프레임 정보 업데이트
            self.total_frames = self.current_media_info['duration_frames']
            self.fps = self.current_media_info['fps']
            
            # 프리뷰 프레임에 미디어 설정
            self.preview_frame.set_media(media_path, self.current_media_info)
            
            # 현재 프레임을 0으로 리셋
            self.current_frame = 0
            self.preview_frame.set_current_frame(0)
            
            # 시간 표시 업데이트
            self.update_time_display()
            
            print(f"[미디어 로드] {os.path.basename(media_path)} - {self.current_media_info['media_type']}")
            return True
            
        except Exception as e:
            print(f"미디어 로드 실패: {e}")
            return False
            
    def set_timeline_clips(self, clips):
        """타임라인 클립 설정 (로그 스팸 방지)"""
        self.current_timeline_clips = clips
        self.preview_frame.set_timeline_clips(clips)
        self.preview_mode = "timeline"
        
        # 타임라인의 총 길이 계산
        if clips:
            max_end_frame = max((clip.start_frame + clip.duration) for clip in clips)
            self.total_frames = max(max_end_frame, 900)  # 최소 30초
        else:
            self.total_frames = 900
            
        # 로그 스팸 방지 - 클립 수나 길이가 변경되었을 때만 출력
        current_length = self.total_frames / self.fps
        if (not hasattr(self, '_last_clip_count') or 
            not hasattr(self, '_last_timeline_length') or
            self._last_clip_count != len(clips) or
            abs(self._last_timeline_length - current_length) > 1.0):
            
            print(f"[타임라인 업데이트] {len(clips)}개 클립, 총 길이: {current_length:.1f}초")
            self._last_clip_count = len(clips)
            self._last_timeline_length = current_length
        
    def render_frame_at_position(self, frame_position):
        """특정 프레임 위치의 이미지 렌더링 (순환 시그널 방지)"""
        old_frame = self.current_frame
        self.current_frame = frame_position
        self.preview_mode = "timeline"
        
        # 프리뷰 프레임에도 현재 위치 정보 전달
        self.preview_frame.timeline_frame_position = frame_position
        
        # 해당 프레임에서 활성 클립 찾기
        active_clips = []
        for clip in self.current_timeline_clips:
            if clip.start_frame <= frame_position < clip.start_frame + clip.duration:
                active_clips.append(clip)
                
        if active_clips:
            # 가장 위쪽 트랙의 클립 사용 (간단한 구현)
            active_clips.sort(key=lambda c: c.track)
            top_clip = active_clips[0]
            
            # 클립 내 상대 프레임 계산
            relative_frame = frame_position - top_clip.start_frame
            
            # 로그 출력 (프레임이 실제로 변경되었을 때만)
            if old_frame != frame_position:
                print(f"[프리뷰 렌더링] 프레임: {frame_position}, 클립: {top_clip.name}, 상대프레임: {relative_frame}")
            
            # 미디어 정보 설정 (프리뷰 프레임용) - 클립 변경시에만
            if (top_clip.media_path != self.preview_frame.current_media_path or 
                not self.preview_frame.current_media_info):
                try:
                    media_info = MediaAnalyzer.get_media_info(top_clip.media_path)
                    self.preview_frame.set_media(top_clip.media_path, media_info)
                    print(f"[미디어 변경] {os.path.basename(top_clip.media_path)}")
                except Exception as e:
                    print(f"미디어 정보 로드 실패: {top_clip.media_path} - {e}")
                    
            # 프리뷰 프레임 업데이트 - 확실한 업데이트
            self.preview_frame.set_current_frame(relative_frame)
            self.preview_frame.set_active_clip(top_clip)
        else:
            # 활성 클립이 없으면 빈 화면
            if old_frame != frame_position:
                print(f"[프리뷰 렌더링] 프레임 {frame_position}: 활성 클립 없음")
            self.preview_frame.clear_frame()
            
        # 시간 표시 및 화면 업데이트
        self.update_time_display()
        
        # 확실한 화면 업데이트 (중복이어도 상관없음)
        self.preview_frame.force_update()
        
        # 위젯 자체도 업데이트
        self.update()
        
        # 타임라인에서 호출된 경우 시그널 발생하지 않음 (순환 방지)
        # 사용자가 직접 프리뷰에서 조작한 경우에만 시그널 발생
        # if old_frame != frame_position:
        #     self.frame_changed.emit(self.current_frame)
        
    def _on_audio_position_changed(self, position_ms):
        """오디오 위치 변경 이벤트 (동기화 개선)"""
        # 재생 중이 아니거나 사용자가 수동으로 조작 중이면 무시
        if not self.is_playing or hasattr(self, '_user_seeking'):
            return
            
        # 오디오 위치를 기준으로 프레임 동기화
        audio_frame = int((position_ms / 1000.0) * self.fps)
        
        # 타임라인 모드에서는 클립 내 상대 위치 고려
        if self.preview_mode == "timeline":
            audio_clips = self._get_audio_clips_at_frame(self.current_frame)
            if audio_clips:
                clip = audio_clips[0]
                absolute_frame = clip.start_frame + audio_frame
                target_frame = absolute_frame
            else:
                target_frame = audio_frame
        else:
            target_frame = audio_frame
        
        # 동기화 임계값 설정 (프레임 드리프트 방지)
        sync_threshold = 3  # 3프레임 이상 차이날 때만 동기화
        frame_diff = abs(target_frame - self.current_frame)
        
        if frame_diff > sync_threshold and frame_diff < 300:  # 10초 이상 차이나면 무시 (비정상 상황)
            old_frame = self.current_frame
            self.current_frame = max(0, min(target_frame, self.total_frames - 1))
            
            # 프레임 점프가 너무 클 때는 로그 남김
            if frame_diff > 30:  # 1초 이상
                print(f"[동기화] 큰 프레임 점프: {old_frame} -> {self.current_frame} ({frame_diff} 프레임)")
            
            # UI 업데이트 (시그널 방출 방지하여 루프 차단)
            self.update_time_display()
            self.preview_frame.update()
            # frame_changed 시그널은 타임라인 업데이트를 위해 필요하지만 주의깊게 사용
            self.frame_changed.emit(self.current_frame)
        
    def _on_audio_state_changed(self, state):
        """오디오 상태 변경 이벤트"""
        # QMediaPlayer.PlaybackState와 동기화
        from PyQt6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlaybackState.StoppedState:
            if self.is_playing:  # 오디오가 끝났으면 재생 정지
                self.pause()
        
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
        self.active_clip = None  # 현재 활성 클립
        self.thumbnail_cache = {}
        
        # 타임라인 프레임 위치 (render_frame_at_position에서 설정)
        self.timeline_frame_position = 0
        
        # 강제 업데이트 플래그
        self._force_update = False
        
    def force_update(self):
        """강제 프레임 업데이트 (더 확실한 방법)"""
        # 캐시된 렌더링 상태는 유지 (로그 스팸 방지)
        # if hasattr(self, '_last_rendered_frame'):
        #     delattr(self, '_last_rendered_frame')
            
        self._force_update = True
        
        # 여러 번의 업데이트 시도
        self.update()
        self.repaint()  # 즉시 다시 그리기
        
        # Qt 이벤트 루프 강제 처리
        QCoreApplication.processEvents()
        
        self._force_update = False
        
    def set_current_frame(self, frame):
        """현재 프레임 설정 (개선된 로직)"""
        if self.current_frame != frame:
            old_frame = self.current_frame
            self.current_frame = frame
            
            # 미디어 정보가 있으면 시간도 계산
            if self.current_media_info and 'fps' in self.current_media_info:
                current_time = frame / self.current_media_info['fps']
                print(f"[PreviewFrame] 프레임 변경: {old_frame} -> {frame} ({current_time:.2f}초)")
            else:
                print(f"[PreviewFrame] 프레임 변경: {old_frame} -> {frame}")
                
            # 강제 화면 업데이트
            self.force_update()
        else:
            # 같은 프레임이어도 강제 업데이트가 필요한 경우가 있음
            if hasattr(self, '_force_update') and self._force_update:
                print(f"[PreviewFrame] 강제 업데이트: 프레임 {frame}")
                self.update()
                self.repaint()
        
    def clear_frame(self):
        """프레임 지우기 (개선된 로직)"""
        self.current_media_path = None
        self.current_media_info = None
        self.active_clip = None
        self.current_frame = 0
        print(f"[PreviewFrame] 프레임 지움")
        self.force_update()
        
    def draw_video_frame(self, painter, rect):
        """비디오 프레임 그리기 (썸네일 기반) - 정확한 시간 우선"""
        try:
            # 현재 프레임 시간 계산 (더 정확한 계산)
            if self.current_media_info and 'fps' in self.current_media_info:
                current_time = self.current_frame / self.current_media_info['fps']
            else:
                current_time = self.current_frame / 30.0  # 기본 30fps
                
            # 로그 스팸 방지 - 이전 프레임과 다를 때만 출력
            if not hasattr(self, '_last_rendered_frame') or self._last_rendered_frame != self.current_frame:
                print(f"[비디오 렌더링] 프레임: {self.current_frame}, 시간: {current_time:.2f}초, 파일: {os.path.basename(self.current_media_path) if self.current_media_path else 'None'}")
                self._last_rendered_frame = self.current_frame
                
            # 캐시 키 생성 (파일 경로 + 프레임 번호)
            cache_key = f"{self.current_media_path}_{self.current_frame}"
            
            # 이미 렌더링된 프레임인지 확인
            if hasattr(self, '_frame_cache') and cache_key in self._frame_cache:
                pixmap = self._frame_cache[cache_key]
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        rect.size(), 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    x = rect.x() + (rect.width() - scaled_pixmap.width()) // 2
                    y = rect.y() + (rect.height() - scaled_pixmap.height()) // 2
                    painter.drawPixmap(x, y, scaled_pixmap)
                    self._draw_frame_overlay(painter, rect)
                    return
                    
            # 캐시 초기화
            if not hasattr(self, '_frame_cache'):
                self._frame_cache = {}
                
            # 캐시 크기 제한 (메모리 관리)
            if len(self._frame_cache) > 20:
                # 가장 오래된 항목 제거
                oldest_key = next(iter(self._frame_cache))
                del self._frame_cache[oldest_key]
                
            # 정확한 현재 시간의 썸네일을 먼저 시도
            loaded_pixmap = None
            used_time = current_time
            
            # 1. 정확한 현재 시간 썸네일 시도
            print(f"[썸네일 시도] 정확한 시간: {current_time:.1f}초")
            thumbnail_path = MediaAnalyzer.get_thumbnail_path(self.current_media_path, current_time)
            
            if thumbnail_path and os.path.exists(thumbnail_path):
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    loaded_pixmap = pixmap
                    used_time = current_time
                    print(f"[썸네일 로드] {os.path.basename(thumbnail_path)} (정확한 시간: {current_time:.1f}s)")
                else:
                    print(f"[썸네일 오류] 파일 로드 실패: {thumbnail_path}")
            else:
                print(f"[썸네일 없음] 시간 {current_time:.1f}초 썸네일 파일 없음")
                
            # 2. 정확한 시간이 실패하면 근처 시간들 시도
            if not loaded_pixmap:
                print(f"[썸네일 대체] 근처 시간대 시도")
                thumbnail_times = []
                
                # 근처 시간들 (0.5초 간격)
                for offset in [-1.0, -0.5, 0.5, 1.0]:
                    nearby_time = current_time + offset
                    if nearby_time >= 0:
                        thumbnail_times.append(nearby_time)
                
                # 기본 안전 시간들
                thumbnail_times.extend([0.5, 1.0, 2.0, 0.0])
                
                # 중복 제거
                thumbnail_times = list(set(thumbnail_times))
                
                for time_to_try in thumbnail_times:
                    if time_to_try < 0:
                        continue
                        
                    thumbnail_path = MediaAnalyzer.get_thumbnail_path(self.current_media_path, time_to_try)
                    
                    if thumbnail_path and os.path.exists(thumbnail_path):
                        pixmap = QPixmap(thumbnail_path)
                        if not pixmap.isNull():
                            loaded_pixmap = pixmap
                            used_time = time_to_try
                            print(f"[썸네일 대체로드] {os.path.basename(thumbnail_path)} (시간: {time_to_try:.1f}s)")
                            break
                        
            if loaded_pixmap:
                # 캐시에 저장
                self._frame_cache[cache_key] = loaded_pixmap
                
                scaled_pixmap = loaded_pixmap.scaled(
                    rect.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                
                x = rect.x() + (rect.width() - scaled_pixmap.width()) // 2
                y = rect.y() + (rect.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
                
                # 대체 썸네일 표시 알림 (현재 시간과 다를 때만)
                if abs(used_time - current_time) > 0.1:
                    painter.setPen(QPen(QColor(255, 255, 0, 200)))
                    font = QFont("Arial", 10)
                    painter.setFont(font)
                    painter.drawText(rect.adjusted(10, 10, -10, -10), 
                                   Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, 
                                   f"썸네일({used_time:.1f}s)")
                
                self._draw_frame_overlay(painter, rect)
                return
                    
            # 모든 방법 실패시 플레이스홀더
            print(f"[썸네일 완전실패] {os.path.basename(self.current_media_path)} 프레임 {self.current_frame}")
            self.draw_placeholder(painter, rect, f"비디오: {os.path.basename(self.current_media_path)}")
            
        except Exception as e:
            print(f"비디오 프레임 그리기 오류: {e}")
            self.draw_placeholder(painter, rect, f"비디오 로드 실패")
            
    def _draw_frame_overlay(self, painter, rect):
        """프레임 오버레이 정보 그리기 (개선된 로직)"""
        painter.setPen(QPen(QColor(255, 255, 255, 200)))
        font = QFont("Arial", 12)
        painter.setFont(font)
        
        # 프레임 번호 및 시간 (더 정확한 정보)
        if self.current_media_info and 'fps' in self.current_media_info:
            current_time = self.current_frame / self.current_media_info['fps']
            frame_text = f"Frame: {self.current_frame} ({current_time:.2f}s)"
        else:
            frame_text = f"Frame: {self.current_frame}"
            
        painter.drawText(rect.adjusted(10, 10, -10, -10), 
                        Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, 
                        frame_text)
        
        # 활성 클립 정보 (타임라인 모드)
        if self.active_clip:
            clip_text = f"클립: {self.active_clip.name}"
            painter.drawText(rect.adjusted(10, 30, -10, -10), 
                            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, 
                            clip_text)
            
        # 타임라인 위치 정보 (타임라인 모드에서)
        if hasattr(self, 'timeline_frame_position'):
            timeline_text = f"타임라인: {self.timeline_frame_position}"
            painter.drawText(rect.adjusted(10, 50, -10, -10), 
                            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, 
                            timeline_text)
        
    def set_media(self, media_path, media_info):
        """미디어 설정 (확실한 업데이트)"""
        path_changed = self.current_media_path != media_path
        self.current_media_path = media_path
        self.current_media_info = media_info
        
        if path_changed:
            print(f"[PreviewFrame] 미디어 설정: {os.path.basename(media_path) if media_path else 'None'}")
            # 프레임을 0으로 리셋하고 강제 업데이트
            self.current_frame = 0
            # 미디어가 변경되었으므로 프레임 캐시 초기화
            if hasattr(self, '_frame_cache'):
                self._frame_cache.clear()
            # 렌더링 상태 초기화
            if hasattr(self, '_last_rendered_frame'):
                delattr(self, '_last_rendered_frame')
            self.force_update()
        else:
            # 같은 미디어라도 프레임이나 정보가 변경되었을 수 있으므로 업데이트
            self.force_update()

    def paintEvent(self, event):
        """페인트 이벤트 (개선된 로직)"""
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
        # 그라데이션 배경 (체크보드 패턴)
        painter.fillRect(rect, QColor(40, 40, 40))
        
        # 체크보드 패턴 그리기
        check_size = 20
        for x in range(0, rect.width(), check_size * 2):
            for y in range(0, rect.height(), check_size * 2):
                check_rect = QRect(rect.x() + x, rect.y() + y, check_size, check_size)
                painter.fillRect(check_rect, QColor(60, 60, 60))
                check_rect = QRect(rect.x() + x + check_size, rect.y() + y + check_size, check_size, check_size)
                painter.fillRect(check_rect, QColor(60, 60, 60))
        
        # 중앙에 플레이스홀더 텍스트
        painter.setPen(QPen(QColor(200, 200, 200)))
        font = QFont("Arial", 18, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "📽️ 영상 미리보기")
        
        # 프레임 번호 표시
        frame_text = f"Frame: {self.current_frame}"
        font = QFont("Arial", 12)
        painter.setFont(font)
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
                
                # 프레임 번호 오버레이
                self._draw_frame_overlay(painter, rect)
            else:
                self.draw_placeholder(painter, rect, f"이미지: {os.path.basename(self.current_media_path)}")
        except Exception as e:
            print(f"이미지 프레임 그리기 오류: {e}")
            self.draw_placeholder(painter, rect, f"이미지 로드 실패")
            
    def draw_audio_frame(self, painter, rect):
        """오디오 파형 그리기"""
        # 오디오 배경 (어두운 그라데이션)
        painter.fillRect(rect, QColor(20, 30, 40))
        
        # 간단한 파형 시뮬레이션
        import math
        painter.setPen(QPen(QColor(100, 200, 100), 2))
        
        # 현재 재생 위치 기반 파형 그리기
        wave_height = rect.height() // 4
        wave_center = rect.y() + rect.height() // 2
        
        # 여러 주파수 파형 그리기
        for i in range(0, rect.width(), 2):
            # 시간 기반 파형 (현재 프레임 반영)
            time = (i + self.current_frame * 2) * 0.1
            wave1 = math.sin(time) * wave_height * 0.3
            wave2 = math.sin(time * 2.5) * wave_height * 0.2
            wave3 = math.sin(time * 0.7) * wave_height * 0.1
            
            combined_wave = wave1 + wave2 + wave3
            
            x = rect.x() + i
            y = wave_center + int(combined_wave)
            
            painter.drawLine(x, wave_center, x, y)
        
        # 중앙에 오디오 아이콘
        painter.setPen(QPen(QColor(150, 255, 150), 3))
        font = QFont("Arial", 36, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🎵")
        
        # 파일 이름 및 정보 표시
        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        file_name = os.path.basename(self.current_media_path)
        painter.drawText(rect.adjusted(10, 10, -10, -60), 
                        Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter, 
                        file_name)
        
        # 현재 시간 표시
        if self.current_media_info:
            current_time = self.current_frame / 30.0  # 30fps 기준
            total_time = self.current_media_info['duration']
            time_text = f"{current_time:.1f}s / {total_time:.1f}s"
            
            font = QFont("Arial", 12)
            painter.setFont(font)
            painter.setPen(QPen(QColor(200, 200, 200)))
            painter.drawText(rect.adjusted(10, -50, -10, -10), 
                            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, 
                            time_text)
        
    def draw_placeholder(self, painter, rect, text="미디어 미리보기"):
        """플레이스홀더 그리기"""
        # 그라데이션 배경 (어두운 테마)
        painter.fillRect(rect, QColor(45, 45, 45))
        
        # 테두리 그리기
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRect(rect.adjusted(2, 2, -2, -2))
        
        # 중앙에 텍스트
        painter.setPen(QPen(QColor(220, 220, 220)))
        font = QFont("Arial", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        
        # 미디어 정보 표시
        if self.current_media_info:
            info_lines = [
                f"크기: {self.current_media_info['width']}x{self.current_media_info['height']}",
                f"FPS: {self.current_media_info['fps']:.1f}",
                f"길이: {self.current_media_info['duration']:.1f}초",
                f"타입: {self.current_media_info['media_type']}"
            ]
            
            font = QFont("Arial", 10)
            painter.setFont(font)
            painter.setPen(QPen(QColor(180, 180, 180)))
            
            y_offset = 15
            for i, info_line in enumerate(info_lines):
                painter.drawText(rect.adjusted(10, 10 + i * y_offset, -10, -10), 
                               Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, 
                               info_line)
        
        # 프레임 번호 표시
        frame_text = f"Frame: {self.current_frame}"
        font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 100)))
        painter.drawText(rect.adjusted(10, -30, -10, -10), 
                        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, 
                        frame_text)
        
    def set_timeline_clips(self, clips):
        """타임라인 클립 설정"""
        self.timeline_clips = clips
        
    def set_active_clip(self, clip):
        """활성 클립 설정"""
        self.active_clip = clip 