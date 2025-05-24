"""
BLOUcut 프로젝트 관리자
프로젝트 저장, 로드, 관리 기능
"""

import json
import os
from typing import Dict, Optional, List
from PyQt6.QtCore import QObject, pyqtSignal

class ProjectManager(QObject):
    """프로젝트 관리자"""
    
    # 시그널
    project_loaded = pyqtSignal(dict)  # 프로젝트 로드됨
    project_saved = pyqtSignal(str)    # 프로젝트 저장됨
    
    def __init__(self):
        super().__init__()
        self.current_project = None
        self.project_path = None
        self.timeline_widget = None
        
    def set_timeline_widget(self, timeline_widget):
        """타임라인 위젯 설정"""
        self.timeline_widget = timeline_widget
        
    def new_project(self, name: str = "새 프로젝트") -> Dict:
        """새 프로젝트 생성"""
        self.current_project = {
            "name": name,
            "version": "1.0",
            "settings": {
                "fps": 30,
                "resolution": [1920, 1080],
                "audio_sample_rate": 48000
            },
            "timeline": {
                "clips": [],
                "markers": [],
                "tracks": 3
            },
            "media": [],
            "created_time": "",
            "modified_time": ""
        }
        return self.current_project
        
    def load_project(self, file_path: str) -> Optional[Dict]:
        """프로젝트 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
                
            self.current_project = project_data
            self.project_path = file_path
            self.project_loaded.emit(project_data)
            return project_data
            
        except Exception as e:
            print(f"프로젝트 로드 오류: {e}")
            return None
            
    def save_project(self, file_path: str = None) -> bool:
        """프로젝트 저장"""
        if not self.current_project:
            return False
            
        if file_path:
            self.project_path = file_path
        elif not self.project_path:
            return False
            
        try:
            # 현재 타임라인 상태 저장
            if self.timeline_widget:
                self.current_project["timeline"]["clips"] = self.serialize_clips()
                self.current_project["timeline"]["markers"] = self.serialize_markers()
                
            with open(self.project_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_project, f, indent=2, ensure_ascii=False)
                
            self.project_saved.emit(self.project_path)
            return True
            
        except Exception as e:
            print(f"프로젝트 저장 오류: {e}")
            return False
            
    def serialize_clips(self) -> List[Dict]:
        """클립들을 직렬화"""
        if not self.timeline_widget:
            return []
            
        clips_data = []
        for clip in self.timeline_widget.clips:
            clip_data = {
                "name": clip.name,
                "media_path": clip.media_path,
                "start_frame": clip.start_frame,
                "duration": clip.duration,
                "track": clip.track,
                "media_type": getattr(clip, 'media_type', 'video'),
                "properties": {
                    "position_x": getattr(clip, 'position_x', 0),
                    "position_y": getattr(clip, 'position_y', 0),
                    "scale_x": getattr(clip, 'scale_x', 1.0),
                    "scale_y": getattr(clip, 'scale_y', 1.0),
                    "rotation": getattr(clip, 'rotation', 0),
                    "opacity": getattr(clip, 'opacity', 1.0),
                    "volume": getattr(clip, 'volume', 1.0),
                    "effects": getattr(clip, 'effects', [])
                }
            }
            clips_data.append(clip_data)
        return clips_data
        
    def serialize_markers(self) -> List[Dict]:
        """마커들을 직렬화"""
        if not self.timeline_widget or not hasattr(self.timeline_widget, 'marker_manager'):
            return []
            
        markers_data = []
        for marker in self.timeline_widget.marker_manager.markers:
            markers_data.append(marker.to_dict())
        return markers_data
        
    def get_current_project(self) -> Optional[Dict]:
        """현재 프로젝트 가져오기"""
        return self.current_project
        
    def serialize_project(self) -> Dict:
        """프로젝트를 JSON 직렬화용 데이터로 변환"""
        if not self.current_project:
            return {}
            
        # 현재 타임라인 상태 업데이트
        if self.timeline_widget:
            self.current_project["timeline"]["clips"] = self.serialize_clips()
            self.current_project["timeline"]["markers"] = self.serialize_markers()
            
        return self.current_project.copy()
        
    def set_project_name(self, name: str):
        """프로젝트 이름 설정"""
        if self.current_project:
            self.current_project["name"] = name
            
    def get_project_path(self) -> Optional[str]:
        """프로젝트 경로 가져오기"""
        return self.project_path
        
    def has_unsaved_changes(self) -> bool:
        """미저장 변경사항 여부"""
        # TODO: 실제 변경사항 추적 로직 구현
        return True  # 임시로 항상 True 반환 