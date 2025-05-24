#!/usr/bin/env python3
"""
BLOUcut - 전문적인 영상 편집기
메인 진입점
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ui.main_window import MainWindow

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    app.setApplicationName("BLOUcut")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BLOUcut Team")
    
    # 다크 테마 적용
    app.setStyleSheet("""
        QApplication {
            background-color: #2b2b2b;
            color: #ffffff;
        }
    """)
    
    # 메인 윈도우 생성
    main_window = MainWindow()
    main_window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 