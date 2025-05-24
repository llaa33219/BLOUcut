"""
BLOUcut 메인 윈도우
새 프로젝트, 기존 프로젝트 불러오기, 설정 등을 담당
"""

import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLabel, QListWidget, QListWidgetItem, 
                           QFrame, QTextEdit, QGroupBox, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPalette

from .project_window import ProjectWindow

class MainWindow(QMainWindow):
    """메인 윈도우 클래스"""
    
    def __init__(self):
        super().__init__()
        self.project_window = None
        self.init_ui()
        self.load_recent_projects()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("BLOUcut - 전문적인 영상 편집기")
        self.setGeometry(100, 100, 1000, 700)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 왼쪽 패널 - 새 프로젝트 및 설정
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 오른쪽 패널 - 최근 프로젝트
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)
        
        # 스타일 적용
        self.apply_styles()
        
    def create_left_panel(self):
        """왼쪽 패널 생성"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.Box)
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # 로고 및 제목
        title_label = QLabel("BLOUcut")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont("Arial", 24, QFont.Weight.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        subtitle_label = QLabel("전문적인 영상 편집기")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont("Arial", 12)
        subtitle_label.setFont(subtitle_font)
        layout.addWidget(subtitle_label)
        
        layout.addWidget(QLabel())  # 간격
        
        # 새 프로젝트 버튼
        new_project_btn = QPushButton("새 프로젝트")
        new_project_btn.setMinimumHeight(50)
        new_project_btn.clicked.connect(self.create_new_project)
        layout.addWidget(new_project_btn)
        
        # 프로젝트 열기 버튼
        open_project_btn = QPushButton("기존 프로젝트 열기")
        open_project_btn.setMinimumHeight(50)
        open_project_btn.clicked.connect(self.open_existing_project)
        layout.addWidget(open_project_btn)
        
        layout.addWidget(QLabel())  # 간격
        
        # 설정 그룹
        settings_group = QGroupBox("설정")
        settings_layout = QVBoxLayout(settings_group)
        
        # 프로젝트 환경 설정
        project_settings_btn = QPushButton("프로젝트 환경 설정")
        project_settings_btn.clicked.connect(self.open_project_settings)
        settings_layout.addWidget(project_settings_btn)
        
        # 편집기 기본 설정
        editor_settings_btn = QPushButton("편집기 기본 설정")
        editor_settings_btn.clicked.connect(self.open_editor_settings)
        settings_layout.addWidget(editor_settings_btn)
        
        # 버전 정보
        version_btn = QPushButton("버전 정보")
        version_btn.clicked.connect(self.show_version_info)
        settings_layout.addWidget(version_btn)
        
        layout.addWidget(settings_group)
        
        layout.addStretch()
        return panel
        
    def create_right_panel(self):
        """오른쪽 패널 생성"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.Box)
        layout = QVBoxLayout(panel)
        
        # 최근 프로젝트 제목
        recent_title = QLabel("최근 프로젝트")
        recent_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(recent_title)
        
        # 최근 프로젝트 리스트
        self.recent_projects_list = QListWidget()
        self.recent_projects_list.itemDoubleClicked.connect(self.open_recent_project)
        layout.addWidget(self.recent_projects_list)
        
        return panel
        
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 10px;
            }
            
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #45a049;
            }
            
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            
            QLabel {
                color: #333;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #fafafa;
                alternate-background-color: #f0f0f0;
            }
            
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
        """)
        
    def create_new_project(self):
        """새 프로젝트 생성"""
        self.open_project_window()
        
    def open_existing_project(self):
        """기존 프로젝트 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "프로젝트 파일 선택",
            "",
            "BLOUcut 프로젝트 (*.blc);;모든 파일 (*)"
        )
        
        if file_path:
            self.open_project_window(file_path)
            
    def open_recent_project(self, item):
        """최근 프로젝트 열기"""
        project_path = item.data(Qt.ItemDataRole.UserRole)
        if os.path.exists(project_path):
            self.open_project_window(project_path)
        else:
            QMessageBox.warning(self, "파일 없음", f"프로젝트 파일을 찾을 수 없습니다:\n{project_path}")
            
    def open_project_window(self, project_path=None):
        """프로젝트 윈도우 열기"""
        if self.project_window:
            self.project_window.close()
            
        self.project_window = ProjectWindow(project_path)
        self.project_window.show()
        self.hide()  # 메인 윈도우 숨기기
        
    def open_project_settings(self):
        """프로젝트 환경 설정"""
        QMessageBox.information(self, "설정", "프로젝트 환경 설정 기능이 곧 추가될 예정입니다.")
        
    def open_editor_settings(self):
        """편집기 기본 설정"""
        QMessageBox.information(self, "설정", "편집기 기본 설정 기능이 곧 추가될 예정입니다.")
        
    def show_version_info(self):
        """버전 정보 표시"""
        version_info = """
        BLOUcut 영상 편집기
        버전: 1.0.0
        
        개발: BLOUcut Team
        Python 기반 전문적인 영상 편집기
        
        지원하는 기능:
        • AI 기반 편집 도구
        • 고급 영상 편집
        • 멀티트랙 타임라인
        • 다양한 효과 및 필터
        """
        QMessageBox.about(self, "BLOUcut 정보", version_info)
        
    def load_recent_projects(self):
        """최근 프로젝트 불러오기"""
        # 임시로 더미 데이터 추가
        dummy_projects = [
            "내 첫 번째 영상.blc",
            "유튜브 인트로.blc",
            "결혼식 영상.blc"
        ]
        
        for project in dummy_projects:
            item = QListWidgetItem(project)
            item.setData(Qt.ItemDataRole.UserRole, f"~/Documents/BLOUcut/{project}")
            self.recent_projects_list.addItem(item) 