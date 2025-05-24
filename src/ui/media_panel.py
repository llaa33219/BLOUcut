"""
BLOUcut 미디어 패널
미디어 파일 관리 및 표시
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QListWidget, QListWidgetItem, QLabel, QLineEdit,
                           QComboBox, QFrame, QFileDialog, QMenu, QMessageBox,
                           QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import QPixmap, QIcon, QDrag, QPainter, QColor, QFont, QMouseEvent

from ..core.media_analyzer import MediaAnalyzer

class MediaPanel(QWidget):
    """미디어 패널"""
    
    # 시그널
    media_dropped = pyqtSignal(str, int, int)  # 미디어 파일, 트랙, 시작 프레임
    media_selected = pyqtSignal(str)  # 선택된 미디어 파일
    
    def __init__(self):
        super().__init__()
        self.media_items = []  # 미디어 아이템 리스트
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 상단 툴바
        toolbar_layout = self.create_toolbar()
        layout.addLayout(toolbar_layout)
        
        # 검색 및 필터
        search_layout = self.create_search_filter()
        layout.addLayout(search_layout)
        
        # 미디어 리스트
        self.media_list = MediaListWidget()  # 커스텀 리스트 위젯 사용
        self.media_list.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        self.media_list.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.media_list.itemDoubleClicked.connect(self.preview_media)
        self.media_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.media_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.media_list.customContextMenuRequested.connect(self.show_context_menu)
        # 드래그 시작 시그널 연결
        self.media_list.media_dragged.connect(self.on_media_dragged)
        layout.addWidget(self.media_list, 1)
        
        # 미디어 정보
        self.info_label = QLabel("미디어를 선택하세요")
        self.info_label.setWordWrap(True)
        self.info_label.setMaximumHeight(60)
        layout.addWidget(self.info_label)
        
        self.apply_styles()
        
        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)
        
    def create_toolbar(self):
        """툴바 생성"""
        layout = QHBoxLayout()
        
        # 미디어 추가 버튼
        add_button = QPushButton("추가")
        add_button.clicked.connect(self.add_media_files)
        layout.addWidget(add_button)
        
        # 폴더 추가 버튼
        add_folder_button = QPushButton("폴더")
        add_folder_button.clicked.connect(self.add_media_folder)
        layout.addWidget(add_folder_button)
        
        # 새로고침 버튼
        refresh_button = QPushButton("새로고침")
        refresh_button.clicked.connect(self.refresh_media_list)
        layout.addWidget(refresh_button)
        
        layout.addStretch()
        
        return layout
        
    def create_search_filter(self):
        """검색 및 필터 생성"""
        layout = QHBoxLayout()
        
        # 검색 입력
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색...")
        self.search_input.textChanged.connect(self.filter_media)
        layout.addWidget(self.search_input)
        
        # 타입 필터
        self.type_filter = QComboBox()
        self.type_filter.addItems(["전체", "비디오", "오디오", "이미지"])
        self.type_filter.currentTextChanged.connect(self.filter_media)
        layout.addWidget(self.type_filter)
        
        return layout
        
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QWidget {
                background-color: #3c3c3c;
                color: white;
            }
            
            QPushButton {
                background-color: #555;
                border: 1px solid #777;
                border-radius: 3px;
                padding: 5px 10px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #666;
            }
            
            QPushButton:pressed {
                background-color: #444;
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
            
            QComboBox {
                background-color: #555;
                border: 1px solid #777;
                border-radius: 3px;
                padding: 5px;
            }
            
            QComboBox::drop-down {
                border: none;
            }
            
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 3px;
            }
            
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #444;
            }
            
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            
            QListWidget::item:hover {
                background-color: #555;
            }
            
            QLabel {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
    def add_media_files(self):
        """미디어 파일 추가"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "미디어 파일 선택",
            "",
            "미디어 파일 (*.mp4 *.avi *.mov *.mkv *.mp3 *.wav *.aac *.jpg *.png *.bmp);;비디오 파일 (*.mp4 *.avi *.mov *.mkv);;오디오 파일 (*.mp3 *.wav *.aac);;이미지 파일 (*.jpg *.png *.bmp);;모든 파일 (*)"
        )
        
        for file_path in file_paths:
            self.add_media(file_path)
            
    def add_media_folder(self):
        """폴더의 모든 미디어 파일 추가"""
        folder_path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        
        if folder_path:
            media_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.mp3', '.wav', '.aac', '.jpg', '.png', '.bmp', '.jpeg', '.gif']
            
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in media_extensions):
                        file_path = os.path.join(root, file)
                        self.add_media(file_path)
                        
    def add_media(self, file_path):
        """미디어 파일 추가"""
        if not os.path.exists(file_path):
            return
            
        # 중복 체크
        for item in self.media_items:
            if item['path'] == file_path:
                return
                
        # 미디어 정보 생성
        media_info = self.get_media_info(file_path)
        self.media_items.append(media_info)
        
        # 리스트 위젯에 추가
        self.add_media_to_list(media_info)
        
    def get_media_info(self, file_path):
        """미디어 파일 정보 추출"""
        # MediaAnalyzer로 실제 미디어 정보 추출
        media_info = MediaAnalyzer.get_media_info(file_path)
        
        # UI에서 사용할 형식으로 변환
        type_mapping = {
            'video': '비디오',
            'audio': '오디오', 
            'image': '이미지',
            'unknown': '기타'
        }
        
        return {
            'path': file_path,
            'name': media_info['name'],
            'type': type_mapping.get(media_info['media_type'], '기타'),
            'size': media_info['file_size'],
            'extension': os.path.splitext(file_path)[1].lower(),
            'duration': MediaAnalyzer.format_duration(media_info['duration']),
            'duration_seconds': media_info['duration'],
            'duration_frames': media_info['duration_frames'],
            'width': media_info.get('width', 0),
            'height': media_info.get('height', 0),
            'fps': media_info.get('fps', 30.0),
            'media_type_raw': media_info['media_type']
        }
        

            
    def add_media_to_list(self, media_info):
        """리스트 위젯에 미디어 아이템 추가"""
        item = QListWidgetItem()
        item_widget = MediaListItem(media_info)
        
        # 아이템 크기 설정
        item.setSizeHint(item_widget.sizeHint())
        
        # 미디어 정보를 아이템에 저장
        item.setData(Qt.ItemDataRole.UserRole, media_info)
        
        self.media_list.addItem(item)
        self.media_list.setItemWidget(item, item_widget)
        
    def refresh_media_list(self):
        """미디어 리스트 새로고침"""
        # 존재하지 않는 파일 제거
        valid_items = []
        for item in self.media_items:
            if os.path.exists(item['path']):
                valid_items.append(item)
                
        self.media_items = valid_items
        
        # 리스트 위젯 다시 구성
        self.media_list.clear()
        for media_info in self.media_items:
            self.add_media_to_list(media_info)
            
    def filter_media(self):
        """미디어 필터링"""
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        
        for i in range(self.media_list.count()):
            item = self.media_list.item(i)
            media_info = item.data(Qt.ItemDataRole.UserRole)
            
            # 검색 텍스트 필터
            name_match = search_text in media_info['name'].lower()
            
            # 타입 필터
            type_match = (type_filter == "전체" or media_info['type'] == type_filter)
            
            # 아이템 표시/숨김
            item.setHidden(not (name_match and type_match))
            
    def preview_media(self, item):
        """미디어 미리보기"""
        media_info = item.data(Qt.ItemDataRole.UserRole)
        self.media_selected.emit(media_info['path'])
        
    def on_selection_changed(self):
        """선택 변경시 정보 업데이트"""
        selected_items = self.media_list.selectedItems()
        
        if selected_items:
            media_info = selected_items[0].data(Qt.ItemDataRole.UserRole)
            info_text = f"이름: {media_info['name']}\n"
            info_text += f"타입: {media_info['type']}\n"
            info_text += f"크기: {self.format_file_size(media_info['size'])}\n"
            info_text += f"지속시간: {media_info['duration']}"
            self.info_label.setText(info_text)
        else:
            self.info_label.setText("미디어를 선택하세요")
            
    def format_file_size(self, size_bytes):
        """파일 크기 포맷팅"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
        
    def show_context_menu(self, position):
        """우클릭 컨텍스트 메뉴"""
        item = self.media_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        
        # 타임라인에 추가
        add_to_timeline_action = menu.addAction("타임라인에 추가")
        add_to_timeline_action.triggered.connect(lambda: self.add_to_timeline(item))
        
        # 미리보기
        preview_action = menu.addAction("미리보기")
        preview_action.triggered.connect(lambda: self.preview_media(item))
        
        menu.addSeparator()
        
        # 파일 위치 열기
        open_location_action = menu.addAction("파일 위치 열기")
        open_location_action.triggered.connect(lambda: self.open_file_location(item))
        
        # 삭제
        remove_action = menu.addAction("목록에서 제거")
        remove_action.triggered.connect(lambda: self.remove_media(item))
        
        menu.exec(self.media_list.mapToGlobal(position))
        
    def add_to_timeline(self, item):
        """타임라인에 미디어 추가"""
        media_info = item.data(Qt.ItemDataRole.UserRole)
        self.media_dropped.emit(media_info['path'], 0, 0)  # 첫 번째 트랙, 시작 위치
        
    def open_file_location(self, item):
        """파일 위치 열기"""
        media_info = item.data(Qt.ItemDataRole.UserRole)
        file_path = media_info['path']
        
        if os.path.exists(file_path):
            # 플랫폼별 파일 탐색기 열기
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", "/select,", file_path])
            elif system == "Darwin":  # macOS
                subprocess.run(["open", "-R", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", os.path.dirname(file_path)])
        else:
            QMessageBox.warning(self, "파일 없음", "파일을 찾을 수 없습니다.")
            
    def remove_media(self, item):
        """미디어 목록에서 제거"""
        media_info = item.data(Qt.ItemDataRole.UserRole)
        
        # 미디어 리스트에서 제거
        self.media_items = [item for item in self.media_items if item['path'] != media_info['path']]
        
        # 위젯에서 제거
        row = self.media_list.row(item)
        self.media_list.takeItem(row)
        
    def clear(self):
        """미디어 패널 초기화"""
        self.media_items.clear()
        self.media_list.clear()
        self.info_label.setText("미디어를 선택하세요")
        
    # 드래그 앤 드롭 지원
    def dragEnterEvent(self, event):
        """드래그 진입 이벤트"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """드롭 이벤트"""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.add_media(file_path)
            elif os.path.isdir(file_path):
                # 폴더인 경우 하위 미디어 파일들 추가
                media_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.mp3', '.wav', '.aac', '.jpg', '.png', '.bmp']
                for file in os.listdir(file_path):
                    if any(file.lower().endswith(ext) for ext in media_extensions):
                        self.add_media(os.path.join(file_path, file))
                        
        event.acceptProposedAction()
        
    def on_media_dragged(self, file_path):
        """미디어가 드래그될 때 호출"""
        # 타임라인으로 드래그&드롭 시그널 발생 (드래그 완료 후에만)
        # 실제 드롭은 타임라인의 dropEvent에서 처리됨
        pass

class MediaListItem(QWidget):
    """미디어 리스트 아이템 위젯"""
    
    def __init__(self, media_info):
        super().__init__()
        self.media_info = media_info
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # 썸네일 (아이콘)
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(40, 40)
        thumbnail_label.setStyleSheet("border: 1px solid #555; border-radius: 3px;")
        
        # 미디어 타입에 따른 아이콘 설정
        icon_text = "🎬" if self.media_info['type'] == "비디오" else \
                   "🎵" if self.media_info['type'] == "오디오" else \
                   "🖼️" if self.media_info['type'] == "이미지" else "📄"
        
        thumbnail_label.setText(icon_text)
        thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thumbnail_label)
        
        # 정보 레이아웃
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # 파일 이름
        name_label = QLabel(self.media_info['name'])
        name_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        name_label.setStyleSheet("border: none; background: transparent;")
        info_layout.addWidget(name_label)
        
        # 추가 정보
        details = f"{self.media_info['type']} • {self.media_info['duration']}"
        details_label = QLabel(details)
        details_label.setFont(QFont("Arial", 8))
        details_label.setStyleSheet("color: #aaa; border: none; background: transparent;")
        info_layout.addWidget(details_label)
        
        layout.addLayout(info_layout, 1)
        
        # 크기 설정
        self.setMaximumHeight(60)
        
    def sizeHint(self):
        """크기 힌트"""
        return self.size()


class MediaListWidget(QListWidget):
    """드래그&드롭이 가능한 미디어 리스트 위젯"""
    
    # 시그널
    media_dragged = pyqtSignal(str)  # 미디어 파일 경로
    
    def __init__(self):
        super().__init__()
        self.drag_start_position = None
        
    def mousePressEvent(self, event: QMouseEvent):
        """마우스 프레스 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event: QMouseEvent):
        """마우스 이동 이벤트 - 드래그 시작"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
            
        if not self.drag_start_position:
            return
            
        # 드래그 거리 확인
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 
            QApplication.startDragDistance()):
            return
            
        # 현재 선택된 아이템 확인
        current_item = self.currentItem()
        if not current_item:
            return
            
        # 미디어 정보 가져오기
        media_info = current_item.data(Qt.ItemDataRole.UserRole)
        if not media_info:
            return
            
        # 드래그 시작
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # 파일 경로를 URL로 설정
        urls = [QUrl.fromLocalFile(media_info['path'])]
        mime_data.setUrls(urls)
        
        # 추가 데이터 설정
        mime_data.setText(media_info['path'])
        mime_data.setData("application/x-media-file", media_info['path'].encode())
        
        drag.setMimeData(mime_data)
        
        # 드래그 실행
        drop_action = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        
        if drop_action == Qt.DropAction.CopyAction:
            # 드래그 완료 시그널 발생
            self.media_dragged.emit(media_info['path'])