"""
BLOUcut 오디오 엔진
PyQt6의 QMediaPlayer를 사용한 오디오 재생
"""

import os
from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

class AudioEngine(QObject):
    """오디오 재생 엔진"""
    
    # 시그널
    position_changed = pyqtSignal(int)  # 재생 위치 변경 (밀리초)
    duration_changed = pyqtSignal(int)  # 총 길이 변경 (밀리초)
    state_changed = pyqtSignal(int)     # 재생 상태 변경
    
    def __init__(self):
        super().__init__()
        
        # 미디어 플레이어 설정
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # 현재 상태
        self.current_file = None
        self.is_playing = False
        self.current_position = 0  # 밀리초
        self.total_duration = 0    # 밀리초
        self.volume = 1.0
        
        # 시그널 연결
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        
        # 위치 업데이트 타이머
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._emit_position)
        self.position_timer.start(100)  # 100ms마다 업데이트
        
    def load_file(self, file_path):
        """오디오 파일 로드"""
        if not os.path.exists(file_path):
            return False
            
        try:
            self.current_file = file_path
            url = QUrl.fromLocalFile(file_path)
            self.player.setSource(url)
            return True
        except Exception as e:
            print(f"오디오 로드 실패: {e}")
            return False
            
    def play(self):
        """재생"""
        if self.player.source().isEmpty():
            return
            
        self.player.play()
        self.is_playing = True
        
    def pause(self):
        """일시정지"""
        self.player.pause()
        self.is_playing = False
        
    def stop(self):
        """정지"""
        self.player.stop()
        self.is_playing = False
        self.current_position = 0
        
    def set_position(self, position_ms):
        """재생 위치 설정 (밀리초)"""
        self.player.setPosition(position_ms)
        self.current_position = position_ms
        
    def set_volume(self, volume):
        """볼륨 설정 (0.0 ~ 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        self.audio_output.setVolume(self.volume)
        
    def get_position(self):
        """현재 재생 위치 반환 (밀리초)"""
        return self.player.position()
        
    def get_duration(self):
        """총 길이 반환 (밀리초)"""
        return self.player.duration()
        
    def get_state(self):
        """재생 상태 반환"""
        return self.player.playbackState()
        
    def _on_position_changed(self, position):
        """위치 변경 이벤트"""
        self.current_position = position
        
    def _on_duration_changed(self, duration):
        """길이 변경 이벤트"""
        self.total_duration = duration
        self.duration_changed.emit(duration)
        
    def _on_state_changed(self, state):
        """상태 변경 이벤트"""
        self.is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self.state_changed.emit(state)
        
    def _emit_position(self):
        """위치 시그널 방출"""
        current_pos = self.get_position()
        if current_pos != self.current_position:
            self.current_position = current_pos
            self.position_changed.emit(current_pos) 