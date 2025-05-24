"""
BLOUcut 효과 매니저
클립에 적용된 효과들을 처리하고 렌더링
"""

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen
import cv2

class EffectsManager(QObject):
    """효과 매니저"""
    
    effect_applied = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        
    def apply_effects_to_frame(self, frame, effects, frame_time=0.0):
        """프레임에 효과들 적용"""
        if not effects:
            return frame
            
        result_frame = frame.copy()
        
        for effect in effects:
            result_frame = self.apply_single_effect(result_frame, effect, frame_time)
            
        return result_frame
        
    def apply_single_effect(self, frame, effect, frame_time):
        """단일 효과 적용"""
        effect_name = effect.get('name', '')
        effect_type = effect.get('type', '')
        parameters = effect.get('parameters', {})
        
        if effect_type == 'filter':
            return self.apply_filter_effect(frame, effect_name, parameters)
        elif effect_type == 'color':
            return self.apply_color_effect(frame, effect_name, parameters)
        elif effect_type == 'transition':
            return self.apply_transition_effect(frame, effect_name, parameters, frame_time)
        else:
            return frame
            
    def apply_filter_effect(self, frame, effect_name, parameters):
        """필터 효과 적용"""
        intensity = parameters.get('intensity', 0.5)
        
        if effect_name == "블러":
            blur_radius = int(intensity * 10) * 2 + 1  # 홀수로 만들기
            return cv2.GaussianBlur(frame, (blur_radius, blur_radius), 0)
            
        elif effect_name == "샤픈":
            # 샤프닝 커널
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(frame, -1, kernel)
            # 강도에 따라 블렌딩
            return cv2.addWeighted(frame, 1-intensity, sharpened, intensity, 0)
            
        elif effect_name == "빈티지":
            # 세피아 효과
            sepia_kernel = np.array([[0.272, 0.534, 0.131],
                                   [0.349, 0.686, 0.168],
                                   [0.393, 0.769, 0.189]])
            sepia = cv2.transform(frame, sepia_kernel)
            # 비네팅 효과 추가
            rows, cols = frame.shape[:2]
            X_resultant_kernel = cv2.getGaussianKernel(cols, cols/3)
            Y_resultant_kernel = cv2.getGaussianKernel(rows, rows/3)
            gaussian_kernel = Y_resultant_kernel * X_resultant_kernel.T
            mask = gaussian_kernel / gaussian_kernel.max()
            sepia = sepia * mask[:,:,np.newaxis]
            return np.clip(sepia, 0, 255).astype(np.uint8)
            
        elif effect_name == "흑백":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            
        elif effect_name == "카툰":
            # 카툰 효과
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_blur = cv2.medianBlur(gray, 5)
            edges = cv2.adaptiveThreshold(gray_blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
            color = cv2.bilateralFilter(frame, 9, 300, 300)
            cartoon = cv2.bitwise_and(color, color, mask=edges)
            return cartoon
            
        elif effect_name == "글로우":
            # 글로우 효과
            glow_intensity = parameters.get('intensity', 0.5)
            blur_radius = int(glow_intensity * 20) * 2 + 1
            blurred = cv2.GaussianBlur(frame, (blur_radius, blur_radius), 0)
            return cv2.addWeighted(frame, 1.0, blurred, glow_intensity * 0.8, 0)
            
        return frame
        
    def apply_color_effect(self, frame, effect_name, parameters):
        """색상 효과 적용"""
        if effect_name == "밝기/대비":
            brightness = parameters.get('brightness', 0) / 100.0
            contrast = parameters.get('contrast', 0) / 100.0
            
            # 밝기와 대비 조정
            adjusted = frame.astype(np.float32)
            adjusted = adjusted * (1 + contrast) + brightness * 255
            return np.clip(adjusted, 0, 255).astype(np.uint8)
            
        elif effect_name == "색조/채도":
            hue_shift = parameters.get('hue', 0)
            saturation = parameters.get('saturation', 0) / 100.0
            
            # BGR에서 HSV로 변환
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            
            # 색조 조정
            hsv[:,:,0] = (hsv[:,:,0] + hue_shift) % 180
            
            # 채도 조정
            hsv[:,:,1] = np.clip(hsv[:,:,1] * (1 + saturation), 0, 255)
            
            # 다시 BGR로 변환
            return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            
        elif effect_name == "색상 균형":
            cyan_red = parameters.get('cyan_red', 0) / 100.0
            magenta_green = parameters.get('magenta_green', 0) / 100.0
            yellow_blue = parameters.get('yellow_blue', 0) / 100.0
            
            # 색상 균형 조정 (간단한 구현)
            adjusted = frame.astype(np.float32)
            adjusted[:,:,0] += yellow_blue * 50  # Blue 채널
            adjusted[:,:,1] += magenta_green * 50  # Green 채널
            adjusted[:,:,2] += cyan_red * 50  # Red 채널
            
            return np.clip(adjusted, 0, 255).astype(np.uint8)
            
        elif effect_name == "색온도":
            temperature = parameters.get('temperature', 6500)
            
            # 색온도 조정 (간단한 구현)
            if temperature < 6500:
                # 따뜻한 톤 (빨간색 증가)
                factor = (6500 - temperature) / 2500.0
                adjusted = frame.astype(np.float32)
                adjusted[:,:,2] = np.clip(adjusted[:,:,2] * (1 + factor * 0.3), 0, 255)
            else:
                # 차가운 톤 (파란색 증가)
                factor = (temperature - 6500) / 3500.0
                adjusted = frame.astype(np.float32)
                adjusted[:,:,0] = np.clip(adjusted[:,:,0] * (1 + factor * 0.3), 0, 255)
                
            return np.clip(adjusted, 0, 255).astype(np.uint8)
            
        return frame
        
    def apply_transition_effect(self, frame, effect_name, parameters, frame_time):
        """전환 효과 적용"""
        duration = parameters.get('duration', 1.0)
        progress = min(frame_time / duration, 1.0) if duration > 0 else 1.0
        
        if effect_name == "페이드 인":
            alpha = progress
            return (frame * alpha).astype(np.uint8)
            
        elif effect_name == "페이드 아웃":
            alpha = 1.0 - progress
            return (frame * alpha).astype(np.uint8)
            
        elif effect_name == "줌 인":
            # 줌 인 효과
            height, width = frame.shape[:2]
            scale = 1.0 + progress * 0.2  # 20% 확대
            
            # 확대된 이미지 크기
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # 확대
            resized = cv2.resize(frame, (new_width, new_height))
            
            # 중앙에서 원본 크기만큼 크롭
            start_x = (new_width - width) // 2
            start_y = (new_height - height) // 2
            
            return resized[start_y:start_y+height, start_x:start_x+width]
            
        elif effect_name == "슬라이드 좌측":
            # 왼쪽에서 슬라이드
            height, width = frame.shape[:2]
            offset = int(width * (1.0 - progress))
            
            result = np.zeros_like(frame)
            if offset < width:
                result[:, offset:] = frame[:, :width-offset]
                
            return result
            
        elif effect_name == "슬라이드 우측":
            # 오른쪽에서 슬라이드
            height, width = frame.shape[:2]
            offset = int(width * progress)
            
            result = np.zeros_like(frame)
            if offset > 0:
                result[:, :offset] = frame[:, width-offset:]
                
            return result
            
        return frame
        
    def apply_clip_properties(self, frame, clip):
        """클립 속성들 적용 (변형, 색상 보정 등)"""
        if frame is None:
            return None
            
        # 색상 보정 적용
        result = self.apply_color_correction(frame, clip)
        
        # 변형 적용 (크기, 회전, 위치는 렌더링 시점에서 처리)
        
        return result
        
    def apply_color_correction(self, frame, clip):
        """색상 보정 적용"""
        brightness = getattr(clip, 'brightness', 0.0)
        contrast = getattr(clip, 'contrast', 0.0)
        saturation = getattr(clip, 'saturation', 0.0)
        hue = getattr(clip, 'hue', 0.0)
        
        if abs(brightness) < 0.01 and abs(contrast) < 0.01 and abs(saturation) < 0.01 and abs(hue) < 1:
            return frame
            
        # 밝기/대비 조정
        if abs(brightness) > 0.01 or abs(contrast) > 0.01:
            adjusted = frame.astype(np.float32)
            adjusted = adjusted * (1 + contrast) + brightness * 255
            frame = np.clip(adjusted, 0, 255).astype(np.uint8)
            
        # 색조/채도 조정
        if abs(saturation) > 0.01 or abs(hue) > 1:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            
            if abs(hue) > 1:
                hsv[:,:,0] = (hsv[:,:,0] + hue) % 180
                
            if abs(saturation) > 0.01:
                hsv[:,:,1] = np.clip(hsv[:,:,1] * (1 + saturation), 0, 255)
                
            frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            
        return frame
        
    def get_available_effects(self):
        """사용 가능한 효과 목록 반환"""
        return {
            'filter': [
                '블러', '샤픈', '빈티지', '흑백', '카툰', '글로우'
            ],
            'color': [
                '밝기/대비', '색조/채도', '색상 균형', '색온도', 'RGB 커브'
            ],
            'transition': [
                '페이드 인', '페이드 아웃', '슬라이드 좌측', '슬라이드 우측', '줌 인', '줌 아웃', '디졸브'
            ]
        } 