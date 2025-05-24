"""
BLOUcut 클립보드 관리자
클립 복사, 잘라내기, 붙여넣기 시스템
"""

import json
import copy
from typing import List, Dict, Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal

class ClipboardItem:
    """클립보드 아이템"""
    
    def __init__(self, clip_data: Dict, operation: str = "copy"):
        self.clip_data = clip_data  # 클립 데이터
        self.operation = operation  # "copy" 또는 "cut"
        self.relative_position = 0  # 첫 번째 클립을 기준으로 한 상대 위치
        
    def to_dict(self):
        return {
            "clip_data": self.clip_data,
            "operation": self.operation,
            "relative_position": self.relative_position
        }
        
    @classmethod
    def from_dict(cls, data):
        item = cls(data["clip_data"], data["operation"])
        item.relative_position = data.get("relative_position", 0)
        return item

class ClipboardManager(QObject):
    """클립보드 관리자"""
    
    # 시그널
    clipboard_changed = pyqtSignal()  # 클립보드 변경됨
    items_cut = pyqtSignal(list)  # 클립이 잘라내어짐
    items_copied = pyqtSignal(list)  # 클립이 복사됨
    items_pasted = pyqtSignal(list)  # 클립이 붙여넣어짐
    
    def __init__(self):
        super().__init__()
        self.clipboard_items: List[ClipboardItem] = []
        self.max_history = 10  # 최대 클립보드 히스토리
        self.clipboard_history: List[List[ClipboardItem]] = []
        
    def copy_clips(self, clips: List[Any]):
        """클립들 복사"""
        if not clips:
            return
            
        clipboard_items = []
        
        # 시작 프레임 기준점 찾기 (가장 빠른 클립)
        min_start_frame = min(clip.start_frame for clip in clips)
        
        for clip in clips:
            # 클립 데이터 직렬화
            clip_data = self.serialize_clip(clip)
            
            # 클립보드 아이템 생성
            item = ClipboardItem(clip_data, "copy")
            item.relative_position = clip.start_frame - min_start_frame
            
            clipboard_items.append(item)
            
        # 클립보드에 저장
        self.set_clipboard_items(clipboard_items)
        self.items_copied.emit(clips)
        
    def cut_clips(self, clips: List[Any]):
        """클립들 잘라내기"""
        if not clips:
            return
            
        clipboard_items = []
        
        # 시작 프레임 기준점 찾기
        min_start_frame = min(clip.start_frame for clip in clips)
        
        for clip in clips:
            # 클립 데이터 직렬화
            clip_data = self.serialize_clip(clip)
            
            # 클립보드 아이템 생성
            item = ClipboardItem(clip_data, "cut")
            item.relative_position = clip.start_frame - min_start_frame
            
            clipboard_items.append(item)
            
        # 클립보드에 저장
        self.set_clipboard_items(clipboard_items)
        self.items_cut.emit(clips)
        
    def paste_clips(self, timeline, target_frame: int = None, target_track: int = 0) -> List[Any]:
        """클립들 붙여넣기"""
        if not self.clipboard_items:
            return []
            
        if target_frame is None:
            target_frame = getattr(timeline, 'playhead_position', 0)
            
        pasted_clips = []
        
        for item in self.clipboard_items:
            # 클립 복원
            new_clip = self.deserialize_clip(item.clip_data)
            if new_clip:
                # 위치 조정
                new_clip.start_frame = target_frame + item.relative_position
                new_clip.track = target_track
                
                # 트랙이 범위를 벗어나면 조정
                if hasattr(timeline, 'track_count'):
                    if new_clip.track >= timeline.track_count:
                        new_clip.track = timeline.track_count - 1
                        
                pasted_clips.append(new_clip)
                
        # 타임라인에 추가
        for clip in pasted_clips:
            timeline.clips.append(clip)
            
        if pasted_clips:
            timeline.update()
            self.items_pasted.emit(pasted_clips)
            
        return pasted_clips
        
    def duplicate_clips(self, clips: List[Any], timeline, offset_frames: int = 30) -> List[Any]:
        """클립들 복제"""
        if not clips:
            return []
            
        duplicated_clips = []
        
        for clip in clips:
            # 클립 데이터 직렬화/역직렬화로 복제
            clip_data = self.serialize_clip(clip)
            new_clip = self.deserialize_clip(clip_data)
            
            if new_clip:
                # 위치 조정 (원본 뒤에 배치)
                new_clip.start_frame = clip.start_frame + clip.duration + offset_frames
                new_clip.track = clip.track
                
                duplicated_clips.append(new_clip)
                
        # 타임라인에 추가
        for clip in duplicated_clips:
            timeline.clips.append(clip)
            
        if duplicated_clips:
            timeline.update()
            
        return duplicated_clips
        
    def serialize_clip(self, clip) -> Dict:
        """클립 직렬화"""
        try:
            clip_data = {
                "name": clip.name,
                "media_path": clip.media_path,
                "start_frame": clip.start_frame,
                "duration": clip.duration,
                "track": clip.track,
                "media_type": getattr(clip, 'media_type', 'video'),
                "properties": {}
            }
            
            # 클립 속성들 복사
            properties_to_copy = [
                'x', 'y', 'width', 'height', 'rotation', 'opacity',
                'volume', 'speed', 'reverse', 'effects'
            ]
            
            for prop in properties_to_copy:
                if hasattr(clip, prop):
                    clip_data["properties"][prop] = getattr(clip, prop)
                    
            return clip_data
            
        except Exception as e:
            print(f"클립 직렬화 오류: {e}")
            return {}
            
    def deserialize_clip(self, clip_data: Dict):
        """클립 역직렬화"""
        try:
            # TimelineClip 클래스 import (순환 import 방지)
            from ..timeline.timeline_clip import TimelineClip
            
            # 새 클립 생성
            new_clip = TimelineClip(
                clip_data["media_path"],
                clip_data["start_frame"],
                clip_data["track"]
            )
            
            # 기본 속성 설정
            new_clip.name = clip_data["name"]
            new_clip.duration = clip_data["duration"]
            
            # 추가 속성 설정
            properties = clip_data.get("properties", {})
            for prop, value in properties.items():
                if hasattr(new_clip, prop):
                    setattr(new_clip, prop, value)
                    
            return new_clip
            
        except Exception as e:
            print(f"클립 역직렬화 오류: {e}")
            return None
            
    def set_clipboard_items(self, items: List[ClipboardItem]):
        """클립보드 아이템 설정"""
        # 현재 클립보드를 히스토리에 저장
        if self.clipboard_items:
            self.clipboard_history.insert(0, self.clipboard_items[:])
            
            # 히스토리 크기 제한
            if len(self.clipboard_history) > self.max_history:
                self.clipboard_history = self.clipboard_history[:self.max_history]
                
        # 새 클립보드 설정
        self.clipboard_items = items[:]
        self.clipboard_changed.emit()
        
    def get_clipboard_items(self) -> List[ClipboardItem]:
        """클립보드 아이템 가져오기"""
        return self.clipboard_items[:]
        
    def has_clipboard_data(self) -> bool:
        """클립보드에 데이터가 있는지 확인"""
        return len(self.clipboard_items) > 0
        
    def clear_clipboard(self):
        """클립보드 비우기"""
        self.clipboard_items.clear()
        self.clipboard_changed.emit()
        
    def get_clipboard_info(self) -> Dict:
        """클립보드 정보"""
        if not self.clipboard_items:
            return {"count": 0, "operation": "", "types": []}
            
        # 클립 타입 분석
        types = []
        for item in self.clipboard_items:
            media_type = item.clip_data.get("media_type", "video")
            if media_type not in types:
                types.append(media_type)
                
        # 작업 타입 (모든 아이템이 같은 작업이어야 함)
        operations = list(set(item.operation for item in self.clipboard_items))
        operation = operations[0] if len(operations) == 1 else "mixed"
        
        return {
            "count": len(self.clipboard_items),
            "operation": operation,
            "types": types
        }
        
    def paste_special(self, timeline, options: Dict) -> List[Any]:
        """특별 붙여넣기"""
        if not self.clipboard_items:
            return []
            
        target_frame = options.get("target_frame", getattr(timeline, 'playhead_position', 0))
        target_track = options.get("target_track", 0)
        paste_properties = options.get("paste_properties", True)
        paste_effects = options.get("paste_effects", True)
        time_offset = options.get("time_offset", 0)
        
        pasted_clips = []
        
        for item in self.clipboard_items:
            # 클립 복원
            new_clip = self.deserialize_clip(item.clip_data)
            if new_clip:
                # 위치 조정
                new_clip.start_frame = target_frame + item.relative_position + time_offset
                new_clip.track = target_track
                
                # 속성 복사 옵션 적용
                if not paste_properties:
                    # 기본 속성만 유지, 변형 속성 제거
                    new_clip.x = 0
                    new_clip.y = 0
                    new_clip.rotation = 0
                    new_clip.opacity = 1.0
                    
                if not paste_effects:
                    # 효과 제거
                    new_clip.effects = []
                    
                pasted_clips.append(new_clip)
                
        # 타임라인에 추가
        for clip in pasted_clips:
            timeline.clips.append(clip)
            
        if pasted_clips:
            timeline.update()
            self.items_pasted.emit(pasted_clips)
            
        return pasted_clips
        
    def export_clipboard(self) -> str:
        """클립보드를 JSON으로 내보내기"""
        try:
            data = {
                "version": "1.0",
                "items": [item.to_dict() for item in self.clipboard_items]
            }
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"클립보드 내보내기 오류: {e}")
            return ""
            
    def import_clipboard(self, json_data: str) -> bool:
        """JSON에서 클립보드 가져오기"""
        try:
            data = json.loads(json_data)
            
            items = []
            for item_data in data.get("items", []):
                item = ClipboardItem.from_dict(item_data)
                items.append(item)
                
            self.set_clipboard_items(items)
            return True
            
        except Exception as e:
            print(f"클립보드 가져오기 오류: {e}")
            return False
            
    def get_history_item(self, index: int) -> Optional[List[ClipboardItem]]:
        """히스토리에서 아이템 가져오기"""
        if 0 <= index < len(self.clipboard_history):
            return self.clipboard_history[index][:]
        return None
        
    def restore_from_history(self, index: int) -> bool:
        """히스토리에서 복원"""
        history_items = self.get_history_item(index)
        if history_items:
            self.clipboard_items = history_items
            self.clipboard_changed.emit()
            return True
        return False 