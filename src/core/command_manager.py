"""
BLOUcut 명령 관리자
실행 취소/다시 실행을 위한 Command Pattern 구현
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from PyQt6.QtCore import QObject, pyqtSignal

class Command(ABC):
    """명령 추상 클래스"""
    
    @abstractmethod
    def execute(self):
        """명령 실행"""
        pass
        
    @abstractmethod
    def undo(self):
        """명령 취소"""
        pass
        
    @abstractmethod
    def get_description(self) -> str:
        """명령 설명"""
        pass

class AddClipCommand(Command):
    """클립 추가 명령"""
    
    def __init__(self, timeline, clip, track=0, start_frame=0):
        self.timeline = timeline
        self.clip = clip
        self.track = track
        self.start_frame = start_frame
        self.was_added = False
        
    def execute(self):
        """클립 추가 실행"""
        if not self.was_added:
            self.clip.track = self.track
            self.clip.start_frame = self.start_frame
            self.timeline.clips.append(self.clip)
            self.was_added = True
            self.timeline.update()
            
    def undo(self):
        """클립 추가 취소"""
        if self.was_added and self.clip in self.timeline.clips:
            self.timeline.clips.remove(self.clip)
            self.was_added = False
            self.timeline.update()
            
    def get_description(self) -> str:
        return f"클립 추가: {self.clip.name}"

class DeleteClipCommand(Command):
    """클립 삭제 명령"""
    
    def __init__(self, timeline, clip):
        self.timeline = timeline
        self.clip = clip
        self.clip_index = -1
        
    def execute(self):
        """클립 삭제 실행"""
        if self.clip in self.timeline.clips:
            self.clip_index = self.timeline.clips.index(self.clip)
            self.timeline.clips.remove(self.clip)
            if self.clip in self.timeline.selected_clips:
                self.timeline.selected_clips.remove(self.clip)
            self.timeline.update()
            
    def undo(self):
        """클립 삭제 취소"""
        if self.clip_index >= 0:
            self.timeline.clips.insert(self.clip_index, self.clip)
            self.timeline.update()
            
    def get_description(self) -> str:
        return f"클립 삭제: {self.clip.name}"

class MoveClipCommand(Command):
    """클립 이동 명령"""
    
    def __init__(self, clip, old_start_frame, old_track, new_start_frame, new_track):
        self.clip = clip
        self.old_start_frame = old_start_frame
        self.old_track = old_track
        self.new_start_frame = new_start_frame
        self.new_track = new_track
        
    def execute(self):
        """클립 이동 실행"""
        self.clip.start_frame = self.new_start_frame
        self.clip.track = self.new_track
        
    def undo(self):
        """클립 이동 취소"""
        self.clip.start_frame = self.old_start_frame
        self.clip.track = self.old_track
        
    def get_description(self) -> str:
        return f"클립 이동: {self.clip.name}"

class SplitClipCommand(Command):
    """클립 분할 명령"""
    
    def __init__(self, timeline, original_clip, split_frame):
        self.timeline = timeline
        self.original_clip = original_clip
        self.split_frame = split_frame
        self.second_clip = None
        self.original_duration = original_clip.duration
        
    def execute(self):
        """클립 분할 실행"""
        if self.second_clip is None:
            # 두 번째 클립 생성
            self.second_clip = self.original_clip.duplicate()
            
            # 첫 번째 클립 길이 조정
            first_duration = self.split_frame - self.original_clip.start_frame
            self.original_clip.duration = first_duration
            
            # 두 번째 클립 설정
            self.second_clip.start_frame = self.split_frame
            self.second_clip.duration = self.original_duration - first_duration
            
            # 타임라인에 추가
            self.timeline.clips.append(self.second_clip)
        else:
            # 이미 분할된 경우 다시 추가
            self.original_clip.duration = self.split_frame - self.original_clip.start_frame
            self.timeline.clips.append(self.second_clip)
            
        self.timeline.update()
        
    def undo(self):
        """클립 분할 취소"""
        if self.second_clip and self.second_clip in self.timeline.clips:
            self.timeline.clips.remove(self.second_clip)
            self.original_clip.duration = self.original_duration
            self.timeline.update()
            
    def get_description(self) -> str:
        return f"클립 분할: {self.original_clip.name}"

class PropertyChangeCommand(Command):
    """속성 변경 명령"""
    
    def __init__(self, clip, property_name, old_value, new_value):
        self.clip = clip
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value
        
    def execute(self):
        """속성 변경 실행"""
        setattr(self.clip, self.property_name, self.new_value)
        self.clip.properties_changed.emit()
        
    def undo(self):
        """속성 변경 취소"""
        setattr(self.clip, self.property_name, self.old_value)
        self.clip.properties_changed.emit()
        
    def get_description(self) -> str:
        return f"속성 변경: {self.clip.name} - {self.property_name}"

class CommandManager(QObject):
    """명령 관리자"""
    
    # 시그널
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)
    history_changed = pyqtSignal()
    
    def __init__(self, max_history=50):
        super().__init__()
        self.max_history = max_history
        self.command_history: List[Command] = []
        self.current_index = -1
        
    def execute_command(self, command: Command):
        """명령 실행 및 히스토리에 추가"""
        # 현재 위치 이후의 명령들 제거 (새로운 명령 실행시)
        if self.current_index < len(self.command_history) - 1:
            self.command_history = self.command_history[:self.current_index + 1]
            
        # 명령 실행
        command.execute()
        
        # 히스토리에 추가
        self.command_history.append(command)
        self.current_index += 1
        
        # 최대 히스토리 수 제한
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)
            self.current_index -= 1
            
        self._emit_signals()
        
    def undo(self) -> bool:
        """실행 취소"""
        if self.can_undo():
            command = self.command_history[self.current_index]
            command.undo()
            self.current_index -= 1
            self._emit_signals()
            return True
        return False
        
    def redo(self) -> bool:
        """다시 실행"""
        if self.can_redo():
            self.current_index += 1
            command = self.command_history[self.current_index]
            command.execute()
            self._emit_signals()
            return True
        return False
        
    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        return self.current_index >= 0
        
    def can_redo(self) -> bool:
        """다시 실행 가능 여부"""
        return self.current_index < len(self.command_history) - 1
        
    def get_undo_description(self) -> Optional[str]:
        """실행 취소할 명령 설명"""
        if self.can_undo():
            return self.command_history[self.current_index].get_description()
        return None
        
    def get_redo_description(self) -> Optional[str]:
        """다시 실행할 명령 설명"""
        if self.can_redo():
            return self.command_history[self.current_index + 1].get_description()
        return None
        
    def clear_history(self):
        """히스토리 초기화"""
        self.command_history.clear()
        self.current_index = -1
        self._emit_signals()
        
    def get_history(self) -> List[str]:
        """명령 히스토리 목록"""
        return [cmd.get_description() for cmd in self.command_history]
        
    def _emit_signals(self):
        """시그널 발생"""
        self.can_undo_changed.emit(self.can_undo())
        self.can_redo_changed.emit(self.can_redo())
        self.history_changed.emit() 