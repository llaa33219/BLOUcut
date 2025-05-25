"""
BLOUcut 키프레임 시스템
애니메이션과 시간에 따른 속성 변화를 관리
"""

import json
import math
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

class InterpolationType(Enum):
    """보간 타입"""
    LINEAR = "linear"
    EASE_IN = "ease_in" 
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BEZIER = "bezier"
    HOLD = "hold"  # 이전 값 유지

class Keyframe:
    """개별 키프레임"""
    
    def __init__(self, frame: int, value: Any, interpolation: InterpolationType = InterpolationType.LINEAR):
        self.frame = frame
        self.value = value
        self.interpolation = interpolation
        
        # 베지어 커브 제어점 (베지어 보간용)
        self.control_point_1 = (0.25, 0.1)
        self.control_point_2 = (0.25, 1.0)
        
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'frame': self.frame,
            'value': self.value,
            'interpolation': self.interpolation.value,
            'control_point_1': self.control_point_1,
            'control_point_2': self.control_point_2
        }
        
    @classmethod
    def from_dict(cls, data):
        """딕셔너리에서 생성"""
        keyframe = cls(
            data['frame'],
            data['value'],
            InterpolationType(data.get('interpolation', 'linear'))
        )
        keyframe.control_point_1 = tuple(data.get('control_point_1', (0.25, 0.1)))
        keyframe.control_point_2 = tuple(data.get('control_point_2', (0.25, 1.0)))
        return keyframe

class KeyframeTrack:
    """키프레임 트랙 (하나의 속성에 대한 키프레임들)"""
    
    def __init__(self, property_name: str):
        self.property_name = property_name
        self.keyframes: List[Keyframe] = []
        self.enabled = True
        
    def add_keyframe(self, frame: int, value: Any, interpolation: InterpolationType = InterpolationType.LINEAR):
        """키프레임 추가"""
        # 같은 프레임의 키프레임이 있으면 제거
        self.remove_keyframe_at_frame(frame)
        
        keyframe = Keyframe(frame, value, interpolation)
        self.keyframes.append(keyframe)
        
        # 프레임 순으로 정렬
        self.keyframes.sort(key=lambda kf: kf.frame)
        
        print(f"[키프레임] {self.property_name}: 프레임 {frame}에 값 {value} 추가")
        
    def remove_keyframe_at_frame(self, frame: int):
        """특정 프레임의 키프레임 제거"""
        self.keyframes = [kf for kf in self.keyframes if kf.frame != frame]
        
    def get_value_at_frame(self, frame: int) -> Any:
        """특정 프레임에서의 값 계산 (보간 적용)"""
        if not self.enabled or not self.keyframes:
            return None
            
        # 정확한 키프레임이 있는지 확인
        for keyframe in self.keyframes:
            if keyframe.frame == frame:
                return keyframe.value
                
        # 키프레임들을 프레임순으로 정렬되어 있다고 가정
        # 이전/이후 키프레임 찾기
        prev_keyframe = None
        next_keyframe = None
        
        for keyframe in self.keyframes:
            if keyframe.frame < frame:
                prev_keyframe = keyframe
            elif keyframe.frame > frame and next_keyframe is None:
                next_keyframe = keyframe
                break
                
        # 보간 계산
        if prev_keyframe is None:
            # 첫 번째 키프레임 이전
            return self.keyframes[0].value if self.keyframes else None
        elif next_keyframe is None:
            # 마지막 키프레임 이후
            return prev_keyframe.value
        else:
            # 두 키프레임 사이 - 보간
            return self._interpolate(prev_keyframe, next_keyframe, frame)
            
    def _interpolate(self, prev_kf: Keyframe, next_kf: Keyframe, frame: int) -> Any:
        """두 키프레임 사이 보간"""
        # 진행률 계산 (0.0 ~ 1.0)
        progress = (frame - prev_kf.frame) / (next_kf.frame - prev_kf.frame)
        
        # HOLD 타입이면 이전 값 유지
        if prev_kf.interpolation == InterpolationType.HOLD:
            return prev_kf.value
            
        # 보간 타입에 따라 진행률 조정
        if prev_kf.interpolation == InterpolationType.EASE_IN:
            progress = progress * progress
        elif prev_kf.interpolation == InterpolationType.EASE_OUT:
            progress = 1 - (1 - progress) * (1 - progress)
        elif prev_kf.interpolation == InterpolationType.EASE_IN_OUT:
            if progress < 0.5:
                progress = 2 * progress * progress
            else:
                progress = 1 - 2 * (1 - progress) * (1 - progress)
        elif prev_kf.interpolation == InterpolationType.BEZIER:
            progress = self._bezier_interpolation(progress, prev_kf.control_point_1, prev_kf.control_point_2)
            
        # 값 타입에 따른 보간
        return self._interpolate_values(prev_kf.value, next_kf.value, progress)
        
    def _interpolate_values(self, start_value: Any, end_value: Any, progress: float) -> Any:
        """값 타입에 따른 보간"""
        # 숫자 타입
        if isinstance(start_value, (int, float)) and isinstance(end_value, (int, float)):
            return start_value + (end_value - start_value) * progress
            
        # 리스트/튜플 타입 (위치, 크기, 색상 등)
        elif isinstance(start_value, (list, tuple)) and isinstance(end_value, (list, tuple)):
            if len(start_value) == len(end_value):
                result = []
                for i in range(len(start_value)):
                    if isinstance(start_value[i], (int, float)) and isinstance(end_value[i], (int, float)):
                        result.append(start_value[i] + (end_value[i] - start_value[i]) * progress)
                    else:
                        result.append(start_value[i] if progress < 0.5 else end_value[i])
                return type(start_value)(result)
                
        # 기타 타입은 중간 지점에서 전환
        return start_value if progress < 0.5 else end_value
        
    def _bezier_interpolation(self, t: float, cp1: Tuple[float, float], cp2: Tuple[float, float]) -> float:
        """베지어 커브 보간"""
        # 3차 베지어 커브: P(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
        # P₀ = (0,0), P₃ = (1,1), P₁ = cp1, P₂ = cp2
        
        # X 좌표로 t 값 찾기 (근사)
        x_target = t
        t_estimate = t
        
        for _ in range(10):  # 뉴턴-랩슨 방법으로 근사
            x_current = 3 * (1 - t_estimate) * (1 - t_estimate) * t_estimate * cp1[0] + \
                       3 * (1 - t_estimate) * t_estimate * t_estimate * cp2[0] + \
                       t_estimate * t_estimate * t_estimate
                       
            if abs(x_current - x_target) < 0.001:
                break
                
            # 미분값 계산
            dx_dt = 3 * (1 - t_estimate) * (1 - t_estimate) * cp1[0] - \
                   6 * (1 - t_estimate) * t_estimate * cp1[0] + \
                   3 * (1 - t_estimate) * t_estimate * cp2[0] + \
                   3 * t_estimate * t_estimate * (cp2[0] - cp1[0]) + \
                   3 * t_estimate * t_estimate
                   
            if abs(dx_dt) > 0.001:
                t_estimate = t_estimate - (x_current - x_target) / dx_dt
                t_estimate = max(0, min(1, t_estimate))
                
        # Y 좌표 계산
        y = 3 * (1 - t_estimate) * (1 - t_estimate) * t_estimate * cp1[1] + \
            3 * (1 - t_estimate) * t_estimate * t_estimate * cp2[1] + \
            t_estimate * t_estimate * t_estimate
            
        return max(0, min(1, y))
        
    def has_keyframes(self) -> bool:
        """키프레임이 있는지 확인"""
        return len(self.keyframes) > 0
        
    def get_keyframe_frames(self) -> List[int]:
        """모든 키프레임의 프레임 번호 반환"""
        return [kf.frame for kf in self.keyframes]
        
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'property_name': self.property_name,
            'enabled': self.enabled,
            'keyframes': [kf.to_dict() for kf in self.keyframes]
        }
        
    @classmethod
    def from_dict(cls, data):
        """딕셔너리에서 생성"""
        track = cls(data['property_name'])
        track.enabled = data.get('enabled', True)
        track.keyframes = [Keyframe.from_dict(kf_data) for kf_data in data.get('keyframes', [])]
        return track

class KeyframeManager:
    """키프레임 관리자"""
    
    def __init__(self):
        self.tracks: Dict[str, KeyframeTrack] = {}  # property_name -> KeyframeTrack
        
    def add_keyframe(self, property_name: str, frame: int, value: Any, 
                    interpolation: InterpolationType = InterpolationType.LINEAR):
        """키프레임 추가"""
        if property_name not in self.tracks:
            self.tracks[property_name] = KeyframeTrack(property_name)
            
        self.tracks[property_name].add_keyframe(frame, value, interpolation)
        
    def remove_keyframe(self, property_name: str, frame: int):
        """키프레임 제거"""
        if property_name in self.tracks:
            self.tracks[property_name].remove_keyframe_at_frame(frame)
            
    def get_value_at_frame(self, property_name: str, frame: int) -> Any:
        """특정 프레임에서의 속성 값 가져오기"""
        if property_name not in self.tracks:
            return None
        return self.tracks[property_name].get_value_at_frame(frame)
        
    def get_animated_properties(self) -> List[str]:
        """애니메이션이 있는 속성들 반환"""
        return [prop for prop, track in self.tracks.items() if track.has_keyframes()]
        
    def get_all_keyframe_frames(self) -> List[int]:
        """모든 키프레임 프레임들 반환 (중복 제거)"""
        frames = set()
        for track in self.tracks.values():
            frames.update(track.get_keyframe_frames())
        return sorted(list(frames))
        
    def has_keyframes_at_frame(self, frame: int) -> bool:
        """특정 프레임에 키프레임이 있는지 확인"""
        for track in self.tracks.values():
            if frame in track.get_keyframe_frames():
                return True
        return False
        
    def get_properties_with_keyframes_at_frame(self, frame: int) -> List[str]:
        """특정 프레임에 키프레임이 있는 속성들"""
        properties = []
        for prop_name, track in self.tracks.items():
            if frame in track.get_keyframe_frames():
                properties.append(prop_name)
        return properties
        
    def clear_all_keyframes(self):
        """모든 키프레임 삭제"""
        self.tracks.clear()
        
    def clear_property_keyframes(self, property_name: str):
        """특정 속성의 모든 키프레임 삭제"""
        if property_name in self.tracks:
            del self.tracks[property_name]
            
    def to_dict(self):
        """딕셔너리로 변환 (저장용)"""
        return {
            'tracks': {prop: track.to_dict() for prop, track in self.tracks.items()}
        }
        
    @classmethod  
    def from_dict(cls, data):
        """딕셔너리에서 생성 (로드용)"""
        manager = cls()
        tracks_data = data.get('tracks', {})
        for prop_name, track_data in tracks_data.items():
            manager.tracks[prop_name] = KeyframeTrack.from_dict(track_data)
        return manager

# 애니메이션 가능한 속성들 정의
ANIMATABLE_PROPERTIES = {
    'transform': {
        'position_x': {'default': 0, 'range': (-2000, 2000), 'type': 'float'},
        'position_y': {'default': 0, 'range': (-2000, 2000), 'type': 'float'},
        'scale_x': {'default': 100, 'range': (1, 1000), 'type': 'float'},
        'scale_y': {'default': 100, 'range': (1, 1000), 'type': 'float'},
        'rotation': {'default': 0, 'range': (-360, 360), 'type': 'float'},
        'opacity': {'default': 100, 'range': (0, 100), 'type': 'float'},
    },
    'color': {
        'brightness': {'default': 0, 'range': (-100, 100), 'type': 'float'},
        'contrast': {'default': 0, 'range': (-100, 100), 'type': 'float'},
        'saturation': {'default': 0, 'range': (-100, 100), 'type': 'float'},
        'hue': {'default': 0, 'range': (-180, 180), 'type': 'float'},
        'gamma': {'default': 1.0, 'range': (0.1, 3.0), 'type': 'float'},
    },
    'audio': {
        'volume': {'default': 100, 'range': (0, 200), 'type': 'float'},
        'pitch': {'default': 0, 'range': (-12, 12), 'type': 'float'},
    }
}

def get_property_info(property_name: str) -> Optional[Dict]:
    """속성 정보 가져오기"""
    for category, properties in ANIMATABLE_PROPERTIES.items():
        if property_name in properties:
            return properties[property_name]
    return None 