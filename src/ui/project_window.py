"""
BLOUcut 프로젝트 윈도우
영상 편집의 메인 인터페이스
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QSplitter, QTabWidget, QMenuBar, QMenu, QStatusBar, 
                           QLabel, QFrame, QPushButton, QSlider, QSpinBox, 
                           QGroupBox, QListWidget, QTextEdit, QProgressBar,
                           QToolBar, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QFont

from ..timeline.timeline_widget import TimelineWidget
from ..ui.preview_widget import PreviewWidget
from ..ui.media_panel import MediaPanel
from ..ui.effects_panel import EffectsPanel
from ..ui.properties_panel import PropertiesPanel
from ..ui.export_dialog import ExportDialog
from ..core.keyboard_shortcuts import KeyboardShortcutManager
from ..core.auto_save_manager import AutoSaveManager
from ..core.project_manager import ProjectManager

class ProjectWindow(QMainWindow):
    """프로젝트 편집 윈도우"""
    
    def __init__(self, project_path=None):
        super().__init__()
        self.project_path = project_path
        
        # 프로젝트 관리자 초기화
        self.project_manager = ProjectManager()
        
        self.init_ui()
        self.create_menus()
        self.create_toolbar()
        self.create_status_bar()
        
        # 프로젝트 로드
        if project_path:
            self.load_project(project_path)
        else:
            self.new_project()
            
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("BLOUcut - 새 프로젝트")
        self.setGeometry(50, 50, 1400, 800)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 상단 스플리터 (프리뷰 + 패널들)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 왼쪽 패널 (미디어, 효과 등)
        left_tabs = QTabWidget()
        left_tabs.setMaximumWidth(300)
        left_tabs.setMinimumWidth(250)
        
        # 미디어 패널
        self.media_panel = MediaPanel()
        left_tabs.addTab(self.media_panel, "미디어")
        
        # 효과 패널
        self.effects_panel = EffectsPanel()
        left_tabs.addTab(self.effects_panel, "효과")
        
        top_splitter.addWidget(left_tabs)
        
        # 중앙 프리뷰 화면
        self.preview_widget = PreviewWidget()
        top_splitter.addWidget(self.preview_widget)
        
        # 오른쪽 속성 패널
        self.properties_panel = PropertiesPanel()
        self.properties_panel.setMaximumWidth(300)
        self.properties_panel.setMinimumWidth(250)
        top_splitter.addWidget(self.properties_panel)
        
        # 스플리터 비율 설정
        top_splitter.setSizes([250, 600, 250])
        
        main_layout.addWidget(top_splitter, 2)
        
        # 타임라인 영역 (컨트롤 + 타임라인)
        timeline_layout = QVBoxLayout()
        timeline_frame = QFrame()
        timeline_frame.setLayout(timeline_layout)
        
        # 타임라인 컨트롤 바
        timeline_controls = self.create_timeline_controls()
        timeline_layout.addLayout(timeline_controls)
        
        # 타임라인 위젯
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.setMinimumHeight(200)
        timeline_layout.addWidget(self.timeline_widget, 1)
        
        main_layout.addWidget(timeline_frame, 1)
        
        # 스타일 적용
        self.apply_styles()
        
        # 시그널 연결
        self.connect_signals()
        
        # 명령 관리자 연결
        self.setup_command_manager()
        
        # 키보드 단축키 설정
        self.setup_keyboard_shortcuts()
        
        # 자동 저장 관리자 설정
        self.setup_auto_save()
        
        # 초기 줌 표시 업데이트
        self.update_zoom_display()
        
    def create_timeline_controls(self):
        """타임라인 컨트롤 바 생성"""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 줌 컨트롤
        layout.addWidget(QLabel("줌:"))
        
        # 줌 아웃 버튼
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setMaximumWidth(30)
        zoom_out_btn.clicked.connect(self.zoom_out)
        layout.addWidget(zoom_out_btn)
        
        # 줌 슬라이더
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(1, 10000)  # 매우 넓은 범위 (로그 스케일)
        self.zoom_slider.setValue(1000)  # 1.0x
        self.zoom_slider.setMaximumWidth(150)
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        layout.addWidget(self.zoom_slider)
        
        # 줌 인 버튼
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setMaximumWidth(30)
        zoom_in_btn.clicked.connect(self.zoom_in)
        layout.addWidget(zoom_in_btn)
        
        # 줌 레벨 표시
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        layout.addWidget(self.zoom_label)
        
        layout.addWidget(QFrame())  # 구분선
        
        # 스냅 토글
        self.snap_button = QPushButton("🧲 스냅")
        self.snap_button.setCheckable(True)
        self.snap_button.setChecked(True)
        self.snap_button.toggled.connect(self.toggle_snap)
        layout.addWidget(self.snap_button)
        
        # 핸드 툴
        self.hand_tool_button = QPushButton("✋ 핸드툴")
        self.hand_tool_button.setCheckable(True)
        self.hand_tool_button.toggled.connect(self.toggle_hand_tool)
        layout.addWidget(self.hand_tool_button)
        
        layout.addWidget(QFrame())  # 구분선
        
        # 트랙 관리
        layout.addWidget(QLabel("트랙:"))
        
        add_track_btn = QPushButton("+ 추가")
        add_track_btn.clicked.connect(self.add_track)
        layout.addWidget(add_track_btn)
        
        remove_track_btn = QPushButton("− 제거")
        remove_track_btn.clicked.connect(self.remove_track)
        layout.addWidget(remove_track_btn)
        
        # 트랙 수 표시
        self.track_count_label = QLabel("3개")
        layout.addWidget(self.track_count_label)
        
        layout.addWidget(QFrame())  # 구분선
        
        # 줌 맞춤 버튼들
        fit_all_btn = QPushButton("전체보기")
        fit_all_btn.setToolTip("모든 클립이 보이도록 줌 조정 (Ctrl+F)")
        fit_all_btn.clicked.connect(self.fit_all_clips)
        layout.addWidget(fit_all_btn)
        
        fit_selection_btn = QPushButton("선택맞춤")
        fit_selection_btn.setToolTip("선택된 클립들에 맞춰 줌 조정 (Alt+F)")
        fit_selection_btn.clicked.connect(self.fit_selected_clips)
        layout.addWidget(fit_selection_btn)
        
        reset_zoom_btn = QPushButton("100%")
        reset_zoom_btn.setToolTip("기본 줌 레벨로 복원 (Ctrl+0)")
        reset_zoom_btn.clicked.connect(self.reset_zoom)
        layout.addWidget(reset_zoom_btn)
        
        layout.addStretch()
        
        # 타임라인 정보
        self.timeline_info_label = QLabel("타임라인: 00:00 ~ 00:30")
        layout.addWidget(self.timeline_info_label)
        
        return layout
        
    def create_menus(self):
        """메뉴 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일(&F)")
        
        new_action = QAction("새 프로젝트(&N)", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("열기(&O)", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("저장(&S)", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("다른 이름으로 저장(&A)", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("미디어 가져오기(&I)", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self.import_media)
        file_menu.addAction(import_action)
        
        export_action = QAction("내보내기(&E)", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_video)
        file_menu.addAction(export_action)
        
        # 편집 메뉴
        edit_menu = menubar.addMenu("편집(&E)")
        
        undo_action = QAction("실행 취소(&U)", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("다시 실행(&R)", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("잘라내기(&X)", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("복사(&C)", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("붙여넣기(&V)", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.paste)
        edit_menu.addAction(paste_action)
        
        # 보기 메뉴
        view_menu = menubar.addMenu("보기(&V)")
        
        zoom_in_action = QAction("확대(&I)", self)
        zoom_in_action.setShortcut(QKeySequence("Ctrl+="))
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("축소(&O)", self)
        zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        view_menu.addSeparator()
        
        fit_all_action = QAction("전체 보기(&A)", self)
        fit_all_action.setShortcut(QKeySequence("Ctrl+F"))
        fit_all_action.triggered.connect(self.fit_all_clips)
        view_menu.addAction(fit_all_action)
        
        fit_selection_action = QAction("선택 클립에 맞춤(&S)", self)
        fit_selection_action.setShortcut(QKeySequence("Alt+F"))
        fit_selection_action.triggered.connect(self.fit_selected_clips)
        view_menu.addAction(fit_selection_action)
        
        reset_zoom_action = QAction("기본 줌(&R)", self)
        reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말(&H)")
        
        shortcuts_action = QAction("키보드 단축키(&K)", self)
        shortcuts_action.setShortcut(QKeySequence("Ctrl+/"))
        shortcuts_action.triggered.connect(self.show_shortcuts_help)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("BLOUcut 정보(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        """툴바 생성"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 새 프로젝트
        new_action = QAction("새 프로젝트", self)
        new_action.triggered.connect(self.new_project)
        toolbar.addAction(new_action)
        
        # 열기
        open_action = QAction("열기", self)
        open_action.triggered.connect(self.open_project)
        toolbar.addAction(open_action)
        
        # 저장
        save_action = QAction("저장", self)
        save_action.triggered.connect(self.save_project)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # 실행 취소/다시 실행
        undo_action = QAction("실행 취소", self)
        undo_action.triggered.connect(self.undo)
        toolbar.addAction(undo_action)
        
        redo_action = QAction("다시 실행", self)
        redo_action.triggered.connect(self.redo)
        toolbar.addAction(redo_action)
        
        toolbar.addSeparator()
        
        # 미디어 가져오기
        import_action = QAction("미디어 가져오기", self)
        import_action.triggered.connect(self.import_media)
        toolbar.addAction(import_action)
        
    def create_status_bar(self):
        """상태 바 생성"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # 현재 시간 표시
        self.time_label = QLabel("00:00:00:00")
        status_bar.addWidget(self.time_label)
        
        # 상태 레이블
        self.status_label = QLabel("준비")
        status_bar.addPermanentWidget(self.status_label)
        
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #3c3c3c;
            }
            
            QTabWidget::tab-bar {
                alignment: left;
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
            
            QSplitter::handle {
                background-color: #555;
            }
            
            QSplitter::handle:horizontal {
                width: 3px;
            }
            
            QSplitter::handle:vertical {
                height: 3px;
            }
            
            QMenuBar {
                background-color: #3c3c3c;
                color: white;
                border-bottom: 1px solid #555;
            }
            
            QMenuBar::item {
                padding: 4px 8px;
            }
            
            QMenuBar::item:selected {
                background-color: #4CAF50;
            }
            
            QMenu {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
            }
            
            QMenu::item {
                padding: 4px 20px;
            }
            
            QMenu::item:selected {
                background-color: #4CAF50;
            }
            
            QToolBar {
                background-color: #3c3c3c;
                border: none;
                spacing: 3px;
            }
            
            QToolBar::separator {
                background-color: #555;
                width: 1px;
                margin: 0 5px;
            }
            
            QStatusBar {
                background-color: #3c3c3c;
                color: white;
                border-top: 1px solid #555;
            }
        """)
        
    def connect_signals(self):
        """시그널 연결"""
        # 타임라인과 프리뷰 연결
        self.timeline_widget.playhead_changed.connect(self.update_preview)
        self.preview_widget.frame_changed.connect(self.timeline_widget.set_playhead_position)
        
        # 미디어 패널과 타임라인 연결
        self.media_panel.media_dropped.connect(self.timeline_widget.add_clip)
        self.media_panel.media_selected.connect(self.preview_single_media)
        
        # 타임라인 선택 변경과 속성 패널 연결
        self.timeline_widget.selection_changed.connect(self.properties_panel.update_properties)
        self.timeline_widget.clip_moved.connect(self.on_timeline_changed)
        
    def setup_command_manager(self):
        """명령 관리자 설정"""
        # 타임라인의 명령 관리자 가져오기
        cmd_manager = self.timeline_widget.command_manager
        
        # 실행 취소/다시 실행 버튼 상태 업데이트
        cmd_manager.can_undo_changed.connect(self.update_undo_button)
        cmd_manager.can_redo_changed.connect(self.update_redo_button)
        
    def update_undo_button(self, can_undo):
        """실행 취소 버튼 상태 업데이트"""
        # 메뉴와 툴바의 실행 취소 액션 찾기
        for action in self.menuBar().findChildren(QAction):
            if "실행 취소" in action.text():
                action.setEnabled(can_undo)
                # 툴팁에 명령 설명 추가
                if can_undo:
                    desc = self.timeline_widget.command_manager.get_undo_description()
                    action.setToolTip(f"실행 취소: {desc}")
                else:
                    action.setToolTip("실행 취소")
                    
    def update_redo_button(self, can_redo):
        """다시 실행 버튼 상태 업데이트"""
        # 메뉴와 툴바의 다시 실행 액션 찾기
        for action in self.menuBar().findChildren(QAction):
            if "다시 실행" in action.text():
                action.setEnabled(can_redo)
                # 툴팁에 명령 설명 추가
                if can_redo:
                    desc = self.timeline_widget.command_manager.get_redo_description()
                    action.setToolTip(f"다시 실행: {desc}")
                else:
                    action.setToolTip("다시 실행")
                    
    def setup_keyboard_shortcuts(self):
        """키보드 단축키 설정"""
        self.shortcut_manager = KeyboardShortcutManager(self)
        
        # 단축키와 함수 연결
        self.shortcut_manager.shortcut_activated.connect(self.handle_shortcut)
        
        # 직접 콜백 등록 (기존 메뉴 시스템과 연동)
        shortcuts_map = {
            "new_project": self.new_project,
            "open_project": self.open_project,
            "save_project": self.save_project,
            "save_as": self.save_project_as,
            "import_media": self.import_media,
            "export_video": self.export_video,
            "undo": self.undo,
            "redo": self.redo,
            "cut": self.cut,
            "copy": self.copy,
            "paste": self.paste,
            "zoom_in": self.zoom_in,
            "zoom_out": self.zoom_out,
            "shortcuts_help": self.show_shortcuts_help,
            "help": self.show_about
        }
        
        # 콜백 재등록
        for shortcut_name, callback in shortcuts_map.items():
            info = self.shortcut_manager.get_shortcut_info(shortcut_name)
            if info:
                self.shortcut_manager.register_shortcut(
                    shortcut_name,
                    info['key_sequence'],
                    info['description'],
                    callback,
                    info['category']
                )
                
    def handle_shortcut(self, shortcut_name: str):
        """단축키 처리"""
        # 타임라인 관련 단축키는 타임라인에서 처리
        timeline_shortcuts = [
            "play_pause", "split_clip", "delete_clip", "delete_clip_alt",
            "frame_backward", "frame_forward", "second_backward", "second_forward",
            "5second_backward", "5second_forward", "go_to_start", "go_to_end",
            "group_clips", "ungroup_clips", "duplicate_clip", "select_all", "deselect_all"
        ]
        
        if shortcut_name in timeline_shortcuts:
            # 타임라인에 키 이벤트 전달
            self.timeline_widget.setFocus()
            return
            
        # 미리보기 관련 단축키
        preview_shortcuts = [
            "set_in_point", "set_out_point", "go_to_in_point", "go_to_out_point",
            "clear_in_point", "clear_out_point", "clear_in_out", "toggle_safe_zone",
            "toggle_grid", "speed_quarter", "speed_half", "speed_normal", "speed_double",
            "play_backward", "pause", "play_forward"
        ]
        
        if shortcut_name in preview_shortcuts:
            # 미리보기 위젯에 전달
            self.preview_widget.setFocus()
            return
        
    def new_project(self):
        """새 프로젝트"""
        self.setWindowTitle("BLOUcut - 새 프로젝트")
        self.project_path = None
        
        # 프로젝트 매니저에서 새 프로젝트 생성
        self.project_manager.new_project()
        
        # 타임라인 초기화
        self.timeline_widget.clear()
        # 미디어 패널 초기화
        self.media_panel.clear()
        
    def open_project(self):
        """프로젝트 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "프로젝트 파일 열기",
            "",
            "BLOUcut 프로젝트 (*.blc);;모든 파일 (*)"
        )
        
        if file_path:
            self.load_project(file_path)
            
    def load_project(self, file_path):
        """프로젝트 로드"""
        self.project_path = file_path
        project_name = file_path.split('/')[-1]
        self.setWindowTitle(f"BLOUcut - {project_name}")
        # TODO: 실제 프로젝트 로드 구현
        
    def save_project(self):
        """프로젝트 저장"""
        if self.project_path:
            # TODO: 실제 저장 구현
            QMessageBox.information(self, "저장", "프로젝트가 저장되었습니다.")
        else:
            self.save_project_as()
            
    def save_project_as(self):
        """다른 이름으로 저장"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "프로젝트 저장",
            "",
            "BLOUcut 프로젝트 (*.blc)"
        )
        
        if file_path:
            self.project_path = file_path
            self.save_project()
            
    def import_media(self):
        """미디어 가져오기"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "미디어 파일 선택",
            "",
            "비디오 파일 (*.mp4 *.avi *.mov *.mkv);;오디오 파일 (*.mp3 *.wav *.aac);;이미지 파일 (*.jpg *.png *.bmp);;모든 파일 (*)"
        )
        
        for file_path in file_paths:
            self.media_panel.add_media(file_path)
            
    def export_video(self):
        """영상 내보내기"""
        export_dialog = ExportDialog(self.timeline_widget, self)
        export_dialog.exec()
        
    def undo(self):
        """실행 취소"""
        self.timeline_widget.command_manager.undo()
        
    def redo(self):
        """다시 실행"""
        self.timeline_widget.command_manager.redo()
        
    def cut(self):
        """잘라내기"""
        # TODO: 잘라내기 구현
        pass
        
    def copy(self):
        """복사"""
        # TODO: 복사 구현
        pass
        
    def paste(self):
        """붙여넣기"""
        # TODO: 붙여넣기 구현
        pass
        
    def zoom_in(self):
        """확대"""
        self.timeline_widget.zoom_in()
        self.update_zoom_display()
        
    def zoom_out(self):
        """축소"""
        self.timeline_widget.zoom_out()
        self.update_zoom_display()
        
    def on_zoom_slider_changed(self, value):
        """줌 슬라이더 변경"""
        # 로그 스케일 변환: 1~10000 -> 무제한 범위
        import math
        
        # 1000이 1.0x (100%)가 되도록 설정
        if value == 1000:
            zoom_level = 1.0
        elif value < 1000:
            # 1~999 -> 매우 작은 값~1.0 (로그 스케일)
            log_ratio = (value - 1) / 999.0  # 0~1
            zoom_level = 10 ** (log_ratio * 2 - 4)  # 0.0001 ~ 1.0
        else:
            # 1001~10000 -> 1.0~매우 큰 값 (로그 스케일)
            log_ratio = (value - 1000) / 9000.0  # 0~1
            zoom_level = 10 ** (log_ratio * 4)  # 1.0 ~ 10000
            
        self.timeline_widget.zoom_level = zoom_level
        self.timeline_widget.update()
        self.update_zoom_display()
        
    def update_zoom_display(self):
        """줌 레벨 표시 업데이트"""
        zoom_level = self.timeline_widget.zoom_level
        
        # 줌 레벨을 슬라이더 값으로 변환 (역변환)
        import math
        
        if zoom_level == 1.0:
            slider_value = 1000
        elif zoom_level < 1.0:
            # 매우 작은 값~1.0 -> 1~999
            if zoom_level > 0:
                log_val = (math.log10(zoom_level) + 4) / 2  # 0~1
                slider_value = int(1 + log_val * 999)
            else:
                slider_value = 1
        else:
            # 1.0~매우 큰 값 -> 1001~10000
            log_val = math.log10(zoom_level) / 4  # 0~1
            slider_value = int(1000 + log_val * 9000)
            
        # 슬라이더 범위 제한
        slider_value = max(1, min(10000, slider_value))
            
        # 퍼센트 표시 (더 넓은 범위)
        if zoom_level < 0.01:
            zoom_text = f"{zoom_level*100:.3f}%"
        elif zoom_level < 0.1:
            zoom_text = f"{zoom_level*100:.2f}%"
        elif zoom_level < 1:
            zoom_text = f"{zoom_level*100:.1f}%"
        elif zoom_level < 100:
            zoom_text = f"{int(zoom_level*100)}%"
        else:
            zoom_text = f"{zoom_level*100:.0f}%"
            
        self.zoom_label.setText(zoom_text)
        self.zoom_slider.setValue(slider_value)
        
    def toggle_snap(self, checked):
        """스냅 기능 토글"""
        self.timeline_widget.toggle_snap()
        self.snap_button.setText("🧲 스냅" if checked else "스냅")
        
    def toggle_hand_tool(self, checked):
        """핸드 툴 토글"""
        self.timeline_widget.toggle_hand_tool()
        self.hand_tool_button.setText("✋ 핸드툴" if checked else "핸드툴")
        
    def add_track(self):
        """트랙 추가"""
        self.timeline_widget.add_track()
        self.update_track_count_display()
        
    def remove_track(self):
        """트랙 제거"""
        self.timeline_widget.remove_track()
        self.update_track_count_display()
        
    def update_track_count_display(self):
        """트랙 수 표시 업데이트"""
        count = self.timeline_widget.track_count
        self.track_count_label.setText(f"{count}개")
        
    def fit_all_clips(self):
        """모든 클립에 맞춰 줌 조정"""
        self.timeline_widget.zoom_to_fit_all()
        self.update_zoom_display()
        
    def fit_selected_clips(self):
        """선택된 클립들에 맞춰 줌 조정"""
        self.timeline_widget.zoom_to_fit_selection()
        self.update_zoom_display()
        
    def reset_zoom(self):
        """기본 줌 레벨로 복원"""
        self.timeline_widget.zoom_level = 1.0
        self.timeline_widget.timeline_offset_x = 0
        self.timeline_widget.update()
        self.update_zoom_display()
        
    def show_shortcuts_help(self):
        """키보드 단축키 도움말"""
        self.shortcut_manager.show_shortcuts_help()
        
    def show_about(self):
        """정보 표시"""
        QMessageBox.about(self, "BLOUcut 정보", "BLOUcut 전문적인 영상 편집기\n버전 1.0.0")
        
    def setup_auto_save(self):
        """자동 저장 관리자 설정"""
        # 프로젝트 매니저와 타임라인 연결
        self.project_manager.set_timeline_widget(self.timeline_widget)
        
        # 자동 저장 관리자 초기화
        self.auto_save_manager = AutoSaveManager(self.project_manager, save_interval=300)  # 5분
        
        # 자동 저장 시그널 연결
        self.auto_save_manager.auto_saved.connect(self.on_auto_saved)
        self.auto_save_manager.recovery_available.connect(self.on_recovery_available)
        
        # 자동 저장 시작
        self.auto_save_manager.start_auto_save()
        
    def on_auto_saved(self, file_path: str):
        """자동 저장 완료 알림"""
        self.status_label.setText(f"자동 저장됨: {file_path}")
        
    def on_recovery_available(self, recovery_files: list):
        """복구 파일 사용 가능 알림"""
        if recovery_files:
            reply = QMessageBox.question(
                self, "복구 파일 발견",
                f"{len(recovery_files)}개의 복구 파일을 발견했습니다. 복구하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 가장 최신 복구 파일 사용
                latest_recovery = recovery_files[0]
                # TODO: 복구 로직 구현
                self.status_label.setText("프로젝트가 복구되었습니다.")
        
    def update_time_display(self, frame_number):
        """시간 표시 업데이트"""
        # 30fps 기준으로 계산
        fps = 30
        total_seconds = frame_number / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frames = frame_number % fps
        
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
        self.time_label.setText(time_str)
        
    def update_preview(self, frame_position):
        """프리뷰 화면 업데이트"""
        # 타임라인 클립들을 프리뷰에 전달
        self.preview_widget.set_timeline_clips(self.timeline_widget.clips)
        # 해당 프레임 위치 렌더링
        self.preview_widget.render_frame_at_position(frame_position)
        
    def preview_single_media(self, media_path):
        """단일 미디어 파일 미리보기 (미디어 패널에서 선택시)"""
        try:
            self.preview_widget.load_media(media_path)
        except Exception as e:
            print(f"미디어 미리보기 실패: {e}")
            
    def on_timeline_changed(self, clip, start_frame, track):
        """타임라인 변경 시 프리뷰 업데이트"""
        # 현재 재생 헤드 위치의 프리뷰 업데이트
        current_frame = self.timeline_widget.playhead_position
        self.update_preview(current_frame) 