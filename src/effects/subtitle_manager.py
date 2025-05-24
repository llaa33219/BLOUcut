"""
BLOUcut 자막 매니저
자막 표시 및 관리
"""

import os
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPainter, QFont, QColor, QPen, QFontMetrics
from PyQt6.QtCore import Qt, QRect

class SubtitleManager(QObject):
    """자막 매니저"""
    
    subtitle_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.subtitles = []  # 자막 리스트
        
    def add_subtitle(self, start_frame, end_frame, text, properties=None):
        """자막 추가"""
        subtitle = {
            'start_frame': start_frame,
            'end_frame': end_frame,
            'text': text,
            'font_size': properties.get('font_size', 24) if properties else 24,
            'font_color': properties.get('font_color', QColor(255, 255, 255)) if properties else QColor(255, 255, 255),
            'position': properties.get('position', 'bottom') if properties else 'bottom',
            'x_offset': properties.get('x_offset', 0) if properties else 0,
            'y_offset': properties.get('y_offset', 0) if properties else 0,
            'outline': properties.get('outline', True) if properties else True,
            'outline_color': properties.get('outline_color', QColor(0, 0, 0)) if properties else QColor(0, 0, 0),
            'background': properties.get('background', False) if properties else False,
            'background_color': properties.get('background_color', QColor(0, 0, 0, 128)) if properties else QColor(0, 0, 0, 128)
        }
        
        self.subtitles.append(subtitle)
        self.subtitle_changed.emit()
        
    def remove_subtitle(self, index):
        """자막 제거"""
        if 0 <= index < len(self.subtitles):
            del self.subtitles[index]
            self.subtitle_changed.emit()
            
    def get_active_subtitles(self, current_frame):
        """현재 프레임에서 활성화된 자막들 반환"""
        active = []
        for subtitle in self.subtitles:
            if subtitle['start_frame'] <= current_frame <= subtitle['end_frame']:
                active.append(subtitle)
        return active
        
    def draw_subtitles(self, painter, rect, current_frame):
        """자막 그리기"""
        active_subtitles = self.get_active_subtitles(current_frame)
        
        for subtitle in active_subtitles:
            self.draw_single_subtitle(painter, rect, subtitle)
            
    def draw_single_subtitle(self, painter, rect, subtitle):
        """단일 자막 그리기"""
        # 폰트 설정
        font = QFont("맑은 고딕", subtitle['font_size'], QFont.Weight.Bold)
        painter.setFont(font)
        
        # 텍스트 크기 측정
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(subtitle['text'])
        text_height = metrics.height()
        
        # 위치 계산
        if subtitle['position'] == 'top':
            x = rect.x() + (rect.width() - text_width) // 2 + subtitle['x_offset']
            y = rect.y() + text_height + 20 + subtitle['y_offset']
        elif subtitle['position'] == 'center':
            x = rect.x() + (rect.width() - text_width) // 2 + subtitle['x_offset']
            y = rect.y() + (rect.height() + text_height) // 2 + subtitle['y_offset']
        else:  # bottom
            x = rect.x() + (rect.width() - text_width) // 2 + subtitle['x_offset']
            y = rect.y() + rect.height() - 30 + subtitle['y_offset']
            
        # 배경 그리기
        if subtitle['background']:
            bg_rect = QRect(x - 10, y - text_height - 5, text_width + 20, text_height + 10)
            painter.fillRect(bg_rect, subtitle['background_color'])
            
        # 외곽선 그리기
        if subtitle['outline']:
            painter.setPen(QPen(subtitle['outline_color'], 3))
            painter.drawText(x, y, subtitle['text'])
            painter.setPen(QPen(subtitle['outline_color'], 2))
            painter.drawText(x-1, y-1, subtitle['text'])
            painter.drawText(x+1, y-1, subtitle['text'])
            painter.drawText(x-1, y+1, subtitle['text'])
            painter.drawText(x+1, y+1, subtitle['text'])
            
        # 메인 텍스트 그리기
        painter.setPen(QPen(subtitle['font_color'], 1))
        painter.drawText(x, y, subtitle['text'])
        
    def clear_all_subtitles(self):
        """모든 자막 제거"""
        self.subtitles.clear()
        self.subtitle_changed.emit()
        
    def export_srt(self, file_path, fps=30):
        """SRT 파일로 내보내기"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for i, subtitle in enumerate(self.subtitles, 1):
                    start_time = self.frames_to_timecode(subtitle['start_frame'], fps)
                    end_time = self.frames_to_timecode(subtitle['end_frame'], fps)
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{subtitle['text']}\n\n")
                    
            return True
        except Exception as e:
            print(f"SRT 내보내기 실패: {e}")
            return False
            
    def import_srt(self, file_path, fps=30):
        """SRT 파일에서 불러오기"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # SRT 파싱
            entries = content.strip().split('\n\n')
            
            for entry in entries:
                lines = entry.strip().split('\n')
                if len(lines) >= 3:
                    # 타임코드 파싱
                    timecode_line = lines[1]
                    if ' --> ' in timecode_line:
                        start_str, end_str = timecode_line.split(' --> ')
                        start_frame = self.timecode_to_frames(start_str.strip(), fps)
                        end_frame = self.timecode_to_frames(end_str.strip(), fps)
                        
                        # 텍스트 추출
                        text = '\n'.join(lines[2:])
                        
                        self.add_subtitle(start_frame, end_frame, text)
                        
            return True
        except Exception as e:
            print(f"SRT 불러오기 실패: {e}")
            return False
            
    def frames_to_timecode(self, frames, fps):
        """프레임을 타임코드로 변환"""
        total_seconds = frames / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        
    def timecode_to_frames(self, timecode, fps):
        """타임코드를 프레임으로 변환"""
        # 00:00:00,000 형식
        time_part, ms_part = timecode.split(',')
        h, m, s = map(int, time_part.split(':'))
        ms = int(ms_part)
        
        total_seconds = h * 3600 + m * 60 + s + ms / 1000.0
        return int(total_seconds * fps) 