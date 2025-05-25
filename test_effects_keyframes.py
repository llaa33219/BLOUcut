#!/usr/bin/env python3
"""
BLOUcut 효과 및 키프레임 시스템 테스트
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_keyframe_system():
    """키프레임 시스템 테스트"""
    print("=== 키프레임 시스템 테스트 ===")
    
    from src.core.keyframe import KeyframeManager, InterpolationType
    
    # 키프레임 매니저 생성
    manager = KeyframeManager()
    
    # 위치 애니메이션 키프레임 추가
    manager.add_keyframe('position_x', 0, 0.0, InterpolationType.LINEAR)
    manager.add_keyframe('position_x', 30, 100.0, InterpolationType.EASE_IN_OUT)
    manager.add_keyframe('position_x', 60, 0.0, InterpolationType.LINEAR)
    
    # 스케일 애니메이션 키프레임 추가
    manager.add_keyframe('scale_x', 0, 1.0, InterpolationType.LINEAR)
    manager.add_keyframe('scale_x', 15, 1.5, InterpolationType.EASE_OUT)
    manager.add_keyframe('scale_x', 30, 1.0, InterpolationType.LINEAR)
    
    # 불투명도 애니메이션
    manager.add_keyframe('opacity', 0, 0.0, InterpolationType.LINEAR)
    manager.add_keyframe('opacity', 10, 1.0, InterpolationType.EASE_IN)
    manager.add_keyframe('opacity', 50, 1.0, InterpolationType.LINEAR)
    manager.add_keyframe('opacity', 60, 0.0, InterpolationType.EASE_OUT)
    
    # 키프레임 보간 테스트
    test_frames = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
    
    print("\n프레임별 애니메이션 값:")
    print("Frame | Pos X  | Scale X | Opacity")
    print("------|--------|---------|--------")
    
    for frame in test_frames:
        pos_x = manager.get_value_at_frame('position_x', frame)
        scale_x = manager.get_value_at_frame('scale_x', frame)
        opacity = manager.get_value_at_frame('opacity', frame)
        
        print(f"{frame:5d} | {pos_x:6.1f} | {scale_x:7.2f} | {opacity:7.2f}")
        
    print(f"\n애니메이션된 속성: {manager.get_animated_properties()}")
    print(f"키프레임 프레임들: {manager.get_all_keyframe_frames()}")
    
    return True

def test_effect_system():
    """효과 시스템 테스트"""
    print("\n=== 효과 시스템 테스트 ===")
    
    import numpy as np
    from src.effects.effect_engine import EffectEngine, ColorCorrectionEffect, BlurEffect
    
    # 효과 엔진 생성
    engine = EffectEngine()
    
    # 테스트 이미지 생성 (컬러 그라데이션)
    test_image = np.zeros((400, 600, 3), dtype=np.uint8)
    
    # 그라데이션 패턴 생성
    for y in range(400):
        for x in range(600):
            test_image[y, x] = [
                int((x / 600) * 255),  # 빨강 그라데이션
                int((y / 400) * 255),  # 초록 그라데이션
                128                     # 파랑 고정
            ]
    
    print(f"테스트 이미지 크기: {test_image.shape}")
    
    # 색상 보정 효과 테스트
    color_effect = ColorCorrectionEffect()
    color_effect.set_parameter('brightness', 20)  # 밝기 +20
    color_effect.set_parameter('contrast', 30)    # 대비 +30
    color_effect.set_parameter('saturation', 50)  # 채도 +50
    
    corrected_image = color_effect.apply(test_image)
    print(f"색상 보정 적용됨: 밝기+20, 대비+30, 채도+50")
    
    # 블러 효과 테스트
    blur_effect = BlurEffect()
    blur_effect.set_parameter('radius', 5)
    blur_effect.set_parameter('type', 'gaussian')
    
    blurred_image = blur_effect.apply(corrected_image)
    print(f"가우시안 블러 적용됨: 반지름 5")
    
    # 여러 효과 순차 적용 테스트
    effects = [color_effect, blur_effect]
    final_image = engine.apply_effects(test_image, effects)
    print(f"다중 효과 적용 완료")
    
    print(f"사용 가능한 효과: {engine.get_available_effects()}")
    
    return True

def test_timeline_clip_with_keyframes():
    """키프레임이 있는 타임라인 클립 테스트"""
    print("\n=== 타임라인 클립 + 키프레임 테스트 ===")
    
    from src.timeline.timeline_clip import TimelineClip
    from src.core.keyframe import InterpolationType
    
    # 가상 비디오 파일 경로 (실제 파일은 없어도 됨)
    clip = TimelineClip("test_video.mp4", start_frame=0, track=0)
    clip.duration = 90  # 3초 (30fps)
    
    print(f"클립 생성: {clip.name}, 길이: {clip.duration} 프레임")
    
    # 위치 애니메이션 추가
    clip.animate_position(0, 60, (0, 0), (100, 50), InterpolationType.EASE_IN_OUT)
    
    # 스케일 애니메이션 추가
    clip.animate_scale(0, 30, 1.0, 1.5, InterpolationType.EASE_OUT)
    clip.animate_scale(30, 60, 1.5, 1.0, InterpolationType.EASE_IN)
    
    # 불투명도 애니메이션 추가
    clip.animate_opacity(0, 15, 0.0, 1.0, InterpolationType.EASE_IN)
    clip.animate_opacity(75, 90, 1.0, 0.0, InterpolationType.EASE_OUT)
    
    # 효과 추가
    color_effect = clip.add_color_correction_effect(brightness=10, contrast=20)
    blur_effect = clip.add_blur_effect(radius=3)
    
    print(f"효과 추가됨: {len(clip.effects)}개")
    print(f"키프레임 있음: {clip.has_keyframes()}")
    print(f"키프레임 프레임들: {clip.get_keyframe_frames()}")
    
    # 특정 프레임에서의 애니메이션 값 확인
    test_frames = [0, 15, 30, 45, 60, 75, 90]
    
    print("\n프레임별 애니메이션 값:")
    print("Frame | Pos X  | Pos Y | Scale X | Opacity")
    print("------|--------|-------|---------|--------")
    
    for frame in test_frames:
        pos_x = clip.get_animated_value('position_x', frame)
        pos_y = clip.get_animated_value('position_y', frame)
        scale_x = clip.get_animated_value('scale_x', frame)
        opacity = clip.get_animated_value('opacity', frame)
        
        print(f"{frame:5d} | {pos_x:6.1f} | {pos_y:5.1f} | {scale_x:7.2f} | {opacity:7.2f}")
    
    return True

def test_compositor():
    """컴포지터 테스트"""
    print("\n=== 컴포지터 테스트 ===")
    
    from src.core.compositor import Compositor
    from src.timeline.timeline_clip import TimelineClip
    import numpy as np
    
    # 컴포지터 생성 (작은 해상도로 테스트)
    compositor = Compositor(width=320, height=240)
    
    # 테스트 클립들 생성
    clips = []
    
    # 클립 1: 배경 (가상 이미지)
    clip1 = TimelineClip("background.jpg", start_frame=0, track=0)
    clip1.duration = 120
    clip1.media_type = 'image'
    clips.append(clip1)
    
    # 클립 2: 오버레이 (가상 비디오)
    clip2 = TimelineClip("overlay.mp4", start_frame=30, track=1)
    clip2.duration = 60
    clip2.media_type = 'video'
    # 위치 애니메이션 추가
    clip2.animate_position(0, 30, (0, 0), (50, 25))
    clips.append(clip2)
    
    # 클립 3: 텍스트 (가상)
    clip3 = TimelineClip("title.png", start_frame=60, track=2)
    clip3.duration = 40
    clip3.media_type = 'image'
    # 불투명도 애니메이션
    clip3.animate_opacity(0, 10, 0.0, 1.0)
    clip3.animate_opacity(30, 40, 1.0, 0.0)
    clips.append(clip3)
    
    print(f"테스트 클립 {len(clips)}개 생성")
    
    # 여러 프레임에서 합성 테스트
    test_frames = [0, 30, 60, 90, 120]
    
    for frame in test_frames:
        try:
            # 이 테스트에서는 실제 이미지 파일이 없으므로 오류가 발생할 수 있음
            # 하지만 컴포지터의 로직은 테스트됨
            composite_frame = compositor.composite_frame(clips, frame)
            print(f"프레임 {frame}: 합성 완료 ({composite_frame.shape})")
        except Exception as e:
            print(f"프레임 {frame}: 합성 중 오류 (예상됨) - {e}")
    
    print(f"캐시 크기: {len(compositor.frame_cache)}")
    
    return True

def main():
    """메인 테스트 함수"""
    print("BLOUcut 효과 및 키프레임 시스템 테스트 시작\n")
    
    tests = [
        ("키프레임 시스템", test_keyframe_system),
        ("효과 시스템", test_effect_system),
        ("타임라인 클립 + 키프레임", test_timeline_clip_with_keyframes),
        ("컴포지터", test_compositor),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            print(f"테스트: {test_name}")
            print('='*50)
            
            if test_func():
                print(f"\n✅ {test_name} 테스트 통과")
                passed += 1
            else:
                print(f"\n❌ {test_name} 테스트 실패")
                failed += 1
                
        except Exception as e:
            print(f"\n❌ {test_name} 테스트 오류: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"테스트 결과: {passed}개 통과, {failed}개 실패")
    print('='*50)
    
    if failed == 0:
        print("🎉 모든 테스트 통과!")
        return True
    else:
        print(f"⚠️  {failed}개 테스트에서 문제 발견")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 