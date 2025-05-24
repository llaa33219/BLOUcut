"""
BLOUcut 키보드 단축키 관리자
전문가용 영상 편집 단축키 시스템
"""

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget, QMessageBox
from typing import Dict, Callable, Optional

class KeyboardShortcutManager(QObject):
    """키보드 단축키 관리자"""
    
    # 시그널
    shortcut_activated = pyqtSignal(str)  # 단축키 이름
    
    def __init__(self, parent_widget: QWidget):
        super().__init__()
        self.parent_widget = parent_widget
        self.shortcuts: Dict[str, QShortcut] = {}
        self.shortcuts_info: Dict[str, Dict] = {}
        
        # 기본 단축키 등록
        self.register_default_shortcuts()
        
    def register_shortcut(self, name: str, key_sequence: str, description: str, 
                         callback: Optional[Callable] = None, category: str = "일반"):
        """단축키 등록"""
        if name in self.shortcuts:
            # 기존 단축키 제거
            self.shortcuts[name].deleteLater()
            
        # 새 단축키 생성
        shortcut = QShortcut(QKeySequence(key_sequence), self.parent_widget)
        
        # 콜백 연결
        if callback:
            shortcut.activated.connect(callback)
        else:
            shortcut.activated.connect(lambda: self.shortcut_activated.emit(name))
            
        # 저장
        self.shortcuts[name] = shortcut
        self.shortcuts_info[name] = {
            'key_sequence': key_sequence,
            'description': description,
            'category': category,
            'callback': callback
        }
        
    def register_default_shortcuts(self):
        """기본 단축키 등록"""
        
        # === 파일 작업 ===
        self.register_shortcut("new_project", "Ctrl+N", "새 프로젝트", category="파일")
        self.register_shortcut("open_project", "Ctrl+O", "프로젝트 열기", category="파일")
        self.register_shortcut("save_project", "Ctrl+S", "프로젝트 저장", category="파일")
        self.register_shortcut("save_as", "Ctrl+Shift+S", "다른 이름으로 저장", category="파일")
        self.register_shortcut("import_media", "Ctrl+I", "미디어 가져오기", category="파일")
        self.register_shortcut("export_video", "Ctrl+E", "비디오 내보내기", category="파일")
        
        # === 편집 작업 ===
        self.register_shortcut("undo", "Ctrl+Z", "실행 취소", category="편집")
        self.register_shortcut("redo", "Ctrl+Y", "다시 실행", category="편집")
        self.register_shortcut("redo_alt", "Ctrl+Shift+Z", "다시 실행 (대체)", category="편집")
        self.register_shortcut("cut", "Ctrl+X", "잘라내기", category="편집")
        self.register_shortcut("copy", "Ctrl+C", "복사", category="편집")
        self.register_shortcut("paste", "Ctrl+V", "붙여넣기", category="편집")
        self.register_shortcut("select_all", "Ctrl+A", "모두 선택", category="편집")
        self.register_shortcut("deselect_all", "Ctrl+D", "선택 해제", category="편집")
        
        # === 재생 제어 ===
        self.register_shortcut("play_pause", "Space", "재생/정지", category="재생")
        self.register_shortcut("play_backward", "J", "역방향 재생", category="재생")
        self.register_shortcut("pause", "K", "정지", category="재생")
        self.register_shortcut("play_forward", "L", "정방향 재생", category="재생")
        self.register_shortcut("frame_backward", "Left", "이전 프레임", category="재생")
        self.register_shortcut("frame_forward", "Right", "다음 프레임", category="재생")
        self.register_shortcut("second_backward", "Shift+Left", "1초 뒤로", category="재생")
        self.register_shortcut("second_forward", "Shift+Right", "1초 앞으로", category="재생")
        self.register_shortcut("5second_backward", "Ctrl+Left", "5초 뒤로", category="재생")
        self.register_shortcut("5second_forward", "Ctrl+Right", "5초 앞으로", category="재생")
        self.register_shortcut("go_to_start", "Home", "시작으로 이동", category="재생")
        self.register_shortcut("go_to_end", "End", "끝으로 이동", category="재생")
        
        # === 인/아웃 포인트 ===
        self.register_shortcut("set_in_point", "I", "인 포인트 설정", category="마크")
        self.register_shortcut("set_out_point", "O", "아웃 포인트 설정", category="마크")
        self.register_shortcut("go_to_in_point", "Shift+I", "인 포인트로 이동", category="마크")
        self.register_shortcut("go_to_out_point", "Shift+O", "아웃 포인트로 이동", category="마크")
        self.register_shortcut("clear_in_point", "Alt+I", "인 포인트 지우기", category="마크")
        self.register_shortcut("clear_out_point", "Alt+O", "아웃 포인트 지우기", category="마크")
        self.register_shortcut("clear_in_out", "Alt+X", "인/아웃 포인트 지우기", category="마크")
        
        # === 타임라인 편집 ===
        self.register_shortcut("split_clip", "S", "클립 분할", category="편집")
        self.register_shortcut("delete_clip", "Delete", "클립 삭제", category="편집")
        self.register_shortcut("delete_clip_alt", "Backspace", "클립 삭제 (대체)", category="편집")
        self.register_shortcut("blade_tool", "B", "블레이드 도구", category="도구")
        self.register_shortcut("selection_tool", "V", "선택 도구", category="도구")
        self.register_shortcut("hand_tool", "H", "핸드 도구", category="도구")
        self.register_shortcut("zoom_tool", "Z", "줌 도구", category="도구")
        
        # === 클립 조작 ===
        self.register_shortcut("group_clips", "Ctrl+G", "클립 그룹화", category="클립")
        self.register_shortcut("ungroup_clips", "Ctrl+U", "그룹 해제", category="클립")
        self.register_shortcut("duplicate_clip", "Ctrl+D", "클립 복제", category="클립")
        self.register_shortcut("trim_clip", "T", "클립 트리밍", category="클립")
        self.register_shortcut("rotate_clip", "R", "클립 회전", category="클립")
        self.register_shortcut("flip_clip", "F", "클립 뒤집기", category="클립")
        self.register_shortcut("scale_to_fit", "Shift+F", "화면에 맞춤", category="클립")
        
        # === 보기 ===
        self.register_shortcut("zoom_in", "Ctrl+=", "확대", category="보기")
        self.register_shortcut("zoom_out", "Ctrl+-", "축소", category="보기")
        self.register_shortcut("zoom_to_fit", "Shift+Z", "전체 보기", category="보기")
        self.register_shortcut("zoom_to_selection", "Shift+S", "선택 영역 확대", category="보기")
        self.register_shortcut("toggle_safe_zone", "Shift+S", "세이프존 토글", category="보기")
        self.register_shortcut("toggle_grid", "Shift+G", "격자 토글", category="보기")
        self.register_shortcut("toggle_rulers", "Ctrl+R", "룰러 토글", category="보기")
        
        # === 속도 조절 ===
        self.register_shortcut("speed_quarter", "Shift+1", "0.25x 속도", category="속도")
        self.register_shortcut("speed_half", "Shift+2", "0.5x 속도", category="속도")
        self.register_shortcut("speed_normal", "Shift+3", "1x 속도", category="속도")
        self.register_shortcut("speed_double", "Shift+4", "2x 속도", category="속도")
        
        # === 오디오 ===
        self.register_shortcut("mute_track", "M", "트랙 음소거", category="오디오")
        self.register_shortcut("solo_track", "Shift+M", "트랙 솔로", category="오디오")
        self.register_shortcut("volume_up", "Ctrl+Up", "볼륨 증가", category="오디오")
        self.register_shortcut("volume_down", "Ctrl+Down", "볼륨 감소", category="오디오")
        
        # === 마커 ===
        self.register_shortcut("add_marker", "M", "마커 추가", category="마커")
        self.register_shortcut("next_marker", "Shift+Right", "다음 마커", category="마커")
        self.register_shortcut("prev_marker", "Shift+Left", "이전 마커", category="마커")
        self.register_shortcut("delete_marker", "Shift+Delete", "마커 삭제", category="마커")
        
        # === 렌더링/내보내기 ===
        self.register_shortcut("render_preview", "Enter", "미리보기 렌더링", category="렌더링")
        self.register_shortcut("clear_cache", "Ctrl+Shift+Delete", "캐시 지우기", category="렌더링")
        
        # === 워크스페이스 ===
        self.register_shortcut("fullscreen", "F11", "전체화면", category="워크스페이스")
        self.register_shortcut("minimize_panels", "Shift+Tab", "패널 최소화", category="워크스페이스")
        self.register_shortcut("reset_workspace", "Alt+0", "워크스페이스 초기화", category="워크스페이스")
        
        # === 도움말 ===
        self.register_shortcut("help", "F1", "도움말", category="도움말")
        self.register_shortcut("shortcuts_help", "Ctrl+/", "단축키 도움말", category="도움말")
        
    def get_shortcut(self, name: str) -> Optional[QShortcut]:
        """단축키 가져오기"""
        return self.shortcuts.get(name)
        
    def get_shortcut_info(self, name: str) -> Optional[Dict]:
        """단축키 정보 가져오기"""
        return self.shortcuts_info.get(name)
        
    def get_shortcuts_by_category(self, category: str) -> Dict[str, Dict]:
        """카테고리별 단축키 목록"""
        return {name: info for name, info in self.shortcuts_info.items() 
                if info['category'] == category}
        
    def get_all_categories(self) -> set:
        """모든 카테고리 목록"""
        return {info['category'] for info in self.shortcuts_info.values()}
        
    def set_shortcut_enabled(self, name: str, enabled: bool):
        """단축키 활성화/비활성화"""
        shortcut = self.get_shortcut(name)
        if shortcut:
            shortcut.setEnabled(enabled)
            
    def remove_shortcut(self, name: str):
        """단축키 제거"""
        if name in self.shortcuts:
            self.shortcuts[name].deleteLater()
            del self.shortcuts[name]
            del self.shortcuts_info[name]
            
    def update_shortcut(self, name: str, new_key_sequence: str):
        """단축키 변경"""
        if name in self.shortcuts:
            info = self.shortcuts_info[name]
            self.register_shortcut(
                name, 
                new_key_sequence, 
                info['description'], 
                info['callback'], 
                info['category']
            )
            
    def export_shortcuts(self) -> Dict:
        """단축키 설정 내보내기"""
        return {name: info['key_sequence'] for name, info in self.shortcuts_info.items()}
        
    def import_shortcuts(self, shortcuts_data: Dict):
        """단축키 설정 가져오기"""
        for name, key_sequence in shortcuts_data.items():
            if name in self.shortcuts_info:
                self.update_shortcut(name, key_sequence)
                
    def show_shortcuts_help(self):
        """단축키 도움말 표시"""
        help_text = "BLOUcut 키보드 단축키\n\n"
        
        categories = sorted(self.get_all_categories())
        for category in categories:
            help_text += f"=== {category} ===\n"
            shortcuts = self.get_shortcuts_by_category(category)
            
            for name, info in sorted(shortcuts.items(), key=lambda x: x[1]['description']):
                key_seq = info['key_sequence']
                desc = info['description']
                help_text += f"{key_seq:<20} {desc}\n"
            help_text += "\n"
            
        # 도움말 다이얼로그 표시
        msg_box = QMessageBox(self.parent_widget)
        msg_box.setWindowTitle("키보드 단축키")
        msg_box.setText(help_text)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10pt;
            }
        """)
        msg_box.exec()
        
    def get_conflict_shortcuts(self, key_sequence: str) -> list:
        """충돌하는 단축키 찾기"""
        conflicts = []
        for name, info in self.shortcuts_info.items():
            if info['key_sequence'] == key_sequence:
                conflicts.append(name)
        return conflicts 