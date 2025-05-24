"""
타임라인 클립 클래스
영상, 오디오, 이미지 클립의 정보를 담는 데이터 클래스
"""

import os
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

class ClipType(Enum):
    """클립 타입"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"

class TimelineClip(QObject):
    """타임라인 클립"""
    
    # 시그널
    properties_changed = pyqtSignal()
    
    def __init__(self, media_path, start_frame=0, track=0):
        super().__init__()
        
        # 기본 속성
        self.media_path = media_path
        self.name = os.path.basename(media_path) if media_path else "새 클립"
        self.start_frame = start_frame
        self.track = track
        self.duration = 90  # 기본 3초 (30fps 기준)
        
        # 클립 타입 결정
        self.clip_type = self._determine_clip_type()
        self.media_type = self.clip_type.value  # 호환성을 위한 문자열 타입
        
        # 변형 속성
        self.position_x = 0.0  # 화면상 X 위치 (정규화 -1.0 ~ 1.0)
        self.position_y = 0.0  # 화면상 Y 위치 (정규화 -1.0 ~ 1.0)
        self.scale_x = 1.0     # X 스케일
        self.scale_y = 1.0     # Y 스케일
        self.rotation = 0.0    # 회전각 (도)
        self.opacity = 1.0     # 불투명도 (0.0 ~ 1.0)
        
        # 오디오 속성
        self.volume = 1.0      # 볼륨 (0.0 ~ 2.0)
        self.fade_in = 0       # 페이드 인 프레임 수
        self.fade_out = 0      # 페이드 아웃 프레임 수
        
        # 색상 보정 속성
        self.brightness = 0.0  # 밝기 (-1.0 ~ 1.0)
        self.contrast = 0.0    # 대비 (-1.0 ~ 1.0)
        self.saturation = 0.0  # 채도 (-1.0 ~ 1.0)
        self.hue = 0.0         # 색조 (-180 ~ 180)
        
        # 효과 리스트
        self.effects = []
        
        # 선택 상태
        self.is_selected = False
        self.is_locked = False
        
    def _determine_clip_type(self):
        """파일 확장자로 클립 타입 결정"""
        if not self.media_path:
            return ClipType.TEXT
            
        ext = os.path.splitext(self.media_path)[1].lower()
        
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        audio_exts = ['.mp3', '.wav', '.aac', '.ogg', '.m4a', '.flac']
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
        
        if ext in video_exts:
            return ClipType.VIDEO
        elif ext in audio_exts:
            return ClipType.AUDIO
        elif ext in image_exts:
            return ClipType.IMAGE
        else:
            return ClipType.TEXT
            
    def get_end_frame(self):
        """클립 종료 프레임"""
        return self.start_frame + self.duration
        
    def set_position(self, x, y):
        """위치 설정"""
        self.position_x = max(-1.0, min(1.0, x))
        self.position_y = max(-1.0, min(1.0, y))
        self.properties_changed.emit()
        
    def set_scale(self, scale_x, scale_y=None):
        """스케일 설정"""
        if scale_y is None:
            scale_y = scale_x
        self.scale_x = max(0.1, min(5.0, scale_x))
        self.scale_y = max(0.1, min(5.0, scale_y))
        self.properties_changed.emit()
        
    def set_rotation(self, angle):
        """회전 설정"""
        self.rotation = angle % 360
        self.properties_changed.emit()
        
    def set_opacity(self, opacity):
        """불투명도 설정"""
        self.opacity = max(0.0, min(1.0, opacity))
        self.properties_changed.emit()
        
    def set_volume(self, volume):
        """볼륨 설정"""
        self.volume = max(0.0, min(2.0, volume))
        self.properties_changed.emit()
        
    def set_fade_in(self, frames):
        """페이드 인 설정"""
        self.fade_in = max(0, min(frames, self.duration // 2))
        self.properties_changed.emit()
        
    def set_fade_out(self, frames):
        """페이드 아웃 설정"""
        self.fade_out = max(0, min(frames, self.duration // 2))
        self.properties_changed.emit()
        
    def set_color_correction(self, brightness=None, contrast=None, saturation=None, hue=None):
        """색상 보정 설정"""
        if brightness is not None:
            self.brightness = max(-1.0, min(1.0, brightness))
        if contrast is not None:
            self.contrast = max(-1.0, min(1.0, contrast))
        if saturation is not None:
            self.saturation = max(-1.0, min(1.0, saturation))
        if hue is not None:
            self.hue = max(-180, min(180, hue))
        self.properties_changed.emit()
        
    def add_effect(self, effect):
        """효과 추가"""
        self.effects.append(effect)
        self.properties_changed.emit()
        
    def remove_effect(self, effect):
        """효과 제거"""
        if effect in self.effects:
            self.effects.remove(effect)
            self.properties_changed.emit()
            
    def clear_effects(self):
        """모든 효과 제거"""
        self.effects.clear()
        self.properties_changed.emit()
        
    def duplicate(self):
        """클립 복제"""
        new_clip = TimelineClip(self.media_path, self.start_frame, self.track)
        
        # 모든 속성 복사
        new_clip.duration = self.duration
        new_clip.position_x = self.position_x
        new_clip.position_y = self.position_y
        new_clip.scale_x = self.scale_x
        new_clip.scale_y = self.scale_y
        new_clip.rotation = self.rotation
        new_clip.opacity = self.opacity
        new_clip.volume = self.volume
        new_clip.fade_in = self.fade_in
        new_clip.fade_out = self.fade_out
        new_clip.brightness = self.brightness
        new_clip.contrast = self.contrast
        new_clip.saturation = self.saturation
        new_clip.hue = self.hue
        new_clip.effects = self.effects.copy()
        
        return new_clip
        
    def move_to(self, start_frame, track=None):
        """클립 이동"""
        self.start_frame = max(0, start_frame)
        if track is not None:
            self.track = max(0, track)
        self.properties_changed.emit()
        
    def resize(self, new_duration):
        """클립 길이 변경"""
        self.duration = max(1, new_duration)
        # 페이드가 클립 길이를 초과하지 않도록 조정
        max_fade = self.duration // 2
        self.fade_in = min(self.fade_in, max_fade)
        self.fade_out = min(self.fade_out, max_fade)
        self.properties_changed.emit()
        
    def split_at_frame(self, frame):
        """지정된 프레임에서 클립 분할"""
        if self.start_frame < frame < self.get_end_frame():
            # 두 번째 클립 생성
            second_clip = self.duplicate()
            
            # 첫 번째 클립 길이 조정
            first_duration = frame - self.start_frame
            self.duration = first_duration
            
            # 두 번째 클립 시작점과 길이 조정
            second_clip.start_frame = frame
            second_clip.duration = self.duration - first_duration
            
            return second_clip
        return None
        
    def contains_frame(self, frame):
        """프레임이 클립 범위 내에 있는지 확인"""
        return self.start_frame <= frame < self.get_end_frame()
        
    def overlaps_with(self, other_clip):
        """다른 클립과 겹치는지 확인"""
        if self.track != other_clip.track:
            return False
            
        return not (self.get_end_frame() <= other_clip.start_frame or 
                   other_clip.get_end_frame() <= self.start_frame)
                   
    def get_frame_at_time(self, timeline_frame):
        """타임라인 프레임에서 클립 내부의 프레임 번호 계산"""
        if not self.contains_frame(timeline_frame):
            return -1
        return timeline_frame - self.start_frame
        
    def to_dict(self):
        """딕셔너리로 변환 (저장용)"""
        return {
            'media_path': self.media_path,
            'name': self.name,
            'start_frame': self.start_frame,
            'track': self.track,
            'duration': self.duration,
            'clip_type': self.clip_type.value,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'scale_x': self.scale_x,
            'scale_y': self.scale_y,
            'rotation': self.rotation,
            'opacity': self.opacity,
            'volume': self.volume,
            'fade_in': self.fade_in,
            'fade_out': self.fade_out,
            'brightness': self.brightness,
            'contrast': self.contrast,
            'saturation': self.saturation,
            'hue': self.hue,
            'effects': [effect.to_dict() for effect in self.effects if hasattr(effect, 'to_dict')],
            'is_locked': self.is_locked
        }
        
    @classmethod
    def from_dict(cls, data):
        """딕셔너리에서 복원 (로드용)"""
        clip = cls(data['media_path'], data['start_frame'], data['track'])
        
        # 속성 복원
        clip.name = data.get('name', clip.name)
        clip.duration = data.get('duration', 90)
        clip.position_x = data.get('position_x', 0.0)
        clip.position_y = data.get('position_y', 0.0)
        clip.scale_x = data.get('scale_x', 1.0)
        clip.scale_y = data.get('scale_y', 1.0)
        clip.rotation = data.get('rotation', 0.0)
        clip.opacity = data.get('opacity', 1.0)
        clip.volume = data.get('volume', 1.0)
        clip.fade_in = data.get('fade_in', 0)
        clip.fade_out = data.get('fade_out', 0)
        clip.brightness = data.get('brightness', 0.0)
        clip.contrast = data.get('contrast', 0.0)
        clip.saturation = data.get('saturation', 0.0)
        clip.hue = data.get('hue', 0.0)
        clip.is_locked = data.get('is_locked', False)
        
        # 효과 복원 (나중에 구현)
        # clip.effects = [Effect.from_dict(effect_data) for effect_data in data.get('effects', [])]
        
        return clip
        
    def __str__(self):
        """문자열 표현"""
        return f"TimelineClip('{self.name}', start={self.start_frame}, duration={self.duration}, track={self.track})"
        
    def __repr__(self):
        return self.__str__() 