"""
BLOUcut 컴포지팅 엔진
여러 클립을 레이어별로 합성하여 최종 프레임 생성
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
import os
import math

from .media_analyzer import MediaAnalyzer
from .keyframe import KeyframeManager
from ..effects.effect_engine import EffectEngine, effect_engine
from ..timeline.timeline_clip import TimelineClip

class Transform:
    """변환 정보"""
    
    def __init__(self):
        self.position_x = 0.0
        self.position_y = 0.0
        self.scale_x = 100.0
        self.scale_y = 100.0
        self.rotation = 0.0
        self.opacity = 100.0
        
    def apply_keyframes(self, keyframes: KeyframeManager, frame: int):
        """키프레임 값 적용"""
        props = ['position_x', 'position_y', 'scale_x', 'scale_y', 'rotation', 'opacity']
        for prop in props:
            value = keyframes.get_value_at_frame(prop, frame)
            if value is not None:
                setattr(self, prop, value)

class CompositeLayer:
    """합성 레이어"""
    
    def __init__(self, clip: TimelineClip, frame: int):
        self.clip = clip
        self.frame = frame  # 타임라인 상의 절대 프레임
        self.relative_frame = frame - clip.start_frame  # 클립 내 상대 프레임
        self.transform = Transform()
        self.visible = True
        self.blend_mode = "normal"
        
        # 키프레임이 있으면 적용
        if hasattr(clip, 'keyframes') and clip.keyframes:
            self.transform.apply_keyframes(clip.keyframes, self.relative_frame)
            
        # 클립의 기본 변환 속성 적용
        if hasattr(clip, 'position_x'):
            self.transform.position_x += clip.position_x
        if hasattr(clip, 'position_y'):
            self.transform.position_y += clip.position_y
        if hasattr(clip, 'scale'):
            self.transform.scale_x = self.transform.scale_y = clip.scale
        if hasattr(clip, 'rotation'):
            self.transform.rotation += clip.rotation
        if hasattr(clip, 'opacity'):
            self.transform.opacity = clip.opacity
            
        # opacity가 너무 낮으면 강제로 100.0으로 설정 (완전 불투명)
        if self.transform.opacity < 50.0:
            self.transform.opacity = 100.0

class Compositor:
    """컴포지팅 엔진"""
    
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        self.effect_engine = effect_engine
        
        # 캐시
        self.frame_cache = {}
        self.max_cache_size = 50
        
    def composite_frame(self, clips: List[TimelineClip], frame: int, 
                       background_color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
        """프레임 합성 - 멀티트랙 지원 강화 (UI 트랙 순서 수정)"""
        
        # 배경 생성
        result = np.full((self.height, self.width, 3), background_color, dtype=np.uint8)
        
        # 활성 클립들 찾기 (프레임 범위 내에 있는 클립들)
        active_clips = []
        for clip in clips:
            if clip.start_frame <= frame < clip.start_frame + clip.duration:
                active_clips.append(clip)
                
        if not active_clips:
            return result
            
        # 트랙 순서로 정렬 (높은 트랙부터 낮은 트랙 순 - UI 위쪽이 마지막에 그려짐)
        active_clips.sort(key=lambda c: c.track, reverse=True)
        
        # 트랙별 정보 출력 (디버깅용)
        current_seconds = frame / 30.0
        if not hasattr(self, '_last_comp_log_second') or int(self._last_comp_log_second) != int(current_seconds):
            track_order = [f"트랙{clip.track}:{clip.name}" for clip in active_clips]
            print(f"[Compositor] 프레임 {frame}: {len(active_clips)}개 클립 합성")
            print(f"  합성 순서 (뒤→앞): {' → '.join(track_order)}")
            self._last_comp_log_second = current_seconds
        
        # 각 클립을 레이어로 렌더링 (높은 트랙부터 낮은 트랙 순)
        for i, clip in enumerate(active_clips):
            try:
                layer = CompositeLayer(clip, frame)
                if layer.visible and layer.relative_frame >= 0:
                    layer_image = self._render_layer(layer)
                    if layer_image is not None:
                        # 투명도 확인
                        opacity = layer.transform.opacity
                        print(f"  [{i+1}/{len(active_clips)}] 트랙{clip.track} '{clip.name}' 합성 (투명도: {opacity:.1f}%)")
                        result = self._composite_layer(result, layer_image, layer.transform, layer.blend_mode, clip)
                    else:
                        print(f"  [{i+1}/{len(active_clips)}] 트랙{clip.track} '{clip.name}' 이미지 로드 실패")
                else:
                    print(f"  [{i+1}/{len(active_clips)}] 트랙{clip.track} '{clip.name}' 비활성 (visible={layer.visible}, frame={layer.relative_frame})")
                    
            except Exception as e:
                print(f"레이어 합성 오류 (트랙{clip.track} '{clip.name}'): {e}")
                continue
                
        print(f"[Compositor] 프레임 {frame} 합성 완료")
        return result
        
    def _render_layer(self, layer: CompositeLayer) -> Optional[np.ndarray]:
        """개별 레이어 렌더링"""
        clip = layer.clip
        
        try:
            # 미디어 타입별 처리
            if clip.media_type == 'image':
                image = self._load_image(clip.media_path)
            elif clip.media_type == 'video':
                image = self._load_video_frame(clip.media_path, layer.relative_frame)
            elif clip.media_type == 'audio':
                # 오디오는 시각적 표현 (파형 등)
                image = self._render_audio_visualization(clip, layer.relative_frame)
            else:
                return None
                
            if image is None:
                return None
                
            # 효과 적용
            if hasattr(clip, 'effects') and clip.effects:
                image = self.effect_engine.apply_effects(image, clip.effects, layer.relative_frame)
                
            # 색상 보정 적용 (키프레임 지원)
            image = self._apply_color_correction(image, clip, layer.relative_frame)
            
            return image
            
        except Exception as e:
            print(f"레이어 렌더링 오류: {e}")
            return None
        
    def _load_image(self, image_path: str) -> Optional[np.ndarray]:
        """이미지 로드 - 화면 크기에 맞춰 비율 유지"""
        if not os.path.exists(image_path):
            return None
            
        image = cv2.imread(image_path)
        if image is None:
            return None
        
        # 이미지를 화면 크기에 맞춰 리사이즈 (비율 유지)
        h, w = image.shape[:2]
        
        # 화면 크기에 맞춰 스케일 계산 (비율 유지)
        scale_x = self.width / w
        scale_y = self.height / h
        scale = min(scale_x, scale_y)  # 비율을 유지하면서 화면에 맞춤
        
        # 새로운 크기 계산
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # 이미지 리사이즈
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        
        return image
        
    def _load_video_frame(self, video_path: str, frame_num: int) -> Optional[np.ndarray]:
        """비디오 프레임 로드 (썸네일 기반)"""
        try:
            # 미디어 정보 가져오기
            media_info = MediaAnalyzer.get_media_info(video_path)
            if not media_info:
                return None
                
            # 프레임을 시간으로 변환
            fps = media_info.get('fps', 30)
            time_seconds = frame_num / fps
            
            # 썸네일 경로 찾기
            thumbnail_path = MediaAnalyzer.get_thumbnail_path(video_path, time_seconds)
            
            if thumbnail_path and os.path.exists(thumbnail_path):
                # 썸네일을 직접 로드 (원본 크기 유지)
                image = cv2.imread(thumbnail_path)
                if image is not None:
                    # 화면 크기에 맞춰 리사이즈
                    image = cv2.resize(image, (self.width, self.height), interpolation=cv2.INTER_LANCZOS4)
                    return image
            else:
                # 썸네일이 없으면 생성 시도
                print(f"[Compositor] 썸네일 없음, 생성 시도: {video_path} @ {time_seconds:.1f}s")
                if MediaAnalyzer.generate_thumbnail(video_path, time_seconds):
                    thumbnail_path = MediaAnalyzer.get_thumbnail_path(video_path, time_seconds)
                    if thumbnail_path and os.path.exists(thumbnail_path):
                        image = cv2.imread(thumbnail_path)
                        if image is not None:
                            # 화면 크기에 맞춰 리사이즈
                            image = cv2.resize(image, (self.width, self.height), interpolation=cv2.INTER_LANCZOS4)
                            return image
                        
            # 모든 방법 실패시 플레이스홀더
            return self._create_placeholder(f"비디오\n{os.path.basename(video_path)}\n프레임 {frame_num}")
            
        except Exception as e:
            print(f"비디오 프레임 로드 오류: {e}")
            return self._create_placeholder("비디오 로드 실패")
            
    def _render_audio_visualization(self, clip: TimelineClip, frame: int) -> np.ndarray:
        """오디오 시각화 렌더링"""
        # 간단한 파형 시각화
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 배경 그라데이션
        for y in range(self.height):
            intensity = int(20 + (y / self.height) * 20)
            canvas[y, :] = [intensity, intensity * 1.2, intensity * 1.5]
            
        # 파형 그리기 (간단한 시뮬레이션)
        center_y = self.height // 2
        wave_height = self.height // 4
        
        for x in range(0, self.width, 4):
            # 시간 기반 파형 생성
            time = (x + frame * 10) * 0.01
            wave = math.sin(time) * 0.3 + math.sin(time * 2.5) * 0.2 + math.sin(time * 0.7) * 0.1
            y = center_y + int(wave * wave_height)
            
            # 파형 라인 그리기
            cv2.line(canvas, (x, center_y), (x, y), (100, 255, 100), 2)
            
        # 중앙에 오디오 아이콘
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"AUDIO: {os.path.basename(clip.media_path)}"
        text_size = cv2.getTextSize(text, font, 1, 2)[0]
        text_x = (self.width - text_size[0]) // 2
        text_y = (self.height + text_size[1]) // 2
        cv2.putText(canvas, text, (text_x, text_y), font, 1, (255, 255, 255), 2)
        
        return canvas
        
    def _apply_color_correction(self, image: np.ndarray, clip: TimelineClip, frame: int) -> np.ndarray:
        """색상 보정 적용 (키프레임 지원) - 안전한 버전"""
        try:
            if not hasattr(clip, 'keyframes') or not clip.keyframes:
                return image
                
            # 키프레임에서 색상 보정 값들 가져오기
            color_props = ['brightness', 'contrast', 'saturation', 'hue', 'gamma']
            corrections = {}
            
            for prop in color_props:
                value = clip.keyframes.get_value_at_frame(prop, frame)
                if value is not None:
                    corrections[prop] = value
                    
            if not corrections:
                return image
                
            # 간단한 색상 보정 (OpenCV 기본 기능만 사용)
            result = image.copy()
            
            # 밝기 조정
            if 'brightness' in corrections:
                brightness = corrections['brightness']
                result = cv2.convertScaleAbs(result, alpha=1.0, beta=brightness)
                
            # 대비 조정
            if 'contrast' in corrections:
                contrast = corrections['contrast'] / 100.0
                result = cv2.convertScaleAbs(result, alpha=contrast, beta=0)
                
            return result
            
        except Exception as e:
            print(f"색상 보정 오류: {e}")
            return image
        
    def _composite_layer(self, base: np.ndarray, layer: np.ndarray, 
                        transform: Transform, blend_mode: str, clip: TimelineClip) -> np.ndarray:
        """레이어 합성 - 이미지 오버레이 지원"""
        
        # opacity 값 정규화 (100.0 기준을 1.0으로 변환)
        opacity = transform.opacity / 100.0
        
        # 이미지 클립인 경우 오버레이 방식으로 합성
        if hasattr(clip, 'media_type') and clip.media_type == 'image':
            return self._overlay_image(base, layer, transform, opacity)
        else:
            # 비디오는 기존 방식대로 (전체 화면)
            transformed_layer = self._apply_transform(layer, transform)
            if transformed_layer.shape != base.shape:
                transformed_layer = cv2.resize(transformed_layer, (base.shape[1], base.shape[0]))
            return self._blend_images(base, transformed_layer, blend_mode, opacity)
            
    def _overlay_image(self, base: np.ndarray, overlay: np.ndarray, 
                      transform: Transform, opacity: float) -> np.ndarray:
        """이미지를 베이스 위에 중앙 오버레이로 배치"""
        try:
            # 결과 이미지는 베이스로 시작
            result = base.copy()
            
            # 오버레이 위치 계산 (중앙 배치)
            base_h, base_w = base.shape[:2]
            overlay_h, overlay_w = overlay.shape[:2]
            
            # 중앙 위치 계산 (transform 고려)
            x_offset = (base_w - overlay_w) // 2 + int(transform.position_x)
            y_offset = (base_h - overlay_h) // 2 + int(transform.position_y)
            
            # 경계 체크
            x_offset = max(0, min(x_offset, base_w - overlay_w))
            y_offset = max(0, min(y_offset, base_h - overlay_h))
            
            # 실제 배치 가능한 영역 계산
            end_x = min(x_offset + overlay_w, base_w)
            end_y = min(y_offset + overlay_h, base_h)
            
            if end_x > x_offset and end_y > y_offset:
                # 오버레이할 영역
                overlay_region = overlay[:end_y-y_offset, :end_x-x_offset]
                base_region = result[y_offset:end_y, x_offset:end_x]
                
                # 알파 블렌딩
                if opacity == 1.0:
                    result[y_offset:end_y, x_offset:end_x] = overlay_region
                else:
                    blended = (base_region.astype(np.float32) * (1 - opacity) + 
                             overlay_region.astype(np.float32) * opacity).astype(np.uint8)
                    result[y_offset:end_y, x_offset:end_x] = blended
                
                print(f"[이미지 오버레이] {overlay_w}x{overlay_h} 이미지를 중앙 ({x_offset},{y_offset})에 배치 (투명도: {opacity:.1f})")
            
            return result
            
        except Exception as e:
            print(f"이미지 오버레이 오류: {e}")
            return base
        
    def _apply_transform(self, image: np.ndarray, transform: Transform) -> np.ndarray:
        """변환 적용 (위치, 크기, 회전)"""
        h, w = image.shape[:2]
        
        # 변환 매트릭스 생성
        center_x, center_y = w / 2, h / 2
        
        # 스케일 적용
        scale_x = transform.scale_x / 100.0
        scale_y = transform.scale_y / 100.0
        
        # 회전 매트릭스
        rotation_matrix = cv2.getRotationMatrix2D((center_x, center_y), transform.rotation, 1.0)
        
        # 스케일 적용
        scale_matrix = np.array([[scale_x, 0, 0], [0, scale_y, 0]], dtype=np.float32)
        
        # 변환 적용
        if transform.rotation != 0:
            image = cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR)
            
        if scale_x != 1.0 or scale_y != 1.0:
            new_w = int(w * scale_x)
            new_h = int(h * scale_y)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # 원본 크기 캔버스에 중앙 배치
            canvas = np.zeros((h, w, 3), dtype=np.uint8)
            y_offset = (h - new_h) // 2
            x_offset = (w - new_w) // 2
            
            if y_offset >= 0 and x_offset >= 0:
                canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = image
            image = canvas
            
        # 위치 이동
        if transform.position_x != 0 or transform.position_y != 0:
            translation_matrix = np.float32([[1, 0, transform.position_x], [0, 1, transform.position_y]])
            image = cv2.warpAffine(image, translation_matrix, (w, h), flags=cv2.INTER_LINEAR)
            
        return image
        
    def _blend_images(self, base: np.ndarray, overlay: np.ndarray, 
                     blend_mode: str, opacity: float) -> np.ndarray:
        """이미지 블렌딩 - 값 범위 문제 해결"""
        try:
            if overlay.shape != base.shape:
                # 크기가 다르면 오버레이를 베이스 크기에 맞춤
                overlay = cv2.resize(overlay, (base.shape[1], base.shape[0]))
                
            # 안전한 블렌딩 (기본 알파 블렌딩만 사용)
            opacity = max(0.0, min(1.0, opacity))  # 0-1 범위로 제한
            
            # addWeighted 대신 수동 블렌딩 사용 (값 범위 보존)
            if opacity == 0.0:
                result = base.copy()
            elif opacity == 1.0:
                result = overlay.copy()
            else:
                # 수동 알파 블렌딩
                result = (base.astype(np.float32) * (1 - opacity) + 
                         overlay.astype(np.float32) * opacity).astype(np.uint8)
            
            return result
            
        except Exception as e:
            print(f"블렌딩 오류: {e}")
            # 오류 발생시 기본 이미지 반환
            return base
            
    def _create_placeholder(self, text: str) -> np.ndarray:
        """플레이스홀더 이미지 생성"""
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        canvas.fill(50)  # 어두운 회색
        
        # 텍스트 추가
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        thickness = 2
        
        # 여러 줄 텍스트 처리
        lines = text.split('\n')
        total_height = len(lines) * 30
        start_y = (self.height - total_height) // 2
        
        for i, line in enumerate(lines):
            text_size = cv2.getTextSize(line, font, font_scale, thickness)[0]
            text_x = (self.width - text_size[0]) // 2
            text_y = start_y + i * 30 + text_size[1]
            cv2.putText(canvas, line, (text_x, text_y), font, font_scale, (200, 200, 200), thickness)
            
        return canvas
        
    def _get_cache_key(self, clips: List[TimelineClip], frame: int) -> str:
        """캐시 키 생성"""
        # 클립 정보와 프레임으로 유니크한 키 생성
        clip_info = []
        for clip in clips:
            if clip.start_frame <= frame < clip.start_frame + clip.duration:
                relative_frame = frame - clip.start_frame
                clip_key = f"{clip.media_path}:{relative_frame}:{clip.track}"
                clip_info.append(clip_key)
                
        return f"frame_{frame}:" + "|".join(sorted(clip_info))
        
    def _cache_frame(self, cache_key: str, frame: np.ndarray):
        """프레임 캐시"""
        if len(self.frame_cache) >= self.max_cache_size:
            # 가장 오래된 항목 제거
            oldest_key = next(iter(self.frame_cache))
            del self.frame_cache[oldest_key]
            
        self.frame_cache[cache_key] = frame.copy()
        
    def clear_cache(self):
        """캐시 클리어"""
        self.frame_cache.clear()
        
    def set_resolution(self, width: int, height: int):
        """해상도 설정"""
        if self.width != width or self.height != height:
            self.width = width
            self.height = height
            self.clear_cache()  # 해상도가 변경되면 캐시 클리어

# 전역 컴포지터 인스턴스
compositor = Compositor() 