"""
BLOUcut 미디어 분석기
FFprobe를 사용하여 미디어 파일의 실제 정보를 추출
"""

import subprocess
import json
import os
from typing import Dict, Optional, Tuple

class MediaAnalyzer:
    """미디어 파일 분석기"""
    
    # 캐시 시스템
    _info_cache = {}
    _cache_size_limit = 100
    
    @staticmethod
    def get_media_info(file_path: str) -> Dict:
        """미디어 파일 정보 추출"""
        # 캐시 확인 (파일 경로와 수정 시간으로 키 생성)
        cache_key = file_path
        if os.path.exists(file_path):
            cache_key = f"{file_path}_{os.path.getmtime(file_path)}"
            
        if cache_key in MediaAnalyzer._info_cache:
            return MediaAnalyzer._info_cache[cache_key].copy()
        
        if not os.path.exists(file_path):
            return MediaAnalyzer._get_default_info(file_path)
            
        try:
            # FFprobe 명령어로 미디어 정보 추출
            cmd = [
                'ffprobe', 
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return MediaAnalyzer._get_default_info(file_path)
                
            data = json.loads(result.stdout)
            info = MediaAnalyzer._parse_ffprobe_data(file_path, data)
            
            # 캐시에 저장 (크기 제한)
            if len(MediaAnalyzer._info_cache) >= MediaAnalyzer._cache_size_limit:
                # 가장 오래된 항목 제거
                oldest_key = next(iter(MediaAnalyzer._info_cache))
                del MediaAnalyzer._info_cache[oldest_key]
                
            MediaAnalyzer._info_cache[cache_key] = info.copy()
            return info
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # FFprobe가 없거나 실패한 경우 기본값 반환
            return MediaAnalyzer._get_default_info(file_path)
    
    @staticmethod
    def _parse_ffprobe_data(file_path: str, data: Dict) -> Dict:
        """FFprobe 데이터 파싱"""
        info = {
            'path': file_path,
            'name': os.path.basename(file_path),
            'duration': 0.0,
            'duration_frames': 0,
            'fps': 30.0,
            'width': 0,
            'height': 0,
            'has_video': False,
            'has_audio': False,
            'media_type': 'unknown',
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
        
        # 포맷 정보에서 길이 추출
        if 'format' in data and 'duration' in data['format']:
            try:
                info['duration'] = float(data['format']['duration'])
            except (ValueError, TypeError):
                pass
        
        # 스트림 정보 분석
        if 'streams' in data:
            for stream in data['streams']:
                codec_type = stream.get('codec_type', '')
                
                if codec_type == 'video':
                    info['has_video'] = True
                    info['width'] = int(stream.get('width', 0))
                    info['height'] = int(stream.get('height', 0))
                    
                    # FPS 계산
                    if 'r_frame_rate' in stream:
                        fps_str = stream['r_frame_rate']
                        if '/' in fps_str:
                            num, den = fps_str.split('/')
                            if int(den) != 0:
                                info['fps'] = float(num) / float(den)
                    
                    # 비디오 길이 (스트림별로 다를 수 있음)
                    if 'duration' in stream and info['duration'] == 0:
                        try:
                            info['duration'] = float(stream['duration'])
                        except (ValueError, TypeError):
                            pass
                            
                elif codec_type == 'audio':
                    info['has_audio'] = True
                    
                    # 오디오 길이
                    if 'duration' in stream and info['duration'] == 0:
                        try:
                            info['duration'] = float(stream['duration'])
                        except (ValueError, TypeError):
                            pass
        
        # 파일 확장자 확인
        ext = os.path.splitext(file_path)[1].lower()
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        audio_exts = ['.mp3', '.wav', '.aac', '.ogg', '.m4a', '.flac', '.wma']
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
        
        # 미디어 타입 결정 (확장자 우선)
        if ext in audio_exts:
            # 오디오 파일 (앨범 아트가 있어도 오디오로 처리)
            info['media_type'] = 'audio'
            info['fps'] = 30.0  # 타임라인 기준 FPS
        elif ext in video_exts:
            # 비디오 파일
            info['media_type'] = 'video'
        elif ext in image_exts:
            # 이미지 파일
            info['media_type'] = 'image'
            info['duration'] = 3.0  # 이미지 기본 3초
            info['fps'] = 30.0  # 타임라인 기준 FPS
        else:
            # 확장자로 판단할 수 없는 경우 스트림 정보 사용
            if info['has_video']:
                info['media_type'] = 'video'
            elif info['has_audio']:
                info['media_type'] = 'audio'
                info['fps'] = 30.0
            else:
                info['media_type'] = 'unknown'
        
        # 프레임 단위 길이 계산 (타임라인 기준 30fps로 통일)
        timeline_fps = 30.0
        info['duration_frames'] = int(info['duration'] * timeline_fps)
        
        # 디버그 출력 (간단하게)
        print(f"[미디어분석] {os.path.basename(file_path)}: {info['duration']:.1f}초, {info['media_type']}")
        
        return info
    
    @staticmethod
    def _get_default_info(file_path: str) -> Dict:
        """기본 미디어 정보 반환 (FFprobe 실패시)"""
        ext = os.path.splitext(file_path)[1].lower()
        
        # 확장자 기반 추정
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        audio_exts = ['.mp3', '.wav', '.aac', '.ogg', '.m4a', '.flac', '.wma']
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
        
        if ext in video_exts:
            media_type = 'video'
            duration = 10.0  # 기본 10초
        elif ext in audio_exts:
            media_type = 'audio'
            duration = 30.0  # 기본 30초
        elif ext in image_exts:
            media_type = 'image'
            duration = 3.0   # 기본 3초
        else:
            media_type = 'unknown'
            duration = 3.0
        
        return {
            'path': file_path,
            'name': os.path.basename(file_path),
            'duration': duration,
            'duration_frames': int(duration * 30),
            'fps': 30.0,
            'width': 1920,
            'height': 1080,
            'has_video': media_type == 'video',
            'has_audio': media_type in ['video', 'audio'],
            'media_type': media_type,
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """초를 시:분:초 형식으로 변환"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def get_thumbnail_path(file_path: str, time_seconds: float = 1.0) -> Optional[str]:
        """비디오 파일의 썸네일 생성 (FFmpeg 사용) - 시간별 썸네일 지원"""
        if not os.path.exists(file_path):
            return None
            
        # 썸네일 저장 경로
        cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'thumbnails')
        os.makedirs(cache_dir, exist_ok=True)
        
        # 시간 정보를 포함한 고유 해시 생성 (시간별로 다른 썸네일)
        time_rounded = round(time_seconds, 1)  # 0.1초 단위로 반올림
        file_hash = str(hash(file_path + str(os.path.getmtime(file_path)) + str(time_rounded)))
        thumbnail_path = os.path.join(cache_dir, f"thumb_{file_hash}_t{time_rounded:.1f}.jpg")
        
        # 이미 생성된 썸네일이 있으면 반환
        if os.path.exists(thumbnail_path):
            return thumbnail_path
            
        try:
            # FFmpeg로 썸네일 생성 (더 안정적인 옵션 사용)
            cmd = [
                'ffmpeg',
                '-i', file_path,
                '-ss', str(max(0, time_seconds)),  # 음수 방지
                '-vframes', '1',
                '-vf', 'scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2',
                '-q:v', '3',
                '-f', 'image2',
                '-y',
                thumbnail_path
            ]
            
            # 로그 출력 (디버깅용)
            result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
            
            if result.returncode == 0 and os.path.exists(thumbnail_path):
                # 성공 로그 (시간 정보 포함)
                print(f"[썸네일 생성] {os.path.basename(file_path)} - {time_seconds:.1f}초")
                return thumbnail_path
            else:
                print(f"FFmpeg 썸네일 생성 실패: {result.stderr}")
                
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"썸네일 생성 실패: {e}")
            
        return None 