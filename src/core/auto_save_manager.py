"""
BLOUcut 자동 저장 관리자
프로젝트 자동 저장 및 백업/복구 시스템
"""

import os
import json
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, List
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

class AutoSaveManager(QObject):
    """자동 저장 관리자"""
    
    # 시그널
    auto_saved = pyqtSignal(str)  # 자동 저장됨 (파일 경로)
    backup_created = pyqtSignal(str)  # 백업 생성됨
    recovery_available = pyqtSignal(list)  # 복구 가능한 파일들
    
    def __init__(self, project_manager, save_interval=300):  # 기본 5분
        super().__init__()
        self.project_manager = project_manager
        self.save_interval = save_interval  # 초 단위
        self.is_enabled = True
        self.has_unsaved_changes = False
        self.last_save_time = 0
        
        # 자동 저장 타이머
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        
        # 백업 디렉토리 설정
        self.backup_dir = Path.home() / ".bloucut" / "backups"
        self.auto_save_dir = Path.home() / ".bloucut" / "autosave"
        self.crash_recovery_dir = Path.home() / ".bloucut" / "recovery"
        
        # 디렉토리 생성
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.auto_save_dir.mkdir(parents=True, exist_ok=True)
        self.crash_recovery_dir.mkdir(parents=True, exist_ok=True)
        
        # 시작 시 복구 파일 확인
        self.check_recovery_files()
        
    def start_auto_save(self):
        """자동 저장 시작"""
        if self.is_enabled and self.save_interval > 0:
            self.auto_save_timer.start(self.save_interval * 1000)
            
    def stop_auto_save(self):
        """자동 저장 중지"""
        self.auto_save_timer.stop()
        
    def set_save_interval(self, seconds: int):
        """저장 간격 설정"""
        self.save_interval = seconds
        if self.auto_save_timer.isActive():
            self.auto_save_timer.stop()
            self.start_auto_save()
            
    def set_enabled(self, enabled: bool):
        """자동 저장 활성화/비활성화"""
        self.is_enabled = enabled
        if enabled:
            self.start_auto_save()
        else:
            self.stop_auto_save()
            
    def mark_unsaved_changes(self):
        """미저장 변경사항 표시"""
        self.has_unsaved_changes = True
        
    def mark_saved(self):
        """저장됨 표시"""
        self.has_unsaved_changes = False
        self.last_save_time = time.time()
        
    def auto_save(self):
        """자동 저장 실행"""
        if not self.has_unsaved_changes:
            return
            
        try:
            # 현재 프로젝트가 있는지 확인
            current_project = self.project_manager.get_current_project()
            if not current_project:
                return
                
            # 자동 저장 파일명 생성
            timestamp = int(time.time())
            project_name = current_project.get("name", "untitled")
            auto_save_file = self.auto_save_dir / f"{project_name}_autosave_{timestamp}.blc"
            
            # 프로젝트 데이터 저장
            project_data = self.project_manager.serialize_project()
            
            with open(auto_save_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
                
            # 이전 자동 저장 파일 정리 (최근 5개만 유지)
            self.cleanup_old_auto_saves(project_name)
            
            # 크래시 복구 파일 생성
            self.create_crash_recovery_file(project_data)
            
            self.auto_saved.emit(str(auto_save_file))
            
        except Exception as e:
            print(f"자동 저장 오류: {e}")
            
    def create_backup(self, project_path: str) -> str:
        """프로젝트 백업 생성"""
        try:
            project_file = Path(project_path)
            if not project_file.exists():
                return ""
                
            # 백업 파일명 생성
            timestamp = int(time.time())
            backup_name = f"{project_file.stem}_backup_{timestamp}{project_file.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # 파일 복사
            shutil.copy2(project_path, backup_path)
            
            # 오래된 백업 정리 (최근 10개만 유지)
            self.cleanup_old_backups(project_file.stem)
            
            self.backup_created.emit(str(backup_path))
            return str(backup_path)
            
        except Exception as e:
            print(f"백업 생성 오류: {e}")
            return ""
            
    def create_crash_recovery_file(self, project_data: Dict):
        """크래시 복구 파일 생성"""
        try:
            recovery_file = self.crash_recovery_dir / "recovery.blc"
            recovery_data = {
                "timestamp": time.time(),
                "project_data": project_data,
                "session_id": os.getpid()  # 프로세스 ID로 세션 구분
            }
            
            with open(recovery_file, 'w', encoding='utf-8') as f:
                json.dump(recovery_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"복구 파일 생성 오류: {e}")
            
    def check_recovery_files(self):
        """복구 파일 확인"""
        try:
            recovery_files = []
            
            # 자동 저장 파일 확인
            for file_path in self.auto_save_dir.glob("*_autosave_*.blc"):
                recovery_files.append({
                    "path": str(file_path),
                    "type": "autosave",
                    "timestamp": file_path.stat().st_mtime,
                    "name": file_path.stem
                })
                
            # 크래시 복구 파일 확인
            recovery_file = self.crash_recovery_dir / "recovery.blc"
            if recovery_file.exists():
                try:
                    with open(recovery_file, 'r', encoding='utf-8') as f:
                        recovery_data = json.load(f)
                        
                    # 같은 세션이 아닌 경우만 복구 대상
                    if recovery_data.get("session_id") != os.getpid():
                        recovery_files.append({
                            "path": str(recovery_file),
                            "type": "crash_recovery",
                            "timestamp": recovery_data.get("timestamp", 0),
                            "name": "크래시 복구"
                        })
                except:
                    pass
                    
            if recovery_files:
                # 최신 순으로 정렬
                recovery_files.sort(key=lambda x: x["timestamp"], reverse=True)
                self.recovery_available.emit(recovery_files)
                
        except Exception as e:
            print(f"복구 파일 확인 오류: {e}")
            
    def recover_project(self, recovery_info: Dict) -> Optional[Dict]:
        """프로젝트 복구"""
        try:
            file_path = recovery_info["path"]
            
            if recovery_info["type"] == "crash_recovery":
                # 크래시 복구 파일
                with open(file_path, 'r', encoding='utf-8') as f:
                    recovery_data = json.load(f)
                return recovery_data.get("project_data")
            else:
                # 자동 저장 파일
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
        except Exception as e:
            print(f"프로젝트 복구 오류: {e}")
            return None
            
    def cleanup_old_auto_saves(self, project_name: str, keep_count: int = 5):
        """오래된 자동 저장 파일 정리"""
        try:
            pattern = f"{project_name}_autosave_*.blc"
            auto_save_files = list(self.auto_save_dir.glob(pattern))
            
            # 수정 시간으로 정렬 (최신 순)
            auto_save_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 오래된 파일 삭제
            for file_path in auto_save_files[keep_count:]:
                file_path.unlink()
                
        except Exception as e:
            print(f"자동 저장 파일 정리 오류: {e}")
            
    def cleanup_old_backups(self, project_name: str, keep_count: int = 10):
        """오래된 백업 파일 정리"""
        try:
            pattern = f"{project_name}_backup_*.blc"
            backup_files = list(self.backup_dir.glob(pattern))
            
            # 수정 시간으로 정렬 (최신 순)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 오래된 파일 삭제
            for file_path in backup_files[keep_count:]:
                file_path.unlink()
                
        except Exception as e:
            print(f"백업 파일 정리 오류: {e}")
            
    def get_backup_list(self, project_name: str = None) -> List[Dict]:
        """백업 목록 가져오기"""
        try:
            backups = []
            
            if project_name:
                pattern = f"{project_name}_backup_*.blc"
            else:
                pattern = "*_backup_*.blc"
                
            for file_path in self.backup_dir.glob(pattern):
                backups.append({
                    "path": str(file_path),
                    "name": file_path.stem,
                    "timestamp": file_path.stat().st_mtime,
                    "size": file_path.stat().st_size
                })
                
            # 최신 순으로 정렬
            backups.sort(key=lambda x: x["timestamp"], reverse=True)
            return backups
            
        except Exception as e:
            print(f"백업 목록 조회 오류: {e}")
            return []
            
    def clear_recovery_files(self):
        """복구 파일 정리"""
        try:
            # 크래시 복구 파일 삭제
            recovery_file = self.crash_recovery_dir / "recovery.blc"
            if recovery_file.exists():
                recovery_file.unlink()
                
            # 오래된 자동 저장 파일 정리 (1주일 이상 된 것)
            week_ago = time.time() - (7 * 24 * 60 * 60)
            for file_path in self.auto_save_dir.glob("*_autosave_*.blc"):
                if file_path.stat().st_mtime < week_ago:
                    file_path.unlink()
                    
        except Exception as e:
            print(f"복구 파일 정리 오류: {e}")
            
    def get_settings(self) -> Dict:
        """자동 저장 설정 가져오기"""
        return {
            "enabled": self.is_enabled,
            "interval": self.save_interval,
            "backup_dir": str(self.backup_dir),
            "auto_save_dir": str(self.auto_save_dir)
        }
        
    def load_settings(self, settings: Dict):
        """자동 저장 설정 로드"""
        self.set_enabled(settings.get("enabled", True))
        self.set_save_interval(settings.get("interval", 300))
        
        # 사용자 정의 디렉토리가 있으면 사용
        if "backup_dir" in settings:
            custom_backup_dir = Path(settings["backup_dir"])
            if custom_backup_dir.exists():
                self.backup_dir = custom_backup_dir
                
        if "auto_save_dir" in settings:
            custom_auto_save_dir = Path(settings["auto_save_dir"])
            if custom_auto_save_dir.exists():
                self.auto_save_dir = custom_auto_save_dir 