"""
BLOUcut Pygame 오디오 엔진
pygame.mixer를 사용한 안정적인 오디오 재생
"""

import os
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import pygame

class PygameAudioEngine(QObject):
    """Pygame 기반 오디오 재생 엔진"""
    
    # 시그널
    position_changed = pyqtSignal(int)  # 재생 위치 변경 (밀리초)
    duration_changed = pyqtSignal(int)  # 총 길이 변경 (밀리초)
    state_changed = pyqtSignal(int)     # 재생 상태 변경
    
    def __init__(self):
        super().__init__()
        
        # pygame 초기화
        try:
            # 더 큰 버퍼로 설정하여 지연 최소화
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            self.pygame_available = True
            print("Pygame 오디오 엔진 초기화 성공")
        except Exception as e:
            print(f"Pygame 초기화 실패: {e}")
            self.pygame_available = False
        
        # 현재 상태
        self.current_file = None
        self.sound = None
        self.channel = None  # 재생 채널
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0  # 밀리초
        self.total_duration = 0    # 밀리초
        self.volume = 1.0
        self.start_time = 0        # 재생 시작 시간
        self.pause_position = 0    # 일시정지된 위치
        self.last_logged_position = -1  # 마지막 로그 위치
        
        # 위치 추적 스레드
        self.position_thread = None
        self.stop_position_thread = False
        
        # 위치 업데이트 타이머
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._emit_position)
        self.position_timer.start(100)  # 100ms마다 업데이트
        
    def load_file(self, file_path):
        """오디오 파일 로드"""
        if not self.pygame_available:
            print("Pygame을 사용할 수 없음")
            return False
            
        if not os.path.exists(file_path):
            print(f"파일이 존재하지 않음: {file_path}")
            return False
            
        # 지원하는 파일 형식인지 확인
        ext = os.path.splitext(file_path)[1].lower()
        supported_formats = ['.wav', '.ogg', '.mp3']
        
        try:
            # 이전 사운드 정리
            if self.sound:
                pygame.mixer.stop()
                self.channel = None
                
            # 새 파일 로드
            self.current_file = file_path
            
            # MP3 파일은 특별 처리 필요할 수 있음
            if ext == '.mp3':
                print(f"MP3 파일 로드 시도: {os.path.basename(file_path)}")
                
            self.sound = pygame.mixer.Sound(file_path)
            
            # 길이 계산
            try:
                # pygame 2.0+에서는 get_length() 사용
                if hasattr(self.sound, 'get_length'):
                    self.total_duration = int(self.sound.get_length() * 1000)
                else:
                    # 기본값 사용
                    self.total_duration = 30000  # 30초
            except Exception as duration_error:
                print(f"길이 계산 실패: {duration_error}")
                # 다른 방법으로 시도
                try:
                    import wave
                    if ext == '.wav':
                        with wave.open(file_path, 'r') as wav_file:
                            frames = wav_file.getnframes()
                            sample_rate = wav_file.getframerate()
                            duration = frames / float(sample_rate)
                            self.total_duration = int(duration * 1000)
                    else:
                        # 기본값
                        self.total_duration = 30000  # 30초
                except:
                    self.total_duration = 30000  # 30초
            
            self.current_position = 0
            self.pause_position = 0
            
            self.duration_changed.emit(self.total_duration)
            print(f"오디오 로드 성공: {os.path.basename(file_path)} ({self.total_duration/1000:.2f}초)")
            return True
            
        except Exception as e:
            print(f"오디오 로드 실패 [{ext}]: {e}")
            
            # MP3 파일의 경우 대안 시도
            if ext == '.mp3':
                print("MP3 파일 로드를 위해 pygame 재초기화 시도...")
                try:
                    pygame.mixer.quit()
                    pygame.mixer.init()
                    self.sound = pygame.mixer.Sound(file_path)
                    self.total_duration = 30000  # 임시 길이
                    self.current_position = 0
                    self.pause_position = 0
                    self.duration_changed.emit(self.total_duration)
                    print(f"MP3 재시도 성공: {os.path.basename(file_path)}")
                    return True
                except Exception as retry_error:
                    print(f"MP3 재시도 실패: {retry_error}")
                    
            return False
            
    def play(self):
        """재생 - 개선된 로직"""
        if not self.pygame_available or not self.sound:
            print("[오디오] 재생 불가: pygame 또는 사운드 없음")
            return
            
        try:
            if self.is_paused:
                # 일시정지에서 재개
                pygame.mixer.unpause()
                self.start_time = time.time() - (self.pause_position / 1000.0)
                print(f"[오디오] 재개: {self.pause_position/1000:.1f}초부터")
            else:
                # 새로 재생 - 먼저 기존 재생 정지
                if self.channel:
                    pygame.mixer.stop()
                    
                self.channel = self.sound.play()
                if self.channel:
                    self.start_time = time.time() - (self.current_position / 1000.0)
                    # 볼륨 설정
                    self.sound.set_volume(self.volume)
                    print(f"[오디오] 재생: {self.current_position/1000:.1f}초부터")
                else:
                    print("[오디오] 채널 할당 실패")
                    return
                
            self.is_playing = True
            self.is_paused = False
            self.state_changed.emit(1)  # Playing state
            
        except Exception as e:
            print(f"오디오 재생 실패: {e}")
            self.is_playing = False
        
    def pause(self):
        """일시정지 - 개선된 로직"""
        if not self.pygame_available or not self.is_playing:
            return
            
        try:
            pygame.mixer.pause()
            self.is_playing = False
            self.is_paused = True
            self.pause_position = self.get_position()
            self.state_changed.emit(2)  # Paused state
            print(f"[오디오] 일시정지: {self.pause_position/1000:.1f}초")
            
        except Exception as e:
            print(f"오디오 일시정지 실패: {e}")
        
    def stop(self):
        """정지 - 개선된 로직"""
        if not self.pygame_available:
            return
            
        try:
            pygame.mixer.stop()
            self.is_playing = False
            self.is_paused = False
            self.current_position = 0
            self.pause_position = 0
            self.start_time = 0
            self.channel = None
            self.state_changed.emit(0)  # Stopped state
            print("[오디오] 정지")
            
        except Exception as e:
            print(f"오디오 정지 실패: {e}")
        
    def set_position(self, position_ms):
        """재생 위치 설정 (밀리초) - 개선된 로직"""
        if not self.pygame_available or not self.sound:
            return
            
        # 위치 유효성 검사
        position_ms = max(0, min(position_ms, self.total_duration))
        
        # 현재 위치와 너무 가까우면 설정하지 않음 (무의미한 작업 방지)
        if abs(position_ms - self.current_position) < 100:  # 100ms 이하 차이
            return
            
        was_playing = self.is_playing
        
        # 현재 재생 중이면 정지
        if was_playing and self.channel:
            pygame.mixer.stop()
            self.channel = None
            
        # 위치 업데이트
        self.current_position = position_ms
        self.pause_position = position_ms
        
        if was_playing:
            # 새 위치에서 재생 재시작
            try:
                self.channel = self.sound.play()
                if self.channel:
                    self.start_time = time.time() - (position_ms / 1000.0)
                    self.is_playing = True
                    self.is_paused = False
                    # 볼륨 재설정
                    self.sound.set_volume(self.volume)
                else:
                    print("[오디오] 위치 설정 후 채널 할당 실패")
                    self.is_playing = False
            except Exception as e:
                print(f"위치 설정 후 재생 실패: {e}")
                self.is_playing = False
        
        # 로그 간소화 (1초 단위로만)
        current_second = int(position_ms / 1000)
        last_second = getattr(self, '_last_logged_second', -1)
        if current_second != last_second:
            print(f"[오디오 위치] {current_second}초")
            self._last_logged_second = current_second
        
    def set_volume(self, volume):
        """볼륨 설정 (0.0 ~ 1.0) - 개선된 로직"""
        self.volume = max(0.0, min(1.0, volume))
        if self.pygame_available and self.sound:
            try:
                self.sound.set_volume(self.volume)
                # 볼륨 로그 간소화 (10% 단위로만)
                volume_percent = int(self.volume * 100)
                if volume_percent % 10 == 0:
                    print(f"[볼륨] {volume_percent}%")
            except Exception as e:
                print(f"볼륨 설정 실패: {e}")
        
    def get_position(self):
        """현재 재생 위치 반환 (밀리초) - 개선된 로직"""
        if not self.pygame_available:
            return 0
            
        if self.is_playing and not self.is_paused and self.channel:
            # 채널이 아직 재생 중인지 확인
            if not self.channel.get_busy():
                # 채널이 정지되었으면 재생 완료로 처리
                if self.current_position < self.total_duration - 500:  # 500ms 여유
                    print(f"[오디오] 예상치 못한 채널 정지 - 위치: {self.current_position}ms")
                self.current_position = self.total_duration
                if self.is_playing:
                    print("[오디오] 재생 완료 - 자동 정지")
                    self.stop()
                return self.current_position
            
            # 재생 중일 때는 시간 기반 계산
            elapsed = time.time() - self.start_time
            calculated_position = int(elapsed * 1000)
            
            # 계산된 위치가 유효한 범위 내에 있는지 확인
            if calculated_position >= 0 and calculated_position <= self.total_duration:
                self.current_position = calculated_position
            else:
                # 범위를 벗어나면 조정
                if calculated_position > self.total_duration:
                    self.current_position = self.total_duration
                    if self.is_playing:
                        print("[오디오] 총 길이 초과로 재생 종료")
                        self.stop()
                else:
                    self.current_position = 0
        
        return self.current_position
        
    def get_duration(self):
        """총 길이 반환 (밀리초)"""
        return self.total_duration
        
    def get_state(self):
        """재생 상태 반환"""
        if self.is_playing:
            return 1  # Playing
        elif self.is_paused:
            return 2  # Paused
        else:
            return 0  # Stopped
        
    def _emit_position(self):
        """위치 시그널 방출 - 개선된 로직"""
        # 재생 중일 때만 위치 업데이트
        if not self.is_playing or self.is_paused:
            return
            
        current_pos = self.get_position()
        
        # 위치가 유효한 범위 내에 있을 때만 시그널 방출
        if 0 <= current_pos <= self.total_duration:
            self.position_changed.emit(current_pos)
        
        # 재생 완료 확인
        if current_pos >= self.total_duration and self.is_playing:
            print("[오디오] 재생 완료")
            self.stop()
        
    def __del__(self):
        """소멸자"""
        if hasattr(self, 'pygame_available') and self.pygame_available:
            try:
                pygame.mixer.quit()
            except:
                pass 