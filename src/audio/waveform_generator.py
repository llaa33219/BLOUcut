"""
BLOUcut 오디오 파형 생성기
오디오 파일을 분석하여 타임라인에 표시할 파형 데이터 생성
"""

import numpy as np
import librosa
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor

class WaveformData:
    """파형 데이터 클래스"""
    
    def __init__(self, peaks: List[float], sample_rate: int, duration: float):
        self.peaks = peaks  # 피크 값들
        self.sample_rate = sample_rate
        self.duration = duration
        self.channels = 1  # 모노로 변환된 데이터
        
    def get_peak_at_time(self, time_seconds: float) -> float:
        """특정 시간의 피크 값 가져오기"""
        if not self.peaks or time_seconds < 0 or time_seconds > self.duration:
            return 0.0
            
        # 시간을 인덱스로 변환
        samples_per_peak = len(self.peaks) / self.duration
        index = int(time_seconds * samples_per_peak)
        index = min(index, len(self.peaks) - 1)
        
        return self.peaks[index]
        
    def get_peaks_in_range(self, start_time: float, end_time: float, 
                          target_width: int) -> List[float]:
        """시간 범위의 피크들을 지정된 너비로 리샘플링"""
        if not self.peaks or start_time >= end_time:
            return [0.0] * target_width
            
        # 시간을 인덱스로 변환
        samples_per_peak = len(self.peaks) / self.duration
        start_idx = max(0, int(start_time * samples_per_peak))
        end_idx = min(len(self.peaks), int(end_time * samples_per_peak))
        
        if start_idx >= end_idx:
            return [0.0] * target_width
            
        # 원본 데이터 추출
        source_peaks = self.peaks[start_idx:end_idx]
        
        # 리샘플링
        if len(source_peaks) == target_width:
            return source_peaks
        elif len(source_peaks) < target_width:
            # 업샘플링 (선형 보간)
            return self._upsample(source_peaks, target_width)
        else:
            # 다운샘플링 (최대값 유지)
            return self._downsample(source_peaks, target_width)
            
    def _upsample(self, data: List[float], target_size: int) -> List[float]:
        """업샘플링 (선형 보간)"""
        if not data:
            return [0.0] * target_size
            
        result = []
        ratio = (len(data) - 1) / (target_size - 1) if target_size > 1 else 0
        
        for i in range(target_size):
            pos = i * ratio
            idx = int(pos)
            frac = pos - idx
            
            if idx >= len(data) - 1:
                result.append(data[-1])
            else:
                # 선형 보간
                value = data[idx] * (1 - frac) + data[idx + 1] * frac
                result.append(value)
                
        return result
        
    def _downsample(self, data: List[float], target_size: int) -> List[float]:
        """다운샘플링 (최대값 유지)"""
        if not data:
            return [0.0] * target_size
            
        result = []
        chunk_size = len(data) / target_size
        
        for i in range(target_size):
            start_idx = int(i * chunk_size)
            end_idx = int((i + 1) * chunk_size)
            end_idx = min(end_idx, len(data))
            
            if start_idx < end_idx:
                # 청크에서 최대값 찾기
                chunk_max = max(abs(x) for x in data[start_idx:end_idx])
                result.append(chunk_max)
            else:
                result.append(0.0)
                
        return result
        
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "peaks": self.peaks,
            "sample_rate": self.sample_rate,
            "duration": self.duration,
            "channels": self.channels
        }
        
    @classmethod
    def from_dict(cls, data: Dict):
        """딕셔너리에서 생성"""
        waveform = cls(data["peaks"], data["sample_rate"], data["duration"])
        waveform.channels = data.get("channels", 1)
        return waveform

class WaveformGeneratorThread(QThread):
    """파형 생성 스레드"""
    
    # 시그널
    progress_updated = pyqtSignal(int)  # 진행률 (0-100)
    waveform_generated = pyqtSignal(object)  # 생성된 파형 데이터
    error_occurred = pyqtSignal(str)  # 오류 발생
    
    def __init__(self, audio_path: str, target_peaks: int = 1000):
        super().__init__()
        self.audio_path = audio_path
        self.target_peaks = target_peaks  # 목표 피크 수
        self.is_cancelled = False
        
    def run(self):
        """파형 생성 실행"""
        try:
            self.progress_updated.emit(10)
            
            # 오디오 파일 로드
            y, sr = librosa.load(self.audio_path, sr=None, mono=True)
            duration = len(y) / sr
            
            if self.is_cancelled:
                return
                
            self.progress_updated.emit(30)
            
            # 피크 추출
            peaks = self._extract_peaks(y, self.target_peaks)
            
            if self.is_cancelled:
                return
                
            self.progress_updated.emit(80)
            
            # 파형 데이터 생성
            waveform_data = WaveformData(peaks, sr, duration)
            
            self.progress_updated.emit(100)
            self.waveform_generated.emit(waveform_data)
            
        except Exception as e:
            self.error_occurred.emit(f"파형 생성 오류: {str(e)}")
            
    def _extract_peaks(self, audio_data: np.ndarray, target_peaks: int) -> List[float]:
        """오디오 데이터에서 피크 추출"""
        if len(audio_data) == 0:
            return [0.0] * target_peaks
            
        # 청크 크기 계산
        chunk_size = max(1, len(audio_data) // target_peaks)
        peaks = []
        
        for i in range(0, len(audio_data), chunk_size):
            if self.is_cancelled:
                break
                
            chunk = audio_data[i:i + chunk_size]
            if len(chunk) > 0:
                # RMS 값 계산 (더 부드러운 파형)
                rms = np.sqrt(np.mean(chunk ** 2))
                peaks.append(float(rms))
                
            # 진행률 업데이트
            progress = 30 + int((i / len(audio_data)) * 50)
            self.progress_updated.emit(progress)
            
        # 목표 길이에 맞춤
        while len(peaks) < target_peaks:
            peaks.append(0.0)
            
        return peaks[:target_peaks]
        
    def cancel(self):
        """생성 취소"""
        self.is_cancelled = True

class WaveformGenerator(QObject):
    """파형 생성기 관리자"""
    
    # 시그널
    waveform_ready = pyqtSignal(str, object)  # 파일 경로, 파형 데이터
    generation_progress = pyqtSignal(str, int)  # 파일 경로, 진행률
    generation_error = pyqtSignal(str, str)  # 파일 경로, 오류 메시지
    
    def __init__(self):
        super().__init__()
        self.cache_dir = Path.home() / ".bloucut" / "waveforms"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_threads: Dict[str, WaveformGeneratorThread] = {}
        self.waveform_cache: Dict[str, WaveformData] = {}
        
    def generate_waveform(self, audio_path: str, force_regenerate: bool = False) -> Optional[WaveformData]:
        """파형 생성 또는 캐시에서 로드"""
        audio_path = str(Path(audio_path).resolve())
        
        # 캐시 확인
        if not force_regenerate:
            cached_waveform = self._load_from_cache(audio_path)
            if cached_waveform:
                self.waveform_cache[audio_path] = cached_waveform
                self.waveform_ready.emit(audio_path, cached_waveform)
                return cached_waveform
                
        # 이미 생성 중인지 확인
        if audio_path in self.active_threads:
            return None
            
        # 새로운 스레드로 생성
        thread = WaveformGeneratorThread(audio_path)
        thread.progress_updated.connect(
            lambda progress: self.generation_progress.emit(audio_path, progress)
        )
        thread.waveform_generated.connect(
            lambda waveform: self._on_waveform_generated(audio_path, waveform)
        )
        thread.error_occurred.connect(
            lambda error: self.generation_error.emit(audio_path, error)
        )
        thread.finished.connect(
            lambda: self._cleanup_thread(audio_path)
        )
        
        self.active_threads[audio_path] = thread
        thread.start()
        
        return None
        
    def _on_waveform_generated(self, audio_path: str, waveform_data: WaveformData):
        """파형 생성 완료 처리"""
        # 캐시에 저장
        self.waveform_cache[audio_path] = waveform_data
        self._save_to_cache(audio_path, waveform_data)
        
        # 시그널 발생
        self.waveform_ready.emit(audio_path, waveform_data)
        
    def _cleanup_thread(self, audio_path: str):
        """스레드 정리"""
        if audio_path in self.active_threads:
            thread = self.active_threads[audio_path]
            thread.deleteLater()
            del self.active_threads[audio_path]
            
    def get_cached_waveform(self, audio_path: str) -> Optional[WaveformData]:
        """캐시된 파형 데이터 가져오기"""
        audio_path = str(Path(audio_path).resolve())
        return self.waveform_cache.get(audio_path)
        
    def _get_cache_path(self, audio_path: str) -> Path:
        """캐시 파일 경로 생성"""
        # 파일 경로를 해시하여 캐시 파일명 생성
        import hashlib
        path_hash = hashlib.md5(audio_path.encode()).hexdigest()
        return self.cache_dir / f"{path_hash}.json"
        
    def _save_to_cache(self, audio_path: str, waveform_data: WaveformData):
        """캐시에 저장"""
        try:
            cache_path = self._get_cache_path(audio_path)
            cache_data = {
                "audio_path": audio_path,
                "waveform": waveform_data.to_dict(),
                "timestamp": Path(audio_path).stat().st_mtime
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
                
        except Exception as e:
            print(f"파형 캐시 저장 오류: {e}")
            
    def _load_from_cache(self, audio_path: str) -> Optional[WaveformData]:
        """캐시에서 로드"""
        try:
            cache_path = self._get_cache_path(audio_path)
            if not cache_path.exists():
                return None
                
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # 파일 수정 시간 확인
            current_mtime = Path(audio_path).stat().st_mtime
            cached_mtime = cache_data.get("timestamp", 0)
            
            if current_mtime != cached_mtime:
                # 파일이 변경됨, 캐시 무효
                cache_path.unlink()
                return None
                
            return WaveformData.from_dict(cache_data["waveform"])
            
        except Exception as e:
            print(f"파형 캐시 로드 오류: {e}")
            return None
            
    def clear_cache(self):
        """캐시 정리"""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            self.waveform_cache.clear()
        except Exception as e:
            print(f"캐시 정리 오류: {e}")
            
    def cancel_generation(self, audio_path: str):
        """파형 생성 취소"""
        if audio_path in self.active_threads:
            self.active_threads[audio_path].cancel()

class WaveformRenderer:
    """파형 렌더러"""
    
    @staticmethod
    def draw_waveform(painter: QPainter, waveform_data: WaveformData, 
                     rect, start_time: float, end_time: float, 
                     color: QColor = QColor(100, 200, 100)):
        """파형 그리기"""
        if not waveform_data or rect.width() <= 0 or rect.height() <= 0:
            return
            
        # 시간 범위의 피크 데이터 가져오기
        peaks = waveform_data.get_peaks_in_range(start_time, end_time, rect.width())
        
        if not peaks:
            return
            
        # 최대값으로 정규화
        max_peak = max(peaks) if peaks else 1.0
        if max_peak == 0:
            max_peak = 1.0
            
        # 파형 그리기
        painter.setPen(QPen(color, 1))
        
        center_y = rect.y() + rect.height() // 2
        max_amplitude = rect.height() // 2 - 2
        
        for i, peak in enumerate(peaks):
            if i >= rect.width():
                break
                
            x = rect.x() + i
            amplitude = int((peak / max_peak) * max_amplitude)
            
            # 상하 대칭으로 그리기
            painter.drawLine(x, center_y - amplitude, x, center_y + amplitude)
            
    @staticmethod
    def draw_simple_waveform(painter: QPainter, rect, color: QColor = QColor(100, 200, 100)):
        """간단한 더미 파형 그리기 (파형 데이터가 없을 때)"""
        painter.setPen(QPen(color, 1))
        
        center_y = rect.y() + rect.height() // 2
        
        # 간단한 사인파 패턴
        for x in range(rect.x(), rect.x() + rect.width(), 2):
            amplitude = int((rect.height() // 4) * np.sin((x - rect.x()) * 0.1))
            painter.drawLine(x, center_y - amplitude, x, center_y + amplitude) 