"""
BLOUcut 타임라인 위젯
영상 클립들을 시간순으로 배치하고 편집하는 메인 인터페이스
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
                           QLabel, QPushButton, QSlider, QSpinBox, QFrame,
                           QRubberBand, QMenu, QApplication)
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QMouseEvent, QKeyEvent

from .timeline_clip import TimelineClip
from .timeline_marker import MarkerManager
from ..core.project_manager import ProjectManager
from ..core.command_manager import (CommandManager, AddClipCommand, DeleteClipCommand, 
                                   MoveClipCommand, SplitClipCommand)
from ..core.clipboard_manager import ClipboardManager
from ..core.media_analyzer import MediaAnalyzer
from ..audio.waveform_generator import WaveformGenerator, WaveformRenderer

class TimelineWidget(QWidget):
    """타임라인 위젯"""
    
    # 시그널
    playhead_changed = pyqtSignal(int)  # 재생 헤드 위치 변경
    selection_changed = pyqtSignal(list)  # 선택된 클립 변경
    clip_moved = pyqtSignal(object, int, int)  # 클립 이동
    
    def __init__(self):
        super().__init__()
        self.clips = []  # 타임라인의 클립들
        self.selected_clips = []  # 선택된 클립들
        self.playhead_position = 0  # 재생 헤드 위치 (프레임 단위)
        self.zoom_level = 1.0  # 줌 레벨
        self.tracks_height = 80  # 트랙 높이
        self.ruler_height = 30  # 룰러 높이
        self.track_count = 3  # 기본 트랙 수
        self.max_tracks = 20  # 최대 트랙 수
        
        # 마우스 상호작용
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.drag_clip = None
        self.is_playhead_dragging = False
        self.drag_original_start_frame = 0
        self.drag_original_track = 0
        
        # 클립 크기 조정 (비활성화됨)
        self.is_resizing = False
        self.resize_clip = None
        self.resize_edge = None  # 'left' 또는 'right'
        self.original_duration = 0
        self.resize_threshold = 3  # 픽셀 단위 (매우 엄격하게) - 현재 비활성화
        
        # 관리자들
        self.command_manager = CommandManager()
        self.marker_manager = MarkerManager()
        self.clipboard_manager = ClipboardManager()
        self.waveform_generator = WaveformGenerator()
        
        # 스냅 기능
        self.snap_enabled = True
        self.snap_threshold = 10  # 픽셀 단위
        
        # 파형 표시 옵션
        self.show_waveforms = True
        
        # 드래그&드롭 상태
        self.drag_drop_frame = None
        self.drag_drop_track = None
        
        # 클립 드래그 오프셋 (클립 내부에서 클릭한 위치)
        self.drag_offset_x = 0
        
        # 타임라인 스크롤 및 뷰포트
        self.timeline_offset_x = 0  # 좌우 스크롤 오프셋
        self.timeline_width = 10000  # 전체 타임라인 너비 (픽셀)
        self.viewport_width = 800    # 보이는 영역 너비
        
        # 핸드 툴 모드
        self.hand_tool_active = False
        self.hand_drag_start = QPoint()
        self.hand_drag_last_offset = 0
        
        # 키보드 포커스 활성화
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # 드래그&드롭 활성화
        self.setAcceptDrops(True)
        
        self.init_ui()
        
        # 크기 변경 이벤트
        self.resizeEvent = self.on_resize
        
    def init_ui(self):
        """UI 초기화"""
        self.setMinimumSize(800, 200)
        self.setMouseTracking(True)
        self.apply_styles()
        
    def on_resize(self, event):
        """크기 변경 이벤트"""
        self.viewport_width = self.width()
        # 타임라인 전체 너비 동적 계산
        if self.clips:
            max_end_frame = max(clip.start_frame + clip.duration for clip in self.clips)
            pixels_per_frame = self.zoom_level * 2
            self.timeline_width = max(10000, (max_end_frame + 300) * pixels_per_frame)
        super().resizeEvent(event)
        
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #555;
            }
        """)
        
    def paintEvent(self, event):
        """페인트 이벤트"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 배경 그리기
        painter.fillRect(self.rect(), QColor(43, 43, 43))
        
        # 룰러 그리기
        self.draw_ruler(painter)
        
        # 트랙 구분선 그리기
        self.draw_tracks(painter)
        
        # 클립들 그리기
        self.draw_clips(painter)
        
        # 마커들 그리기
        self.draw_markers(painter)
        
        # 재생 헤드 그리기
        self.draw_playhead(painter)
        
        # 드래그&드롭 프리뷰 그리기
        self.draw_drop_preview(painter)
        
    def draw_ruler(self, painter):
        """룰러 그리기"""
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.fillRect(0, 0, self.width(), self.ruler_height, QColor(60, 60, 60))
        
        # 시간 눈금 그리기
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        frames_per_second = 30
        pixels_per_frame = self.zoom_level * 2
        
        # 줌 레벨에 따른 동적 시간 간격 결정
        time_interval = self.get_optimal_time_interval(pixels_per_frame, frames_per_second)
        
        # 보이는 영역의 시작/끝 시간 계산
        start_time = max(0, self.timeline_offset_x / (pixels_per_frame * frames_per_second))
        end_time = (self.timeline_offset_x + self.width()) / (pixels_per_frame * frames_per_second)
        
        # 시간 간격에 맞춰 정렬
        start_interval = int(start_time / time_interval) * time_interval
        end_interval = (int(end_time / time_interval) + 2) * time_interval
        
        current_time = start_interval
        while current_time <= end_interval:
            x = (current_time * frames_per_second * pixels_per_frame) - self.timeline_offset_x
            
            if -100 <= x <= self.width() + 100:
                # 주요 눈금 그리기
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawLine(int(x), 0, int(x), self.ruler_height)
                
                # 시간 텍스트 포맷팅
                time_text = self.format_time_text(current_time, time_interval)
                painter.drawText(int(x) + 2, self.ruler_height - 5, time_text)
                
                # 작은 눈금들 (적절한 간격으로)
                self.draw_minor_ticks(painter, current_time, time_interval, pixels_per_frame, frames_per_second)
            
            current_time += time_interval
            
    def get_optimal_time_interval(self, pixels_per_frame, frames_per_second):
        """줌 레벨에 따른 최적 시간 간격 반환"""
        if pixels_per_frame <= 0 or frames_per_second <= 0:
            return 1.0  # 기본값
            
        seconds_per_pixel = 1.0 / (pixels_per_frame * frames_per_second)
        
        # 최소 80픽셀 간격을 유지하도록 시간 간격 결정
        min_interval_seconds = seconds_per_pixel * 80
        
        # 확장된 시간 간격 목록 (매우 작은 값부터 매우 큰 값까지)
        intervals = [
            # 매우 작은 간격 (극대 줌용)
            0.001, 0.002, 0.005, 0.01, 0.02, 0.05,
            # 일반 간격
            0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30,  # 초
            60, 120, 300, 600, 900, 1800,         # 분
            3600, 7200, 10800, 21600,             # 시간
            # 매우 큰 간격 (극소 줌용)
            86400, 172800, 604800, 2629746        # 일, 주, 월
        ]
        
        # 최소 간격보다 큰 가장 작은 간격 선택
        for interval in intervals:
            if interval >= min_interval_seconds:
                return interval
        
        # 최대 간격보다도 큰 경우 동적으로 생성
        return min_interval_seconds
        
    def format_time_text(self, time_seconds, interval):
        """시간 간격에 따른 텍스트 포맷팅"""
        if interval < 0.01:
            # 매우 작은 간격: 밀리초 표시
            return f"{time_seconds*1000:.0f}ms"
        elif interval < 0.1:
            # 0.01~0.1초: 소수점 2자리
            return f"{time_seconds:.2f}s"
        elif interval < 1:
            # 0.1~1초: 소수점 1자리
            return f"{time_seconds:.1f}s"
        elif interval < 60:
            # 1분 미만: 초 단위
            return f"{int(time_seconds)}s"
        elif interval < 3600:
            # 1시간 미만: 분:초
            minutes = int(time_seconds // 60)
            seconds = int(time_seconds % 60)
            return f"{minutes}:{seconds:02d}"
        elif interval < 86400:
            # 1일 미만: 시:분:초
            hours = int(time_seconds // 3600)
            minutes = int((time_seconds % 3600) // 60)
            seconds = int(time_seconds % 60)
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            # 1일 이상: 일 단위
            days = int(time_seconds // 86400)
            hours = int((time_seconds % 86400) // 3600)
            return f"{days}d {hours}h"
            
    def draw_minor_ticks(self, painter, current_time, interval, pixels_per_frame, frames_per_second):
        """작은 눈금 그리기"""
        # 간격이 충분히 클 때만 작은 눈금 표시
        minor_interval = interval / 5  # 주 눈금의 1/5 간격
        
        if minor_interval * frames_per_second * pixels_per_frame >= 20:  # 최소 20픽셀 간격
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            
            for i in range(1, 5):  # 중간에 4개의 작은 눈금
                minor_time = current_time + minor_interval * i
                minor_x = (minor_time * frames_per_second * pixels_per_frame) - self.timeline_offset_x
                
                if 0 <= minor_x <= self.width():
                    painter.drawLine(int(minor_x), self.ruler_height - 8, 
                                   int(minor_x), self.ruler_height)
                               
    def draw_tracks(self, painter):
        """트랙 구분선 그리기"""
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        
        for i in range(self.track_count + 1):
            y = self.ruler_height + i * self.tracks_height
            painter.drawLine(0, y, self.width(), y)
            
        # 트랙 레이블과 버튼
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        
        for i in range(self.track_count):
            y = self.ruler_height + i * self.tracks_height + self.tracks_height // 2
            painter.drawText(5, y, f"V{i+1}")
            
        # 트랙 추가 버튼 영역 (마지막 트랙 아래)
        if self.track_count < self.max_tracks:
            add_track_y = self.ruler_height + self.track_count * self.tracks_height
            painter.setPen(QPen(QColor(100, 200, 100), 2))
            painter.drawLine(0, add_track_y, self.width(), add_track_y)
            
            # + 버튼
            plus_rect = QRect(10, add_track_y + 10, 30, 20)
            painter.drawRect(plus_rect)
            painter.drawText(plus_rect, Qt.AlignmentFlag.AlignCenter, "+")
            
    def draw_clips(self, painter):
        """클립들 그리기"""
        for clip in self.clips:
            self.draw_clip(painter, clip)
            
    def draw_clip(self, painter, clip):
        """개별 클립 그리기"""
        # 클립 위치 계산 (오프셋 적용)
        pixels_per_frame = self.zoom_level * 2
        x = (clip.start_frame * pixels_per_frame) - self.timeline_offset_x
        y = self.ruler_height + clip.track * self.tracks_height + 5
        width = clip.duration * pixels_per_frame
        height = self.tracks_height - 10
        
        # 보이는 영역 밖의 클립은 건너뛰기
        if x + width < 0 or x > self.width():
            return
            
        clip_rect = QRect(int(x), int(y), int(width), int(height))
        
        # 클립 색상 (선택 여부에 따라)
        if clip in self.selected_clips:
            color = QColor(255, 215, 0)  # 금색 (선택됨)
        else:
            color = QColor(76, 175, 80)  # 초록색 (기본)
            
        # 클립 배경
        painter.fillRect(clip_rect, color)
        
        # 클립 테두리
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawRect(clip_rect)
        
        # 파형 그리기 (오디오 클립인 경우)
        if (self.show_waveforms and hasattr(clip, 'media_type') and 
            clip.media_type == 'audio' and hasattr(clip, 'media_path')):
            # 파형 데이터 가져오기 (캐시에서)
            waveform_data = self.waveform_generator.get_cached_waveform(clip.media_path)
            if waveform_data:
                # 클립 시간 범위 계산
                start_time = clip.start_frame / 30.0  # 30fps 기준
                end_time = (clip.start_frame + clip.duration) / 30.0
                
                # 파형 그리기 영역
                waveform_rect = clip_rect.adjusted(2, 20, -2, -2)
                WaveformRenderer.draw_waveform(
                    painter, waveform_data, waveform_rect, 
                    start_time, end_time, QColor(150, 255, 150)
                )
            else:
                # 파형 데이터가 없으면 생성 요청
                self.waveform_generator.generate_waveform(clip.media_path)
        
        # 클립 제목
        font = QFont("Arial", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        
        # 텍스트가 클립 안에 맞도록 조정
        clip_name = clip.name
        if width < 100:  # 클립이 너무 작으면 이름 축약
            clip_name = clip_name[:8] + "..."
            
        painter.drawText(clip_rect.adjusted(5, 5, -5, -5), 
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, 
                        clip_name)
                        
    def draw_playhead(self, painter):
        """재생 헤드 그리기"""
        pixels_per_frame = self.zoom_level * 2
        x = (self.playhead_position * pixels_per_frame) - self.timeline_offset_x
        
        # 보이는 영역 밖이면 그리지 않음
        if x < 0 or x > self.width():
            return
        
        # 재생 헤드 라인
        painter.setPen(QPen(QColor(255, 0, 0), 3))
        painter.drawLine(int(x), 0, int(x), self.height())
        
        # 재생 헤드 위 삼각형
        triangle_points = [
            QPoint(int(x), 0),
            QPoint(int(x) - 8, self.ruler_height),
            QPoint(int(x) + 8, self.ruler_height)
        ]
        painter.setBrush(QBrush(QColor(255, 0, 0)))
        painter.drawPolygon(triangle_points)
        
    def draw_markers(self, painter):
        """마커들 그리기"""
        pixels_per_frame = self.zoom_level * 2
        
        for marker in self.marker_manager.markers:
            x = marker.frame * pixels_per_frame
            
            # 마커 색상
            color = marker.get_color()
            
            if marker.is_range_marker():
                # 범위 마커
                end_x = marker.get_end_frame() * pixels_per_frame
                width = end_x - x
                
                # 반투명 배경
                bg_color = QColor(color)
                bg_color.setAlpha(50)
                painter.fillRect(int(x), self.ruler_height, int(width), 
                               self.height() - self.ruler_height, bg_color)
                
                # 시작/끝 라인
                painter.setPen(QPen(color, 2))
                painter.drawLine(int(x), self.ruler_height, int(x), self.height())
                painter.drawLine(int(end_x), self.ruler_height, int(end_x), self.height())
            else:
                # 점 마커
                painter.setPen(QPen(color, 3))
                painter.drawLine(int(x), self.ruler_height, int(x), self.height())
                
                # 마커 아이콘 (작은 다이아몬드)
                diamond_size = 6
                diamond_points = [
                    QPoint(int(x), self.ruler_height - diamond_size),
                    QPoint(int(x) + diamond_size, self.ruler_height),
                    QPoint(int(x), self.ruler_height + diamond_size),
                    QPoint(int(x) - diamond_size, self.ruler_height)
                ]
                painter.setBrush(QBrush(color))
                painter.drawPolygon(diamond_points)
        
    def mousePressEvent(self, event):
        """마우스 프레스 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 핸드 툴 모드 체크
            if self.hand_tool_active:
                self.hand_drag_start = event.position().toPoint()
                self.hand_drag_last_offset = self.timeline_offset_x
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                return
                
            # 재생 헤드 영역 클릭 확인
            pixels_per_frame = self.zoom_level * 2
            playhead_x = (self.playhead_position * pixels_per_frame) - self.timeline_offset_x
            
            if abs(event.position().x() - playhead_x) < 10 and event.position().y() < self.ruler_height:
                # 재생 헤드 드래그 시작
                self.is_playhead_dragging = True
                return
                
            # 룰러 클릭 - 재생 헤드 이동
            if event.position().y() < self.ruler_height:
                adjusted_x = event.position().x() + self.timeline_offset_x
                new_frame = int(adjusted_x / pixels_per_frame)
                self.set_playhead_position(new_frame)
                return
                
            # 트랙 추가 버튼 클릭 확인
            if self.track_count < self.max_tracks:
                add_track_y = self.ruler_height + self.track_count * self.tracks_height
                plus_rect = QRect(10, add_track_y + 10, 30, 20)
                if plus_rect.contains(event.position().toPoint()):
                    self.add_track()
                    return
                
            # 클립 선택/드래그
            clicked_clip = self.get_clip_at_position(event.position())
            
            if clicked_clip:
                # 크기 조정 영역인지 확인 (완전 비활성화)
                resize_edge = None  # 크기 조정 기능 비활성화
                
                if resize_edge:
                    # 크기 조정 시작
                    print(f"[크기조정 시작] 클립: {clicked_clip.name}, 가장자리: {resize_edge}, 원래 길이: {clicked_clip.duration}")
                    self.is_resizing = True
                    self.resize_clip = clicked_clip
                    self.resize_edge = resize_edge
                    self.original_duration = clicked_clip.duration
                    self.drag_start_pos = event.position()
                else:
                    # 일반 드래그
                    # 클립 선택
                    if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                        self.selected_clips.clear()
                        
                    if clicked_clip not in self.selected_clips:
                        print(f"[클립 선택] {clicked_clip.name} - 길이: {clicked_clip.duration}")
                        self.selected_clips.append(clicked_clip)
                        
                    print(f"[선택 변경 시그널] 클립 수: {len(self.selected_clips)}")
                    self.selection_changed.emit(self.selected_clips[:])
                    
                    # 드래그 시작
                    self.is_dragging = True
                    self.drag_start_pos = event.position()
                    self.drag_clip = clicked_clip
                    self.drag_original_start_frame = clicked_clip.start_frame
                    self.drag_original_track = clicked_clip.track
                    
                    # 단순화된 드래그 (오프셋 제거)
                    print(f"[드래그 시작] 클립: {clicked_clip.name}, 시작 프레임: {clicked_clip.start_frame}")
            else:
                # 빈 공간 클릭 - 선택 해제
                self.selected_clips.clear()
                self.selection_changed.emit([])
                
        elif event.button() == Qt.MouseButton.RightButton:
            # 우클릭 메뉴
            self.show_context_menu(event.position())
            
        self.update()
        
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트"""
        if self.hand_tool_active and event.buttons() & Qt.MouseButton.LeftButton:
            # 핸드 툴 드래그
            delta_x = event.position().x() - self.hand_drag_start.x()
            new_offset = self.hand_drag_last_offset - delta_x
            self.timeline_offset_x = max(0, min(new_offset, self.timeline_width - self.viewport_width))
            self.update()
            return
            
        elif self.is_playhead_dragging:
            # 재생 헤드 드래그
            pixels_per_frame = self.zoom_level * 2
            adjusted_x = event.position().x() + self.timeline_offset_x
            new_frame = max(0, int(adjusted_x / pixels_per_frame))
            self.set_playhead_position(new_frame)
            
        elif self.is_resizing and self.resize_clip:
            # 클립 크기 조정
            pixels_per_frame = self.zoom_level * 2
            delta_x = event.position().x() - self.drag_start_pos.x()
            delta_frames = int(delta_x / pixels_per_frame)
            
            if self.resize_edge == 'right':
                # 오른쪽 가장자리 - 길이 조정
                new_duration = max(30, self.original_duration + delta_frames)  # 최소 1초
                old_duration = self.resize_clip.duration
                self.resize_clip.duration = new_duration
                if abs(new_duration - old_duration) > 10:
                    print(f"[크기조정 우측] {old_duration} -> {new_duration} (델타: {delta_frames})")
            elif self.resize_edge == 'left':
                # 왼쪽 가장자리 - 시작점과 길이 조정
                new_start_frame = max(0, self.resize_clip.start_frame + delta_frames)
                duration_change = self.resize_clip.start_frame - new_start_frame
                new_duration = max(30, self.original_duration + duration_change)
                
                old_start = self.resize_clip.start_frame
                old_duration = self.resize_clip.duration
                self.resize_clip.start_frame = new_start_frame
                self.resize_clip.duration = new_duration
                if abs(new_duration - old_duration) > 10:
                    print(f"[크기조정 좌측] 시작: {old_start} -> {new_start_frame}, 길이: {old_duration} -> {new_duration}")
            
        elif self.is_dragging and self.drag_clip:
            # 클립 드래그 - 단순화된 버전
            pixels_per_frame = self.zoom_level * 2
            
            # 드래그 시작점에서의 이동 거리 계산
            mouse_delta_x = event.position().x() - self.drag_start_pos.x()
            frame_delta = int(mouse_delta_x / pixels_per_frame)
            
            # 새로운 시작 프레임 = 원래 위치 + 이동 거리
            target_start_frame = max(0, self.drag_original_start_frame + frame_delta)
            
            # 트랙 변경 계산
            mouse_delta_y = event.position().y() - self.drag_start_pos.y()
            track_delta = int(mouse_delta_y / self.tracks_height)
            new_track = max(0, min(self.drag_original_track + track_delta, self.track_count - 1))
            
            # 클립 위치 업데이트
            old_start_frame = self.drag_clip.start_frame
            self.drag_clip.start_frame = target_start_frame
            self.drag_clip.track = new_track
            
            # 디버그 출력
            if abs(target_start_frame - old_start_frame) > 5:
                print(f"[단순 드래그] 클립: {self.drag_clip.name}, {old_start_frame} -> {target_start_frame} (델타: {frame_delta})")
            
            self.clip_moved.emit(self.drag_clip, target_start_frame, new_track)
        else:
            # 마우스 커서 변경 (크기 조정 완전 비활성화)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
        self.update()
        
    def mouseReleaseEvent(self, event):
        """마우스 릴리즈 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 드래그가 끝났을 때 이동 명령 생성
            if self.is_dragging and self.drag_clip:
                if (self.drag_clip.start_frame != self.drag_original_start_frame or 
                    self.drag_clip.track != self.drag_original_track):
                    # 실제로 이동된 경우에만 명령 생성
                    move_cmd = MoveClipCommand(
                        self.drag_clip,
                        self.drag_original_start_frame,
                        self.drag_original_track,
                        self.drag_clip.start_frame,
                        self.drag_clip.track
                    )
                    self.command_manager.execute_command(move_cmd)
            
            # 크기 조정이 끝났을 때
            if self.is_resizing and self.resize_clip:
                if self.resize_clip.duration != self.original_duration:
                    # TODO: 크기 조정 명령 추가 (나중에 구현)
                    pass
                    
            self.is_dragging = False
            self.is_playhead_dragging = False
            self.is_resizing = False
            self.drag_clip = None
            self.resize_clip = None
            self.drag_offset_x = 0
            
            # 핸드 툴 커서 복원
            if self.hand_tool_active:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            
    def keyPressEvent(self, event):
        """키보드 이벤트"""
        if event.key() == Qt.Key.Key_Space:
            # 스페이스 - 재생/정지 (현재는 재생 헤드만 이동)
            self.playhead_position += 30  # 1초 이동
            self.playhead_changed.emit(self.playhead_position)
            
        elif event.key() == Qt.Key.Key_S:
            # S - 선택된 클립 분할
            self.split_selected_clips()
            
        elif event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            # Delete - 선택된 클립 삭제
            self.delete_selected_clips()
            
        elif event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+Z - 실행 취소
            self.command_manager.undo()
            
        elif event.key() == Qt.Key.Key_Y and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+Y - 다시 실행
            self.command_manager.redo()
            
        elif event.key() == Qt.Key.Key_Left:
            # 왼쪽 화살표 - 이전 프레임
            self.playhead_position = max(0, self.playhead_position - 1)
            self.playhead_changed.emit(self.playhead_position)
            
        elif event.key() == Qt.Key.Key_Right:
            # 오른쪽 화살표 - 다음 프레임
            self.playhead_position += 1
            self.playhead_changed.emit(self.playhead_position)
            
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            # 줌 인
            self.zoom_in()
            
        elif event.key() == Qt.Key.Key_Minus:
            # 줌 아웃
            self.zoom_out()
            
        elif event.key() == Qt.Key.Key_M:
            # M - 마커 추가
            self.add_marker_at_playhead()
            
        elif event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+C - 복사
            self.copy_selected_clips()
            
        elif event.key() == Qt.Key.Key_X and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+X - 잘라내기
            self.cut_selected_clips()
            
        elif event.key() == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+V - 붙여넣기
            self.paste_clips()
            
        elif event.key() == Qt.Key.Key_D and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+D - 복제
            self.duplicate_selected_clips()
            
        elif event.key() == Qt.Key.Key_H:
            # H - 핸드 툴 토글
            self.toggle_hand_tool()
            
        elif event.key() == Qt.Key.Key_Home:
            # Home - 타임라인 처음으로
            self.timeline_offset_x = 0
            self.playhead_position = 0
            self.playhead_changed.emit(0)
            
        elif event.key() == Qt.Key.Key_End:
            # End - 타임라인 끝으로
            if self.clips:
                last_frame = max(clip.start_frame + clip.duration for clip in self.clips)
                self.playhead_position = last_frame
                self.playhead_changed.emit(last_frame)
                
        elif event.key() == Qt.Key.Key_F and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+F - 전체 보기
            self.zoom_to_fit_all()
            
        elif event.key() == Qt.Key.Key_F and event.modifiers() & Qt.KeyboardModifier.AltModifier:
            # Alt+F - 선택 클립에 맞춤
            self.zoom_to_fit_selection()
            
        elif event.key() == Qt.Key.Key_0 and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+0 - 기본 줌 (100%)
            self.zoom_level = 1.0
                
        self.update()
        
    def wheelEvent(self, event):
        """마우스 휠 이벤트"""
        modifiers = event.modifiers()
        
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Ctrl + 휠 = 줌 (마우스 위치 기준)
            delta = event.angleDelta().y()
            
            # 마우스 위치 기준 줌
            mouse_x = event.position().x()
            
            # 줌 전 마우스 위치의 타임라인 좌표
            pixels_per_frame = self.zoom_level * 2
            old_frame_at_mouse = (mouse_x + self.timeline_offset_x) / pixels_per_frame
            
            # 줌 적용
            zoom_factor = 1.15 if delta > 0 else 1/1.15
            old_zoom = self.zoom_level
            new_zoom = self.zoom_level * zoom_factor
            self.zoom_level = max(new_zoom, 1e-10)  # 0에 가까워지는 것만 방지
            
            # 줌 후 새로운 픽셀/프레임 비율
            new_pixels_per_frame = self.zoom_level * 2
            
            # 마우스 위치가 같은 프레임을 가리키도록 오프셋 조정
            new_x_at_mouse = old_frame_at_mouse * new_pixels_per_frame
            self.timeline_offset_x = new_x_at_mouse - mouse_x
            
            # 오프셋 범위 제한
            self.timeline_offset_x = max(0, min(self.timeline_offset_x, 
                                              self.timeline_width - self.viewport_width))
            
            self.update()
            
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Shift + 휠 = 수평 스크롤
            delta = event.angleDelta().y()
            scroll_amount = delta * 3  # 스크롤 속도 증가
            self.pan_timeline(-scroll_amount)
        else:
            # 일반 휠 = 수직 스크롤 (기본 동작)
            super().wheelEvent(event)
            
    def toggle_hand_tool(self):
        """핸드 툴 토글"""
        self.hand_tool_active = not self.hand_tool_active
        if self.hand_tool_active:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
    def pan_timeline(self, delta_x):
        """타임라인 패닝"""
        self.timeline_offset_x = max(0, min(self.timeline_offset_x + delta_x, 
                                           self.timeline_width - self.viewport_width))
        self.update()
        
    def get_clip_at_position(self, pos):
        """주어진 위치의 클립 찾기"""
        pixels_per_frame = self.zoom_level * 2
        
        for clip in self.clips:
            x = (clip.start_frame * pixels_per_frame) - self.timeline_offset_x
            y = self.ruler_height + clip.track * self.tracks_height + 5
            width = clip.duration * pixels_per_frame
            height = self.tracks_height - 10
            
            clip_rect = QRect(int(x), int(y), int(width), int(height))
            
            if clip_rect.contains(pos.toPoint()):
                return clip
                
        return None
        
    def get_resize_edge(self, pos, clip):
        """클립 크기 조정 가능 영역인지 확인"""
        pixels_per_frame = self.zoom_level * 2
        x = (clip.start_frame * pixels_per_frame) - self.timeline_offset_x
        width = clip.duration * pixels_per_frame
        
        # 클립이 너무 작으면 크기 조정 비활성화
        if width < 30:  # 30픽셀 미만
            return None
        
        left_distance = abs(pos.x() - x)
        right_distance = abs(pos.x() - (x + width))
        
        # 매우 엄격한 임계값 (1픽셀)
        strict_threshold = 1
        
        # 왼쪽 가장자리 (정확히 가장자리에서만)
        if left_distance <= strict_threshold and pos.x() <= x + 2:
            print(f"[크기조정] 왼쪽 가장자리 감지, 거리: {left_distance:.1f}")
            return 'left'
        # 오른쪽 가장자리 (정확히 가장자리에서만)
        elif right_distance <= strict_threshold and pos.x() >= x + width - 2:
            print(f"[크기조정] 오른쪽 가장자리 감지, 거리: {right_distance:.1f}")
            return 'right'
        
        return None
        
    def show_context_menu(self, pos):
        """우클릭 컨텍스트 메뉴"""
        menu = QMenu(self)
        
        clicked_clip = self.get_clip_at_position(pos)
        
        if clicked_clip:
            # 클립 관련 메뉴
            split_action = menu.addAction("분할")
            split_action.triggered.connect(lambda: self.split_clip(clicked_clip))
            
            delete_action = menu.addAction("삭제")
            delete_action.triggered.connect(lambda: self.delete_clip(clicked_clip))
            
            menu.addSeparator()
            
            properties_action = menu.addAction("속성")
            properties_action.triggered.connect(lambda: self.show_clip_properties(clicked_clip))
        else:
            # 빈 공간 메뉴
            paste_action = menu.addAction("붙여넣기")
            paste_action.triggered.connect(self.paste_clips)
            
        menu.exec(self.mapToGlobal(pos.toPoint()))
        
    def add_clip(self, media_path, track=0, start_frame=None):
        """클립 추가"""
        if start_frame is None:
            start_frame = self.playhead_position
            
        # 클립 생성
        clip = TimelineClip(media_path, start_frame, track)
        
        # 실제 미디어 파일 정보로 길이 설정
        try:
            media_info = MediaAnalyzer.get_media_info(media_path)
            # 프레임 단위로 변환 (30fps 기준)
            clip.duration = media_info['duration_frames']
            clip.media_type = media_info['media_type']
            
            # 추가 정보 저장
            clip.original_duration = media_info['duration']
            clip.fps = media_info['fps']
            clip.width = media_info.get('width', 1920)
            clip.height = media_info.get('height', 1080)
            
        except Exception as e:
            print(f"미디어 분석 실패: {e}")
            # 기본값 설정
            clip.duration = 90  # 기본 3초
            clip.media_type = 'unknown'
        
        # 스냅 적용 (드롭 위치에서)
        if self.snap_enabled:
            start_frame = self.apply_snap(start_frame)
            
        clip.start_frame = start_frame
        clip.track = track
            
        # 명령을 통해 클립 추가
        add_cmd = AddClipCommand(self, clip, track, start_frame)
        self.command_manager.execute_command(add_cmd)
        
        return clip
        
    def find_next_available_position(self, track):
        """다음 사용 가능한 위치 찾기"""
        # 해당 트랙의 모든 클립 확인
        track_clips = [clip for clip in self.clips if clip.track == track]
        
        if not track_clips:
            return 0
            
        # 가장 마지막 클립 이후 위치 반환
        last_clip = max(track_clips, key=lambda c: c.start_frame + c.duration)
        return last_clip.start_frame + last_clip.duration
        
    def split_selected_clips(self):
        """선택된 클립들 분할"""
        for clip in self.selected_clips[:]:  # 복사본으로 반복
            self.split_clip(clip)
            
    def split_clip(self, clip):
        """클립 분할"""
        split_frame = self.playhead_position
        
        if clip.start_frame < split_frame < clip.start_frame + clip.duration:
            # 분할 명령 생성 및 실행
            split_cmd = SplitClipCommand(self, clip, split_frame)
            self.command_manager.execute_command(split_cmd)
            
    def delete_selected_clips(self):
        """선택된 클립들 삭제"""
        for clip in self.selected_clips[:]:  # 복사본으로 반복
            delete_cmd = DeleteClipCommand(self, clip)
            self.command_manager.execute_command(delete_cmd)
        self.selected_clips.clear()
        self.selection_changed.emit([])
        
    def delete_clip(self, clip):
        """클립 삭제"""
        delete_cmd = DeleteClipCommand(self, clip)
        self.command_manager.execute_command(delete_cmd)
        
    def show_clip_properties(self, clip):
        """클립 속성 표시"""
        # TODO: 속성 다이얼로그 구현
        pass
        
    def paste_clips(self):
        """클립 붙여넣기"""
        # TODO: 클립보드에서 클립 붙여넣기 구현
        pass
        
    def zoom_in(self):
        """줌 인"""
        self.zoom_level = self.zoom_level * 1.3  # 제한 없음
        self.update()
        
    def zoom_out(self):
        """줌 아웃"""
        self.zoom_level = max(self.zoom_level / 1.3, 1e-10)  # 0에 가까워지는 것만 방지
        self.update()
        
    def zoom_to_fit_all(self):
        """모든 클립이 보이도록 줌 조정"""
        if not self.clips:
            return
            
        # 모든 클립의 범위 계산
        min_frame = min(clip.start_frame for clip in self.clips)
        max_frame = max(clip.start_frame + clip.duration for clip in self.clips)
        
        # 여유 공간 추가 (10%)
        total_frames = max_frame - min_frame
        padding_frames = total_frames * 0.1
        
        # 줌 레벨 계산
        available_width = self.width() - 100  # 여유 공간
        pixels_per_frame = available_width / (total_frames + padding_frames * 2)
        self.zoom_level = pixels_per_frame / 2  # 기본 배율이 2이므로 나누기
        
        # 오프셋 조정 (클립들이 중앙에 오도록)
        self.timeline_offset_x = (min_frame - padding_frames) * pixels_per_frame
        
        self.update()
        
    def zoom_to_fit_selection(self):
        """선택된 클립들이 보이도록 줌 조정"""
        if not self.selected_clips:
            return
            
        # 선택된 클립들의 범위 계산
        min_frame = min(clip.start_frame for clip in self.selected_clips)
        max_frame = max(clip.start_frame + clip.duration for clip in self.selected_clips)
        
        # 여유 공간 추가 (10%)
        total_frames = max_frame - min_frame
        padding_frames = max(total_frames * 0.1, 30)  # 최소 1초 여유
        
        # 줌 레벨 계산
        available_width = self.width() - 100
        pixels_per_frame = available_width / (total_frames + padding_frames * 2)
        self.zoom_level = pixels_per_frame / 2
        
        # 오프셋 조정
        self.timeline_offset_x = (min_frame - padding_frames) * pixels_per_frame
        
        self.update()
        
    def set_playhead_position(self, frame):
        """재생 헤드 위치 설정"""
        self.playhead_position = max(0, frame)
        self.playhead_changed.emit(self.playhead_position)
        self.update()
        
    def clear(self):
        """타임라인 초기화"""
        self.clips.clear()
        self.selected_clips.clear()
        self.playhead_position = 0
        self.marker_manager.clear_all_markers()
        self.update()
        
    def apply_snap(self, frame: int) -> int:
        """스냅 기능 적용"""
        pixels_per_frame = self.zoom_level * 2
        snap_threshold_frames = int(self.snap_threshold / pixels_per_frame)
        
        # 스냅 대상들
        snap_targets = []
        
        # 다른 클립들의 시작/끝 지점
        for clip in self.clips:
            snap_targets.append(clip.start_frame)
            snap_targets.append(clip.start_frame + clip.duration)
            
        # 마커들
        for marker in self.marker_manager.markers:
            snap_targets.append(marker.frame)
            if marker.is_range_marker():
                snap_targets.append(marker.get_end_frame())
                
        # 재생 헤드
        snap_targets.append(self.playhead_position)
        
        # 가장 가까운 스냅 대상 찾기
        closest_target = None
        closest_distance = float('inf')
        
        for target in snap_targets:
            distance = abs(frame - target)
            if distance < snap_threshold_frames and distance < closest_distance:
                closest_distance = distance
                closest_target = target
                
        return closest_target if closest_target is not None else frame
        
    def add_marker_at_playhead(self):
        """재생 헤드 위치에 마커 추가"""
        self.marker_manager.add_marker(self.playhead_position)
        
    def copy_selected_clips(self):
        """선택된 클립들 복사"""
        if self.selected_clips:
            self.clipboard_manager.copy_clips(self.selected_clips)
            
    def cut_selected_clips(self):
        """선택된 클립들 잘라내기"""
        if self.selected_clips:
            self.clipboard_manager.cut_clips(self.selected_clips)
            # 잘라낸 클립들 삭제
            self.delete_selected_clips()
            
    def paste_clips(self):
        """클립들 붙여넣기"""
        pasted_clips = self.clipboard_manager.paste_clips(self, self.playhead_position)
        if pasted_clips:
            # 붙여넣은 클립들 선택
            self.selected_clips = pasted_clips
            self.selection_changed.emit(self.selected_clips[:])
            
    def duplicate_selected_clips(self):
        """선택된 클립들 복제"""
        if self.selected_clips:
            duplicated_clips = self.clipboard_manager.duplicate_clips(self.selected_clips, self)
            # 복제된 클립들 선택
            self.selected_clips = duplicated_clips
            self.selection_changed.emit(self.selected_clips[:])
            
    def toggle_snap(self):
        """스냅 기능 토글"""
        self.snap_enabled = not self.snap_enabled
        
    def set_snap_threshold(self, threshold: int):
        """스냅 임계값 설정"""
        self.snap_threshold = threshold
        
    def add_track(self):
        """트랙 추가"""
        if self.track_count < self.max_tracks:
            self.track_count += 1
            # 위젯 크기 조정
            new_height = self.ruler_height + self.track_count * self.tracks_height + 100
            self.setMinimumHeight(new_height)
            self.update()
            
    def remove_track(self, track_index=None):
        """트랙 제거"""
        if self.track_count > 1:  # 최소 1개 트랙은 유지
            if track_index is None:
                track_index = self.track_count - 1  # 마지막 트랙 제거
                
            # 해당 트랙의 클립들을 다른 트랙으로 이동 또는 삭제
            clips_to_remove = [clip for clip in self.clips if clip.track == track_index]
            for clip in clips_to_remove:
                self.clips.remove(clip)
                
            # 더 높은 트랙의 클립들을 한 트랙씩 아래로 이동
            for clip in self.clips:
                if clip.track > track_index:
                    clip.track -= 1
                    
            self.track_count -= 1
            new_height = self.ruler_height + self.track_count * self.tracks_height + 100
            self.setMinimumHeight(new_height)
            self.update()
        
    def dragEnterEvent(self, event):
        """드래그 진입 이벤트"""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dragLeaveEvent(self, event):
        """드래그 떠남 이벤트"""
        # 드롭 프리뷰 제거
        self.drag_drop_frame = None
        self.drag_drop_track = None
        self.update()
            
    def dragMoveEvent(self, event):
        """드래그 이동 이벤트"""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            # 드롭 위치 계산하여 시각적 피드백
            pixels_per_frame = self.zoom_level * 2
            drop_frame = max(0, int(event.position().x() / pixels_per_frame))
            drop_track = max(0, min(int((event.position().y() - self.ruler_height) / self.tracks_height), 
                                   self.track_count - 1))
            
            # 드롭 위치 저장 (시각적 표시용)
            self.drag_drop_frame = drop_frame
            self.drag_drop_track = drop_track
            self.update()  # 화면 갱신
            
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """드롭 이벤트"""
        # 드롭 위치 계산
        pixels_per_frame = self.zoom_level * 2
        drop_frame = max(0, int(event.position().x() / pixels_per_frame))
        drop_track = max(0, min(int((event.position().y() - self.ruler_height) / self.tracks_height), 
                               self.track_count - 1))
        
        # 미디어 파일 경로 추출
        file_path = None
        
        if event.mimeData().hasUrls():
            # URL에서 파일 경로 추출
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                break
        elif event.mimeData().hasText():
            # 텍스트에서 파일 경로 추출
            file_path = event.mimeData().text()
            
        if file_path and os.path.exists(file_path):
            # 클립 추가
            self.add_clip(file_path, drop_track, drop_frame)
            event.acceptProposedAction()
        else:
            event.ignore()
            
        # 드롭 프리뷰 제거
        self.drag_drop_frame = None
        self.drag_drop_track = None
        self.update()
        
    def draw_drop_preview(self, painter):
        """드래그&드롭 프리뷰 그리기"""
        if self.drag_drop_frame is None or self.drag_drop_track is None:
            return
            
        pixels_per_frame = self.zoom_level * 2
        x = self.drag_drop_frame * pixels_per_frame
        y = self.ruler_height + self.drag_drop_track * self.tracks_height + 5
        width = 90 * pixels_per_frame  # 기본 3초 길이
        height = self.tracks_height - 10
        
        drop_rect = QRect(int(x), int(y), int(width), int(height))
        
        # 반투명 프리뷰 박스
        preview_color = QColor(76, 175, 80, 80)  # 반투명 초록색
        painter.fillRect(drop_rect, preview_color)
        
        # 점선 테두리
        painter.setPen(QPen(QColor(76, 175, 80), 2, Qt.PenStyle.DashLine))
        painter.drawRect(drop_rect)
        
        # 드롭 아이콘 (중앙에 + 표시)
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        center_x = drop_rect.center().x()
        center_y = drop_rect.center().y()
        
        # + 아이콘 그리기
        painter.drawLine(center_x - 10, center_y, center_x + 10, center_y)
        painter.drawLine(center_x, center_y - 10, center_x, center_y + 10)
        
    def get_selected_clips(self):
        """선택된 클립들 반환"""
        return self.selected_clips.copy()
        
    def get_clips(self):
        """모든 클립들 반환"""
        return self.clips.copy()
        
    def clear(self):
        """타임라인 초기화"""
        self.clips.clear()
        self.selected_clips.clear()
        self.playhead_position = 0
        self.marker_manager.clear_all_markers()
        self.update()