"""
BLOUcut 효과 패널
다양한 효과 및 필터 관리
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QListWidget, QListWidgetItem, QLabel, QLineEdit,
                           QComboBox, QFrame, QTabWidget, QScrollArea,
                           QGridLayout, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon

class EffectsPanel(QWidget):
    """효과 패널"""
    
    # 시그널
    effect_applied = pyqtSignal(str, dict)  # 효과 이름, 파라미터
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 검색 입력
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("효과 검색...")
        self.search_input.textChanged.connect(self.filter_effects)
        layout.addWidget(self.search_input)
        
        # 효과 탭
        self.effects_tabs = QTabWidget()
        
        # 전환 효과 탭
        self.transitions_tab = self.create_transitions_tab()
        self.effects_tabs.addTab(self.transitions_tab, "전환")
        
        # 텍스트 효과 탭
        self.text_tab = self.create_text_tab()
        self.effects_tabs.addTab(self.text_tab, "텍스트")
        
        # 필터 효과 탭
        self.filters_tab = self.create_filters_tab()
        self.effects_tabs.addTab(self.filters_tab, "필터")
        
        # 색상 보정 탭
        self.color_tab = self.create_color_tab()
        self.effects_tabs.addTab(self.color_tab, "색상")
        
        # 스티커 탭
        self.stickers_tab = self.create_stickers_tab()
        self.effects_tabs.addTab(self.stickers_tab, "스티커")
        
        layout.addWidget(self.effects_tabs)
        
        self.apply_styles()
        
    def create_transitions_tab(self):
        """전환 효과 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 전환 효과 목록
        transitions = [
            {"name": "페이드 인", "description": "부드럽게 나타남", "duration": "1.0초"},
            {"name": "페이드 아웃", "description": "부드럽게 사라짐", "duration": "1.0초"},
            {"name": "슬라이드 좌측", "description": "왼쪽에서 등장", "duration": "0.5초"},
            {"name": "슬라이드 우측", "description": "오른쪽에서 등장", "duration": "0.5초"},
            {"name": "줌 인", "description": "확대되며 등장", "duration": "0.8초"},
            {"name": "줌 아웃", "description": "축소되며 등장", "duration": "0.8초"},
            {"name": "디졸브", "description": "녹아들며 전환", "duration": "1.5초"},
        ]
        
        for transition in transitions:
            effect_widget = EffectItemWidget(transition, "transition")
            effect_widget.applied.connect(self.on_effect_applied)
            layout.addWidget(effect_widget)
            
        layout.addStretch()
        return widget
        
    def create_text_tab(self):
        """텍스트 효과 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 텍스트 효과 목록
        text_effects = [
            {"name": "기본 텍스트", "description": "단순한 텍스트", "properties": ["글꼴", "크기", "색상"]},
            {"name": "애니메이션 텍스트", "description": "움직이는 텍스트", "properties": ["타이프라이터", "페이드인", "슬라이드업"]},
            {"name": "타이틀 카드", "description": "제목+부제목", "properties": ["제목", "부제목", "배경"]},
            {"name": "하단 자막", "description": "이름/직책 표시", "properties": ["이름", "직책", "위치"]},
            {"name": "외곽선 텍스트", "description": "테두리가 있는 텍스트", "properties": ["외곽선", "두께", "색상"]},
            {"name": "그림자 텍스트", "description": "그림자 효과", "properties": ["그림자", "거리", "투명도"]},
        ]
        
        for effect in text_effects:
            effect_widget = EffectItemWidget(effect, "text")
            effect_widget.applied.connect(self.on_effect_applied)
            layout.addWidget(effect_widget)
            
        layout.addStretch()
        return widget
        
    def create_filters_tab(self):
        """필터 효과 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 필터 효과 목록
        filters = [
            {"name": "블러", "description": "이미지를 흐리게", "types": ["가우시안", "모션", "래디얼"]},
            {"name": "샤픈", "description": "이미지를 선명하게", "intensity": "조절 가능"},
            {"name": "빈티지", "description": "옛날 느낌", "effects": ["세피아", "비네팅", "노이즈"]},
            {"name": "흑백", "description": "흑백 필터", "styles": ["클래식", "고대비"]},
            {"name": "카툰", "description": "만화 스타일", "effects": ["엣지 감지", "색상 감소"]},
            {"name": "글로우", "description": "빛나는 효과", "properties": ["강도", "색상", "크기"]},
        ]
        
        for filter_effect in filters:
            effect_widget = EffectItemWidget(filter_effect, "filter")
            effect_widget.applied.connect(self.on_effect_applied)
            layout.addWidget(effect_widget)
            
        layout.addStretch()
        return widget
        
    def create_color_tab(self):
        """색상 보정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 색상 보정 목록
        color_effects = [
            {"name": "밝기/대비", "description": "밝기와 대비 조절", "range": "-100 ~ +100"},
            {"name": "색조/채도", "description": "색상과 채도 조절", "properties": ["색조", "채도", "명도"]},
            {"name": "색상 균형", "description": "RGB 균형 조절", "controls": ["시안-빨강", "마젠타-초록", "노랑-파랑"]},
            {"name": "색온도", "description": "색온도와 틴트", "range": "2000K ~ 10000K"},
            {"name": "RGB 커브", "description": "정밀 색상 조절", "channels": ["RGB", "빨강", "초록", "파랑"]},
            {"name": "LUT 적용", "description": "룩업 테이블", "formats": [".cube", ".3dl", ".lut"]},
        ]
        
        for effect in color_effects:
            effect_widget = EffectItemWidget(effect, "color")
            effect_widget.applied.connect(self.on_effect_applied)
            layout.addWidget(effect_widget)
            
        layout.addStretch()
        return widget
        
    def create_stickers_tab(self):
        """스티커 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 스티커 목록
        stickers = [
            {"name": "하트 이모지", "description": "하트 모양", "sizes": ["작음", "보통", "큼"]},
            {"name": "화살표", "description": "방향 표시", "styles": ["직선", "곡선", "점선"]},
            {"name": "말풍선", "description": "텍스트 포함", "shapes": ["원형", "사각형", "생각"]},
            {"name": "별", "description": "별 모양", "types": ["5각별", "6각별", "반짝이"]},
            {"name": "도형", "description": "기본 도형", "shapes": ["원", "사각형", "삼각형"]},
            {"name": "프레임", "description": "테두리 프레임", "styles": ["클래식", "모던", "빈티지"]},
        ]
        
        for sticker in stickers:
            effect_widget = EffectItemWidget(sticker, "sticker")
            effect_widget.applied.connect(self.on_effect_applied)
            layout.addWidget(effect_widget)
            
        layout.addStretch()
        return widget
        
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QWidget {
                background-color: #3c3c3c;
                color: white;
            }
            
            QLineEdit {
                background-color: #555;
                border: 1px solid #777;
                border-radius: 3px;
                padding: 5px;
            }
            
            QLineEdit:focus {
                border-color: #4CAF50;
            }
            
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #3c3c3c;
            }
            
            QTabBar::tab {
                background-color: #555;
                color: white;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            
            QTabBar::tab:hover {
                background-color: #666;
            }
        """)
        
    def filter_effects(self):
        """효과 필터링"""
        search_text = self.search_input.text().lower()
        
        # 현재 탭의 모든 효과 위젯을 검색
        current_widget = self.effects_tabs.currentWidget()
        if current_widget:
            for i in range(current_widget.layout().count()):
                item = current_widget.layout().itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if hasattr(widget, 'effect_name'):
                        visible = search_text in widget.effect_name.lower()
                        widget.setVisible(visible)
                        
    def on_effect_applied(self, effect_name, effect_type, parameters):
        """효과 적용 이벤트"""
        self.effect_applied.emit(effect_name, {
            'type': effect_type,
            'parameters': parameters
        })

class EffectItemWidget(QWidget):
    """효과 아이템 위젯"""
    
    applied = pyqtSignal(str, str, dict)  # 효과 이름, 타입, 파라미터
    
    def __init__(self, effect_data, effect_type):
        super().__init__()
        self.effect_data = effect_data
        self.effect_type = effect_type
        self.effect_name = effect_data['name']
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # 효과 아이콘/썸네일
        icon_label = QLabel()
        icon_label.setFixedSize(40, 40)
        icon_label.setStyleSheet("""
            background-color: #555;
            border: 1px solid #777;
            border-radius: 5px;
            color: white;
        """)
        
        # 효과 타입에 따른 아이콘
        icon_text = {
            'transition': '🔄',
            'text': '📝',
            'filter': '🎨',
            'color': '🌈',
            'sticker': '🏷️'
        }.get(self.effect_type, '⭐')
        
        icon_label.setText(icon_text)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # 효과 정보
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # 효과 이름
        name_label = QLabel(self.effect_data['name'])
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_label.setStyleSheet("border: none; background: transparent;")
        info_layout.addWidget(name_label)
        
        # 효과 설명
        desc_label = QLabel(self.effect_data.get('description', ''))
        desc_label.setFont(QFont("Arial", 8))
        desc_label.setStyleSheet("color: #aaa; border: none; background: transparent;")
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout, 1)
        
        # 적용 버튼
        apply_button = QPushButton("적용")
        apply_button.setMaximumWidth(50)
        apply_button.clicked.connect(self.apply_effect)
        layout.addWidget(apply_button)
        
        # 설정 버튼 (파라미터가 있는 경우)
        if self.has_parameters():
            settings_button = QPushButton("⚙")
            settings_button.setMaximumWidth(30)
            settings_button.clicked.connect(self.show_settings)
            layout.addWidget(settings_button)
        
        self.setMaximumHeight(60)
        self.apply_styles()
        
    def has_parameters(self):
        """파라미터가 있는 효과인지 확인"""
        return any(key in self.effect_data for key in ['properties', 'controls', 'parameters', 'range'])
        
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            EffectItemWidget {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 5px;
                margin: 2px;
            }
            
            EffectItemWidget:hover {
                background-color: #444;
                border-color: #777;
            }
            
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #45a049;
            }
            
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
    def apply_effect(self):
        """효과 적용"""
        # 기본 파라미터
        parameters = self.get_default_parameters()
        
        self.applied.emit(self.effect_name, self.effect_type, parameters)
        
    def get_default_parameters(self):
        """기본 파라미터 가져오기"""
        default_params = {}
        
        if self.effect_type == 'transition':
            default_params = {
                'duration': 1.0,
                'easing': 'ease-in-out'
            }
        elif self.effect_type == 'text':
            default_params = {
                'font_family': 'Arial',
                'font_size': 24,
                'color': '#FFFFFF',
                'position': 'center'
            }
        elif self.effect_type == 'filter':
            default_params = {
                'intensity': 0.5,
                'blend_mode': 'normal'
            }
        elif self.effect_type == 'color':
            default_params = {
                'brightness': 0,
                'contrast': 0,
                'saturation': 0,
                'hue': 0
            }
        elif self.effect_type == 'sticker':
            default_params = {
                'size': 1.0,
                'position': [0.5, 0.5],
                'rotation': 0,
                'opacity': 1.0
            }
            
        return default_params
        
    def show_settings(self):
        """설정 다이얼로그 표시"""
        # TODO: 효과별 상세 설정 다이얼로그 구현
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "설정", f"{self.effect_name} 설정 기능이 곧 추가될 예정입니다.") 