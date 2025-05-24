"""
BLOUcut 타임라인 마커 시스템
프로젝트의 중요한 지점을 표시하고 관리하는 마커 시스템
"""

import json
from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor

class TimelineMarker:
    """타임라인 마커"""
    
    # 마커 타입
    MARKER_TYPES = {
        "default": {"name": "기본", "color": "#FFD700"},  # 금색
        "chapter": {"name": "챕터", "color": "#FF4444"},  # 빨강
        "note": {"name": "메모", "color": "#44FF44"},     # 초록
        "todo": {"name": "할일", "color": "#4444FF"},     # 파랑
        "warning": {"name": "주의", "color": "#FF8844"},  # 오렌지
        "sync": {"name": "동기화", "color": "#FF44FF"},   # 마젠타
        "edit": {"name": "편집점", "color": "#44FFFF"},   # 시아
        "custom": {"name": "사용자정의", "color": "#888888"}  # 회색
    }
    
    def __init__(self, frame: int, name: str = "", marker_type: str = "default", 
                 description: str = "", color: str = None):
        self.frame = frame  # 마커 위치 (프레임)
        self.name = name or f"마커 {frame}"
        self.marker_type = marker_type
        self.description = description
        self.color = color or self.MARKER_TYPES.get(marker_type, {}).get("color", "#FFD700")
        self.is_locked = False  # 잠금 여부
        self.duration = 0  # 마커 길이 (0이면 점 마커, >0이면 범위 마커)
        
    def get_color(self) -> QColor:
        """마커 색상 가져오기"""
        return QColor(self.color)
        
    def get_type_name(self) -> str:
        """마커 타입 이름"""
        return self.MARKER_TYPES.get(self.marker_type, {}).get("name", "기본")
        
    def is_range_marker(self) -> bool:
        """범위 마커인지 확인"""
        return self.duration > 0
        
    def get_end_frame(self) -> int:
        """마커 끝 프레임"""
        return self.frame + self.duration
        
    def contains_frame(self, frame: int) -> bool:
        """해당 프레임이 마커 범위에 포함되는지 확인"""
        if self.is_range_marker():
            return self.frame <= frame <= self.get_end_frame()
        else:
            return self.frame == frame
            
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "frame": self.frame,
            "name": self.name,
            "marker_type": self.marker_type,
            "description": self.description,
            "color": self.color,
            "is_locked": self.is_locked,
            "duration": self.duration
        }
        
    @classmethod
    def from_dict(cls, data: Dict):
        """딕셔너리에서 생성"""
        marker = cls(
            data["frame"],
            data.get("name", ""),
            data.get("marker_type", "default"),
            data.get("description", ""),
            data.get("color")
        )
        marker.is_locked = data.get("is_locked", False)
        marker.duration = data.get("duration", 0)
        return marker

class MarkerManager(QObject):
    """마커 관리자"""
    
    # 시그널
    marker_added = pyqtSignal(object)  # 마커 추가됨
    marker_removed = pyqtSignal(object)  # 마커 제거됨
    marker_updated = pyqtSignal(object)  # 마커 업데이트됨
    marker_selected = pyqtSignal(object)  # 마커 선택됨
    markers_changed = pyqtSignal()  # 마커 목록 변경됨
    
    def __init__(self):
        super().__init__()
        self.markers: List[TimelineMarker] = []
        self.selected_marker: Optional[TimelineMarker] = None
        self.auto_increment_names = True
        
    def add_marker(self, frame: int, name: str = "", marker_type: str = "default", 
                   description: str = "", duration: int = 0) -> TimelineMarker:
        """마커 추가"""
        # 같은 위치에 마커가 있는지 확인
        existing_marker = self.get_marker_at_frame(frame)
        if existing_marker and not existing_marker.is_range_marker():
            return existing_marker
            
        # 자동 이름 생성
        if not name and self.auto_increment_names:
            name = self.generate_marker_name(marker_type)
            
        # 마커 생성
        marker = TimelineMarker(frame, name, marker_type, description)
        marker.duration = duration
        
        # 리스트에 추가 (프레임 순서대로)
        self.markers.append(marker)
        self.sort_markers()
        
        self.marker_added.emit(marker)
        self.markers_changed.emit()
        
        return marker
        
    def remove_marker(self, marker: TimelineMarker) -> bool:
        """마커 제거"""
        if marker in self.markers and not marker.is_locked:
            self.markers.remove(marker)
            
            if self.selected_marker == marker:
                self.selected_marker = None
                
            self.marker_removed.emit(marker)
            self.markers_changed.emit()
            return True
        return False
        
    def remove_marker_at_frame(self, frame: int) -> bool:
        """특정 프레임의 마커 제거"""
        marker = self.get_marker_at_frame(frame)
        if marker:
            return self.remove_marker(marker)
        return False
        
    def update_marker(self, marker: TimelineMarker, **kwargs):
        """마커 업데이트"""
        if marker.is_locked:
            return False
            
        for key, value in kwargs.items():
            if hasattr(marker, key):
                setattr(marker, key, value)
                
        # 위치가 변경되면 다시 정렬
        if 'frame' in kwargs:
            self.sort_markers()
            
        self.marker_updated.emit(marker)
        self.markers_changed.emit()
        return True
        
    def get_marker_at_frame(self, frame: int) -> Optional[TimelineMarker]:
        """특정 프레임의 마커 찾기"""
        for marker in self.markers:
            if marker.contains_frame(frame):
                return marker
        return None
        
    def get_markers_in_range(self, start_frame: int, end_frame: int) -> List[TimelineMarker]:
        """범위 내의 마커들 찾기"""
        result = []
        for marker in self.markers:
            if (marker.frame >= start_frame and marker.frame <= end_frame) or \
               (marker.is_range_marker() and 
                marker.frame <= end_frame and marker.get_end_frame() >= start_frame):
                result.append(marker)
        return result
        
    def get_next_marker(self, current_frame: int) -> Optional[TimelineMarker]:
        """다음 마커 찾기"""
        for marker in self.markers:
            if marker.frame > current_frame:
                return marker
        return None
        
    def get_previous_marker(self, current_frame: int) -> Optional[TimelineMarker]:
        """이전 마커 찾기"""
        for marker in reversed(self.markers):
            if marker.frame < current_frame:
                return marker
        return None
        
    def get_markers_by_type(self, marker_type: str) -> List[TimelineMarker]:
        """타입별 마커 목록"""
        return [marker for marker in self.markers if marker.marker_type == marker_type]
        
    def get_chapter_markers(self) -> List[TimelineMarker]:
        """챕터 마커 목록"""
        return self.get_markers_by_type("chapter")
        
    def sort_markers(self):
        """마커를 프레임 순서로 정렬"""
        self.markers.sort(key=lambda m: m.frame)
        
    def select_marker(self, marker: Optional[TimelineMarker]):
        """마커 선택"""
        self.selected_marker = marker
        if marker:
            self.marker_selected.emit(marker)
            
    def get_selected_marker(self) -> Optional[TimelineMarker]:
        """선택된 마커 가져오기"""
        return self.selected_marker
        
    def clear_all_markers(self):
        """모든 마커 제거"""
        # 잠긴 마커는 제외하고 제거
        unlocked_markers = [m for m in self.markers if not m.is_locked]
        for marker in unlocked_markers:
            self.markers.remove(marker)
            
        self.selected_marker = None
        self.markers_changed.emit()
        
    def generate_marker_name(self, marker_type: str) -> str:
        """마커 이름 자동 생성"""
        type_name = TimelineMarker.MARKER_TYPES.get(marker_type, {}).get("name", "마커")
        
        # 같은 타입의 마커 개수 세기
        same_type_markers = self.get_markers_by_type(marker_type)
        number = len(same_type_markers) + 1
        
        return f"{type_name} {number}"
        
    def import_markers_from_chapters(self, chapters: List[Dict]):
        """챕터 정보에서 마커 가져오기"""
        for chapter in chapters:
            frame = chapter.get("start_frame", 0)
            name = chapter.get("title", "")
            description = chapter.get("description", "")
            
            self.add_marker(frame, name, "chapter", description)
            
    def export_chapters(self) -> List[Dict]:
        """챕터 마커를 챕터 정보로 내보내기"""
        chapters = []
        chapter_markers = self.get_chapter_markers()
        
        for marker in chapter_markers:
            chapters.append({
                "start_frame": marker.frame,
                "title": marker.name,
                "description": marker.description
            })
            
        return chapters
        
    def import_markers_from_json(self, json_data: str) -> bool:
        """JSON에서 마커 가져오기"""
        try:
            data = json.loads(json_data)
            
            for marker_data in data.get("markers", []):
                marker = TimelineMarker.from_dict(marker_data)
                self.markers.append(marker)
                
            self.sort_markers()
            self.markers_changed.emit()
            return True
            
        except Exception as e:
            print(f"마커 가져오기 오류: {e}")
            return False
            
    def export_markers_to_json(self) -> str:
        """마커를 JSON으로 내보내기"""
        try:
            data = {
                "version": "1.0",
                "markers": [marker.to_dict() for marker in self.markers]
            }
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"마커 내보내기 오류: {e}")
            return ""
            
    def get_marker_statistics(self) -> Dict:
        """마커 통계"""
        stats = {
            "total_count": len(self.markers),
            "by_type": {},
            "locked_count": 0,
            "range_markers_count": 0
        }
        
        for marker in self.markers:
            # 타입별 카운트
            if marker.marker_type not in stats["by_type"]:
                stats["by_type"][marker.marker_type] = 0
            stats["by_type"][marker.marker_type] += 1
            
            # 잠긴 마커 카운트
            if marker.is_locked:
                stats["locked_count"] += 1
                
            # 범위 마커 카운트
            if marker.is_range_marker():
                stats["range_markers_count"] += 1
                
        return stats
        
    def validate_markers(self) -> List[str]:
        """마커 유효성 검사"""
        issues = []
        
        # 중복 위치 체크
        frame_counts = {}
        for marker in self.markers:
            if marker.frame in frame_counts:
                frame_counts[marker.frame] += 1
            else:
                frame_counts[marker.frame] = 1
                
        for frame, count in frame_counts.items():
            if count > 1:
                issues.append(f"프레임 {frame}에 {count}개의 마커가 있습니다.")
                
        # 빈 이름 체크
        unnamed_count = sum(1 for m in self.markers if not m.name.strip())
        if unnamed_count > 0:
            issues.append(f"{unnamed_count}개의 마커에 이름이 없습니다.")
            
        return issues
        
    def auto_generate_chapters(self, interval_frames: int = 1800):  # 기본 60초 (30fps)
        """자동 챕터 생성"""
        # 기존 챕터 마커 제거
        chapter_markers = self.get_chapter_markers()
        for marker in chapter_markers:
            if not marker.is_locked:
                self.remove_marker(marker)
                
        # 일정 간격으로 챕터 마커 생성
        frame = 0
        chapter_num = 1
        
        # 타임라인 길이 계산 (대략적)
        max_frame = 3600  # 기본 2분 (실제로는 타임라인에서 가져와야 함)
        
        while frame <= max_frame:
            name = f"챕터 {chapter_num}"
            self.add_marker(frame, name, "chapter")
            frame += interval_frames
            chapter_num += 1 