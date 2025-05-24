"""
BLOUcut 내보내기 관리자
FFmpeg 기반 비디오 내보내기 시스템
"""

import os
import subprocess
import json
from typing import Dict, List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QMessageBox

class ExportPreset:
    """내보내기 프리셋"""
    
    def __init__(self, name: str, description: str, settings: Dict):
        self.name = name
        self.description = description
        self.settings = settings
        
    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'settings': self.settings
        }
        
    @classmethod
    def from_dict(cls, data):
        return cls(data['name'], data['description'], data['settings'])

class ExportTask(QThread):
    """내보내기 작업 스레드"""
    
    # 시그널
    progress_changed = pyqtSignal(int)  # 진행률 (0-100)
    status_changed = pyqtSignal(str)   # 상태 메시지
    error_occurred = pyqtSignal(str)   # 오류 메시지
    finished = pyqtSignal(bool)        # 완료 (성공 여부)
    
    def __init__(self, ffmpeg_command: List[str], output_path: str):
        super().__init__()
        self.ffmpeg_command = ffmpeg_command
        self.output_path = output_path
        self.process = None
        self.cancelled = False
        
    def run(self):
        """내보내기 실행"""
        try:
            self.status_changed.emit("내보내기 시작...")
            
            # FFmpeg 프로세스 시작
            self.process = subprocess.Popen(
                self.ffmpeg_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # 진행률 모니터링
            while True:
                if self.cancelled:
                    self.process.terminate()
                    self.finished.emit(False)
                    return
                    
                output = self.process.stderr.readline()
                if output == '' and self.process.poll() is not None:
                    break
                    
                if output:
                    # FFmpeg 출력에서 진행률 파싱
                    progress = self.parse_ffmpeg_progress(output)
                    if progress >= 0:
                        self.progress_changed.emit(progress)
                        
            # 프로세스 완료 확인
            return_code = self.process.poll()
            
            if return_code == 0:
                self.status_changed.emit("내보내기 완료!")
                self.progress_changed.emit(100)
                self.finished.emit(True)
            else:
                error_output = self.process.stderr.read()
                self.error_occurred.emit(f"내보내기 실패: {error_output}")
                self.finished.emit(False)
                
        except Exception as e:
            self.error_occurred.emit(f"내보내기 오류: {str(e)}")
            self.finished.emit(False)
            
    def parse_ffmpeg_progress(self, output: str) -> int:
        """FFmpeg 출력에서 진행률 파싱"""
        # FFmpeg 진행률 파싱 (간단 구현)
        if "time=" in output:
            try:
                time_part = output.split("time=")[1].split()[0]
                # 시간을 초로 변환하여 진행률 계산
                time_parts = time_part.split(":")
                if len(time_parts) == 3:
                    hours = float(time_parts[0])
                    minutes = float(time_parts[1])
                    seconds = float(time_parts[2])
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    
                    # 가정: 30초 프로젝트 (실제로는 프로젝트 길이를 사용해야 함)
                    project_duration = 30.0
                    progress = min(100, int((total_seconds / project_duration) * 100))
                    return progress
            except:
                pass
        return -1
        
    def cancel(self):
        """내보내기 취소"""
        self.cancelled = True
        if self.process:
            self.process.terminate()

class ExportManager(QObject):
    """내보내기 관리자"""
    
    # 시그널
    export_started = pyqtSignal(str)   # 출력 경로
    export_finished = pyqtSignal(bool, str)  # 성공 여부, 경로
    export_progress = pyqtSignal(int)  # 진행률
    export_status = pyqtSignal(str)    # 상태
    
    def __init__(self):
        super().__init__()
        self.current_task = None
        self.presets = self.create_default_presets()
        
    def create_default_presets(self) -> Dict[str, ExportPreset]:
        """기본 프리셋 생성"""
        presets = {}
        
        # YouTube 4K 프리셋
        presets['youtube_4k'] = ExportPreset(
            "YouTube 4K",
            "4K 해상도, 고품질 YouTube 업로드용",
            {
                'resolution': [3840, 2160],
                'framerate': 30,
                'video_codec': 'libx264',
                'video_bitrate': '20M',
                'audio_codec': 'aac',
                'audio_bitrate': '192k',
                'format': 'mp4',
                'preset': 'medium',
                'crf': 18
            }
        )
        
        # YouTube 1080p 프리셋
        presets['youtube_1080p'] = ExportPreset(
            "YouTube 1080p",
            "1080p 해상도, 표준 YouTube 업로드용",
            {
                'resolution': [1920, 1080],
                'framerate': 30,
                'video_codec': 'libx264',
                'video_bitrate': '8M',
                'audio_codec': 'aac',
                'audio_bitrate': '128k',
                'format': 'mp4',
                'preset': 'medium',
                'crf': 20
            }
        )
        
        # Instagram Story 프리셋
        presets['instagram_story'] = ExportPreset(
            "Instagram Story",
            "9:16 세로 비율, 인스타그램 스토리용",
            {
                'resolution': [1080, 1920],
                'framerate': 30,
                'video_codec': 'libx264',
                'video_bitrate': '5M',
                'audio_codec': 'aac',
                'audio_bitrate': '128k',
                'format': 'mp4',
                'preset': 'fast',
                'crf': 22
            }
        )
        
        # TikTok 프리셋
        presets['tiktok'] = ExportPreset(
            "TikTok",
            "TikTok 플랫폼 최적화",
            {
                'resolution': [1080, 1920],
                'framerate': 30,
                'video_codec': 'libx264',
                'video_bitrate': '4M',
                'audio_codec': 'aac',
                'audio_bitrate': '128k',
                'format': 'mp4',
                'preset': 'fast',
                'crf': 23
            }
        )
        
        # 웹 최적화 프리셋
        presets['web_optimized'] = ExportPreset(
            "웹 최적화",
            "웹 사이트용 경량화 비디오",
            {
                'resolution': [1280, 720],
                'framerate': 30,
                'video_codec': 'libx264',
                'video_bitrate': '2M',
                'audio_codec': 'aac',
                'audio_bitrate': '96k',
                'format': 'mp4',
                'preset': 'fast',
                'crf': 25
            }
        )
        
        # 모바일 최적화 프리셋
        presets['mobile_optimized'] = ExportPreset(
            "모바일 최적화",
            "모바일 장치용 최적화",
            {
                'resolution': [854, 480],
                'framerate': 30,
                'video_codec': 'libx264',
                'video_bitrate': '1M',
                'audio_codec': 'aac',
                'audio_bitrate': '96k',
                'format': 'mp4',
                'preset': 'fast',
                'crf': 28
            }
        )
        
        return presets
        
    def get_preset_names(self) -> List[str]:
        """프리셋 이름 목록"""
        return list(self.presets.keys())
        
    def get_preset(self, name: str) -> Optional[ExportPreset]:
        """프리셋 가져오기"""
        return self.presets.get(name)
        
    def add_custom_preset(self, preset: ExportPreset):
        """사용자 정의 프리셋 추가"""
        self.presets[preset.name.lower().replace(' ', '_')] = preset
        
    def export_video(self, timeline, output_path: str, preset_name: str, custom_settings: Optional[Dict] = None):
        """비디오 내보내기"""
        preset = self.get_preset(preset_name)
        if not preset:
            self.export_finished.emit(False, f"프리셋을 찾을 수 없습니다: {preset_name}")
            return
            
        # 설정 적용 (사용자 정의 설정이 있으면 덮어쓰기)
        settings = preset.settings.copy()
        if custom_settings:
            settings.update(custom_settings)
            
        # FFmpeg 명령어 생성
        ffmpeg_command = self.build_ffmpeg_command(timeline, output_path, settings)
        
        # 기존 작업이 있으면 취소
        if self.current_task and self.current_task.isRunning():
            self.current_task.cancel()
            self.current_task.wait()
            
        # 새 작업 시작
        self.current_task = ExportTask(ffmpeg_command, output_path)
        self.current_task.progress_changed.connect(self.export_progress.emit)
        self.current_task.status_changed.connect(self.export_status.emit)
        self.current_task.error_occurred.connect(lambda msg: self.export_finished.emit(False, msg))
        self.current_task.finished.connect(lambda success: self.export_finished.emit(success, output_path))
        
        self.export_started.emit(output_path)
        self.current_task.start()
        
    def build_ffmpeg_command(self, timeline, output_path: str, settings: Dict) -> List[str]:
        """FFmpeg 명령어 구성"""
        command = ['ffmpeg', '-y']  # -y: 덮어쓰기 허용
        
        # 입력 파일들 (실제로는 타임라인의 클립들을 처리해야 함)
        # 현재는 간단한 더미 구현
        command.extend(['-f', 'lavfi', '-i', 'testsrc=duration=10:size=1920x1080:rate=30'])
        command.extend(['-f', 'lavfi', '-i', 'sine=frequency=1000:duration=10'])
        
        # 비디오 설정
        if 'video_codec' in settings:
            command.extend(['-c:v', settings['video_codec']])
            
        if 'video_bitrate' in settings:
            command.extend(['-b:v', settings['video_bitrate']])
            
        if 'crf' in settings:
            command.extend(['-crf', str(settings['crf'])])
            
        if 'preset' in settings:
            command.extend(['-preset', settings['preset']])
            
        if 'resolution' in settings:
            width, height = settings['resolution']
            command.extend(['-s', f"{width}x{height}"])
            
        if 'framerate' in settings:
            command.extend(['-r', str(settings['framerate'])])
            
        # 오디오 설정
        if 'audio_codec' in settings:
            command.extend(['-c:a', settings['audio_codec']])
            
        if 'audio_bitrate' in settings:
            command.extend(['-b:a', settings['audio_bitrate']])
            
        # 출력 파일
        command.append(output_path)
        
        return command
        
    def cancel_export(self):
        """내보내기 취소"""
        if self.current_task and self.current_task.isRunning():
            self.current_task.cancel()
            
    def is_exporting(self) -> bool:
        """내보내기 중인지 확인"""
        return self.current_task and self.current_task.isRunning()
        
    def save_presets(self, file_path: str):
        """프리셋 저장"""
        try:
            data = {name: preset.to_dict() for name, preset in self.presets.items()}
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"프리셋 저장 오류: {e}")
            
    def load_presets(self, file_path: str):
        """프리셋 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.presets = {}
            for name, preset_data in data.items():
                self.presets[name] = ExportPreset.from_dict(preset_data)
        except Exception as e:
            print(f"프리셋 로드 오류: {e}")
            # 오류 시 기본 프리셋으로 복원
            self.presets = self.create_default_presets() 