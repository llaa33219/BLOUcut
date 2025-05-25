"""
BLOUcut 효과 엔진
비디오/이미지에 다양한 효과를 적용하는 엔진
"""

import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import math

class EffectType(Enum):
    """효과 타입"""
    COLOR_CORRECTION = "color_correction"
    BLUR = "blur"
    SHARPEN = "sharpen"
    NOISE = "noise"
    DISTORTION = "distortion"
    ARTISTIC = "artistic"
    TRANSITION = "transition"

class BlendMode(Enum):
    """블렌드 모드"""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"
    ADD = "add"
    SUBTRACT = "subtract"

class Effect:
    """개별 효과"""
    
    def __init__(self, name: str, effect_type: EffectType):
        self.name = name
        self.effect_type = effect_type
        self.enabled = True
        self.parameters = {}
        self.blend_mode = BlendMode.NORMAL
        self.opacity = 100.0  # 0-100%
        
    def apply(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """효과 적용 (서브클래스에서 구현)"""
        return image
        
    def set_parameter(self, name: str, value: Any):
        """파라미터 설정"""
        self.parameters[name] = value
        
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """파라미터 가져오기"""
        return self.parameters.get(name, default)

class ColorCorrectionEffect(Effect):
    """색상 보정 효과"""
    
    def __init__(self):
        super().__init__("Color Correction", EffectType.COLOR_CORRECTION)
        self.parameters = {
            'brightness': 0,      # -100 ~ 100
            'contrast': 0,        # -100 ~ 100  
            'saturation': 0,      # -100 ~ 100
            'hue': 0,            # -180 ~ 180
            'gamma': 1.0,        # 0.1 ~ 3.0
            'highlights': 0,      # -100 ~ 100
            'shadows': 0,         # -100 ~ 100
            'temperature': 0,     # -100 ~ 100 (색온도)
            'tint': 0,           # -100 ~ 100 (색조)
        }
        
    def apply(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """색상 보정 적용"""
        result = image.copy().astype(np.float32)
        
        # 밝기 조정
        brightness = self.get_parameter('brightness', 0) / 100.0
        if brightness != 0:
            result = result + (brightness * 255)
            result = np.clip(result, 0, 255)
            
        # 대비 조정
        contrast = self.get_parameter('contrast', 0) / 100.0
        if contrast != 0:
            factor = (259 * (contrast * 255 + 255)) / (255 * (259 - contrast * 255))
            result = factor * (result - 128) + 128
            result = np.clip(result, 0, 255)
            
        # 감마 보정
        gamma = self.get_parameter('gamma', 1.0)
        if gamma != 1.0:
            gamma_table = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 
                                  for i in np.arange(0, 256)]).astype(np.uint8)
            result = cv2.LUT(result.astype(np.uint8), gamma_table).astype(np.float32)
            
        # HSV로 변환하여 채도/색상 조정
        saturation = self.get_parameter('saturation', 0) / 100.0
        hue = self.get_parameter('hue', 0)
        
        if saturation != 0 or hue != 0:
            hsv = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            
            # 색상 조정
            if hue != 0:
                hsv[:, :, 0] = (hsv[:, :, 0] + hue) % 180
                
            # 채도 조정
            if saturation != 0:
                hsv[:, :, 1] = hsv[:, :, 1] * (1 + saturation)
                hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
                
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
            
        # 색온도 조정
        temperature = self.get_parameter('temperature', 0) / 100.0
        if temperature != 0:
            # 간단한 색온도 시뮬레이션
            if temperature > 0:  # 따뜻하게
                result[:, :, 2] = result[:, :, 2] * (1 + temperature * 0.3)  # 빨강 증가
                result[:, :, 0] = result[:, :, 0] * (1 - temperature * 0.1)  # 파랑 감소
            else:  # 차갑게
                result[:, :, 0] = result[:, :, 0] * (1 - temperature * 0.3)  # 파랑 증가
                result[:, :, 2] = result[:, :, 2] * (1 + temperature * 0.1)  # 빨강 감소
                
        return np.clip(result, 0, 255).astype(np.uint8)

class BlurEffect(Effect):
    """블러 효과"""
    
    def __init__(self):
        super().__init__("Blur", EffectType.BLUR)
        self.parameters = {
            'radius': 5,          # 블러 반지름
            'type': 'gaussian',   # gaussian, motion, radial
            'angle': 0,           # 모션 블러 각도 (motion 타입용)
            'center_x': 50,       # 방사형 블러 중심 X (radial 타입용)
            'center_y': 50,       # 방사형 블러 중심 Y (radial 타입용)
        }
        
    def apply(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """블러 효과 적용"""
        radius = max(1, self.get_parameter('radius', 5))
        blur_type = self.get_parameter('type', 'gaussian')
        
        if blur_type == 'gaussian':
            return cv2.GaussianBlur(image, (radius*2+1, radius*2+1), 0)
            
        elif blur_type == 'motion':
            angle = self.get_parameter('angle', 0)
            kernel = self._create_motion_blur_kernel(radius, angle)
            return cv2.filter2D(image, -1, kernel)
            
        elif blur_type == 'radial':
            return self._apply_radial_blur(image, radius)
            
        return image
        
    def _create_motion_blur_kernel(self, radius: int, angle: float) -> np.ndarray:
        """모션 블러 커널 생성"""
        kernel_size = radius * 2 + 1
        kernel = np.zeros((kernel_size, kernel_size))
        
        # 각도를 라디안으로 변환
        angle_rad = math.radians(angle)
        
        # 선형 모션 블러 커널 생성
        center = kernel_size // 2
        for i in range(kernel_size):
            x = int(center + (i - center) * math.cos(angle_rad))
            y = int(center + (i - center) * math.sin(angle_rad))
            if 0 <= x < kernel_size and 0 <= y < kernel_size:
                kernel[y, x] = 1
                
        return kernel / np.sum(kernel)
        
    def _apply_radial_blur(self, image: np.ndarray, radius: int) -> np.ndarray:
        """방사형 블러 적용"""
        h, w = image.shape[:2]
        center_x = int(w * self.get_parameter('center_x', 50) / 100)
        center_y = int(h * self.get_parameter('center_y', 50) / 100)
        
        # 방사형 블러는 복잡한 구현이 필요하므로 간단히 가우시안 블러로 대체
        return cv2.GaussianBlur(image, (radius*2+1, radius*2+1), 0)

class SharpenEffect(Effect):
    """샤펜 효과"""
    
    def __init__(self):
        super().__init__("Sharpen", EffectType.BLUR)
        self.parameters = {
            'amount': 50,         # 샤펜 강도 0-200
            'radius': 1,          # 샤펜 반지름
            'threshold': 0,       # 임계값
        }
        
    def apply(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """샤펜 효과 적용"""
        amount = self.get_parameter('amount', 50) / 100.0
        radius = self.get_parameter('radius', 1)
        
        # 언샤프 마스크 방법
        blurred = cv2.GaussianBlur(image, (radius*2+1, radius*2+1), 0)
        sharpened = cv2.addWeighted(image, 1 + amount, blurred, -amount, 0)
        
        return np.clip(sharpened, 0, 255).astype(np.uint8)

class NoiseEffect(Effect):
    """노이즈 효과"""
    
    def __init__(self):
        super().__init__("Noise", EffectType.NOISE)
        self.parameters = {
            'amount': 10,         # 노이즈 양
            'type': 'gaussian',   # gaussian, uniform, salt_pepper
            'monochrome': False,  # 흑백 노이즈 여부
        }
        
    def apply(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """노이즈 효과 적용"""
        amount = self.get_parameter('amount', 10) / 100.0
        noise_type = self.get_parameter('type', 'gaussian')
        monochrome = self.get_parameter('monochrome', False)
        
        h, w = image.shape[:2]
        
        if noise_type == 'gaussian':
            if monochrome:
                noise = np.random.normal(0, amount * 255, (h, w, 1))
                noise = np.repeat(noise, 3, axis=2)
            else:
                noise = np.random.normal(0, amount * 255, image.shape)
                
        elif noise_type == 'uniform':
            if monochrome:
                noise = np.random.uniform(-amount * 255, amount * 255, (h, w, 1))
                noise = np.repeat(noise, 3, axis=2)
            else:
                noise = np.random.uniform(-amount * 255, amount * 255, image.shape)
                
        elif noise_type == 'salt_pepper':
            noise = np.zeros(image.shape)
            coords = np.random.random(image.shape[:2]) < amount
            noise[coords] = 255 if np.random.random() > 0.5 else -255
            if not monochrome:
                noise = np.stack([noise] * 3, axis=2)
                
        result = image.astype(np.float32) + noise
        return np.clip(result, 0, 255).astype(np.uint8)

class VignetteEffect(Effect):
    """비네트 효과"""
    
    def __init__(self):
        super().__init__("Vignette", EffectType.ARTISTIC)
        self.parameters = {
            'amount': 50,         # 비네트 강도
            'size': 50,           # 비네트 크기
            'roundness': 50,      # 둥근 정도
            'feather': 50,        # 부드러운 정도
        }
        
    def apply(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """비네트 효과 적용"""
        h, w = image.shape[:2]
        amount = self.get_parameter('amount', 50) / 100.0
        size = self.get_parameter('size', 50) / 100.0
        
        # 중심에서의 거리 계산
        center_x, center_y = w // 2, h // 2
        Y, X = np.ogrid[:h, :w]
        
        # 정규화된 거리 계산
        dist_x = (X - center_x) / (w / 2)
        dist_y = (Y - center_y) / (h / 2)
        distance = np.sqrt(dist_x**2 + dist_y**2)
        
        # 비네트 마스크 생성
        vignette = 1 - np.clip((distance - size) / (1 - size), 0, 1) * amount
        vignette = np.stack([vignette] * 3, axis=2)
        
        result = image.astype(np.float32) * vignette
        return np.clip(result, 0, 255).astype(np.uint8)

class EffectEngine:
    """효과 엔진"""
    
    def __init__(self):
        self.available_effects = {
            'color_correction': ColorCorrectionEffect,
            'blur': BlurEffect,
            'sharpen': SharpenEffect,
            'noise': NoiseEffect,
            'vignette': VignetteEffect,
        }
        
    def create_effect(self, effect_name: str) -> Optional[Effect]:
        """효과 생성"""
        if effect_name in self.available_effects:
            return self.available_effects[effect_name]()
        return None
        
    def apply_effects(self, image: np.ndarray, effects: List[Effect], 
                     frame: int = 0, **kwargs) -> np.ndarray:
        """여러 효과를 순서대로 적용"""
        result = image.copy()
        
        for effect in effects:
            if not effect.enabled:
                continue
                
            try:
                # 효과 적용
                processed = effect.apply(result, frame=frame, **kwargs)
                
                # 투명도 적용
                if effect.opacity < 100:
                    alpha = effect.opacity / 100.0
                    processed = cv2.addWeighted(result, 1 - alpha, processed, alpha, 0)
                    
                # 블렌드 모드 적용
                result = self._apply_blend_mode(result, processed, effect.blend_mode)
                
            except Exception as e:
                print(f"효과 적용 오류 ({effect.name}): {e}")
                continue
                
        return result
        
    def _apply_blend_mode(self, base: np.ndarray, overlay: np.ndarray, 
                         blend_mode: BlendMode) -> np.ndarray:
        """블렌드 모드 적용"""
        base_f = base.astype(np.float32) / 255.0
        overlay_f = overlay.astype(np.float32) / 255.0
        
        if blend_mode == BlendMode.NORMAL:
            result = overlay_f
            
        elif blend_mode == BlendMode.MULTIPLY:
            result = base_f * overlay_f
            
        elif blend_mode == BlendMode.SCREEN:
            result = 1 - (1 - base_f) * (1 - overlay_f)
            
        elif blend_mode == BlendMode.OVERLAY:
            mask = base_f < 0.5
            result = np.where(mask, 2 * base_f * overlay_f, 
                            1 - 2 * (1 - base_f) * (1 - overlay_f))
            
        elif blend_mode == BlendMode.SOFT_LIGHT:
            mask = overlay_f < 0.5
            result = np.where(mask, 
                            base_f - (1 - 2 * overlay_f) * base_f * (1 - base_f),
                            base_f + (2 * overlay_f - 1) * (np.sqrt(base_f) - base_f))
            
        elif blend_mode == BlendMode.HARD_LIGHT:
            mask = overlay_f < 0.5
            result = np.where(mask, 2 * base_f * overlay_f,
                            1 - 2 * (1 - base_f) * (1 - overlay_f))
            
        elif blend_mode == BlendMode.ADD:
            result = base_f + overlay_f
            
        elif blend_mode == BlendMode.SUBTRACT:
            result = base_f - overlay_f
            
        else:
            result = overlay_f
            
        return np.clip(result * 255, 0, 255).astype(np.uint8)
        
    def get_available_effects(self) -> List[str]:
        """사용 가능한 효과 목록"""
        return list(self.available_effects.keys())

# 전역 효과 엔진 인스턴스
effect_engine = EffectEngine() 