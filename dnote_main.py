# 애플리케이션 정보
APP_NAME = "dNote"
VERSION = "0.0.101"  # 현재 버전
GITHUB_OWNER = "I-MM"
GITHUB_REPO = "dNote"

print(f"{APP_NAME} v{VERSION}\n")
print("로딩중... ", end="")

import pygetwindow as gw
import subprocess
import mouse
import logging
import tkinter as tk
import tkinter.font as tkfont 
import threading
import asyncio
import time
import ctypes
import os
import sys
import sounddevice as sd
import wave
import lameenc
import math
import requests
import uuid
import soundfile as sf
import numpy as np
import json
import customtkinter as ctk
import datetime
import shutil
import sentry_sdk
import platform
import glob
import winreg
import errno
import webbrowser

from logging.handlers import RotatingFileHandler
from pathlib import Path
from pynput import mouse
from queue import Queue
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw, ImageTk
from tkinter import messagebox
from datetime import datetime
from sentry_sdk.integrations.threading import ThreadingIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from license_validator import LicenseValidator
from download_manager import run_download_process, set_trial_mode, trial_servers
from dentweb_note_upload import get_patient_name, run_dentweb_upload, click_EMR_button, click_record_button, click_location, activate_window, activate_window2, close_DUR_popup
from chart_programs import chart_manager, set_chart_program, get_available_chart_programs, auto_detect_chart_program, get_patient_info
from dnote_settings import DentalAssistApp
from update_manager import UpdateManager
from cursor_utils import set_block_cursor, restore_default_cursor, show_paste_tip, hide_paste_tip
from file_watcher import initialize_file_watcher, set_main_event_loop
import psutil
import pyautogui

# 병렬 오디오 처리 모듈 import
try:
    from audio_parallel_processor import process_audio_parallel, should_use_parallel_processing
    PARALLEL_PROCESSING_AVAILABLE = True
    logging.info("병렬 오디오 처리 모듈이 성공적으로 로드되었습니다.")
except ImportError as e:
    logging.warning(f"병렬 오디오 처리 모듈을 로드할 수 없습니다: {e}")
    PARALLEL_PROCESSING_AVAILABLE = False

# Sentry 로깅 설정
sentry_logging = LoggingIntegration(
    level=logging.INFO,        # 캡처할 로그 레벨 설정
    event_level=logging.ERROR  # ERROR 이상 레벨만 이벤트로 전송
)

# 로컬 로깅 설정
def setup_logging():
    """로깅 설정 및 로그 파일 경로 설정"""
    # 사용자 로컬 폴더에 로그 저장
    log_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'dNote', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'dnote_main.log')
    
    # 기존 핸들러 제거 (중복 방지)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 루트 로거에 직접 핸들러 추가 (기본 설정보다 더 명시적인 방법)
    root_logger.setLevel(logging.INFO)
    
    # 파일 핸들러 추가 - RotatingFileHandler로 변경
    # 최대 2MB, 최대 4개 백업 파일 (총 8MB 제한)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=2*1024*1024,  # 2MB
        backupCount=4,
        encoding='utf-8',
        delay=False
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 콘솔 핸들러 추가 - --noconsole 환경을 고려한 안전한 방식
    try:
        # 콘솔 창이 있는지 확인
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd and sys.stdout is not None and hasattr(sys.stdout, 'write'):
            # 콘솔이 있고 stdout이 유효한 경우에만 콘솔 핸들러 추가
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
    except Exception:
        # 콘솔 핸들러 추가 실패 시 무시 (파일 로깅은 계속 작동)
        pass
    
    # 로그 파일 확인
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'-'*50}\n새 세션 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'-'*50}\n")
        print(f"로그 파일이 생성되었습니다: {log_file}")
        
        # 로그 로테이션 정보 기록
        root_logger.info(f"로그 파일 설정: 최대 크기 2MB, 백업 파일 4개 (총 8MB 제한)")
    except Exception as e:
        print(f"로그 파일 초기화 중 오류 발생: {str(e)}")
    
    # 어플리케이션 로거 생성
    app_logger = logging.getLogger('dNote')
    app_logger.setLevel(logging.INFO)
    
    # 로그 시스템 초기화 로그 기록
    app_logger.info(f"로깅 시스템 초기화 완료 (로그 파일: {log_file})")
    
    return app_logger

# 콘솔 핸들러를 다시 설정하는 함수
def reinitialize_console_logging():
    """콘솔이 새로 생성된 후 콘솔 로깅 핸들러를 다시 설정"""
    try:
        root_logger = logging.getLogger()
        
        # 기존 StreamHandler 제거 (RotatingFileHandler는 제외)
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                root_logger.removeHandler(handler)
        
        # 새로운 콘솔 핸들러 추가
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        print("콘솔 로깅 핸들러가 다시 설정되었습니다.")
    except Exception as e:
        print(f"콘솔 로깅 핸들러 재설정 중 오류: {e}")

# 로거 초기화 및 외부 모듈에서 사용할 수 있도록 변수로 설정
# logger = setup_logging()

# Sentry 초기화 함수
def initialize_sentry():
    """Sentry.io 초기화 및 설정"""
    try:
        # 버전 정보 가져오기 (있는 경우)
        version_info = "0.0.0"
        try:
            if 'app_version' in globals():
                version_info = VERSION
        except:
            pass
            
        # Sentry SDK 초기화
        sentry_sdk.init(
            dsn="https://457adea841fd9b0c49c0594f5b40f388@o4509298129502208.ingest.de.sentry.io/4509298147721296",
            # 성능 추적 비율 (0.0 - 1.0, 1.0은 모든 트랜잭션 추적)
            traces_sample_rate=0.6,
            # 프로파일링 비율
            profiles_sample_rate=0.6,
            # 릴리즈 정보
            release=f"dnote@{version_info}",
            # 환경 설정 (개발/프로덕션)
            environment="production",
            # 스레드 통합
            integrations=[
                ThreadingIntegration(propagate_hub=True),
                sentry_logging,
            ],
            # 이벤트 샘플링 비율 증가 (더 많은 이벤트 캡처)
            sample_rate=1.0,
            # 최대 breadcrumbs 증가 (기본값 100)
            max_breadcrumbs=150,
            # 개인정보 보호를 위한 설정
            send_default_pii=False,
            # 내부 오류 무시 (Sentry 자체 오류는 보고하지 않음)
            ignore_errors=[KeyboardInterrupt],
            # 로깅 이벤트 처리 향상
            before_send=before_send_event
        )
        
        # Sentry에 기본 컨텍스트 추가
        sentry_sdk.set_context("app_info", {
            "version": version_info,
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "app_start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Breadcrumb 추가 - 앱 시작 정보
        sentry_sdk.add_breadcrumb(
            category="lifecycle",
            message="애플리케이션 시작됨",
            level="info"
        )
        
        logger.info("Sentry 초기화 완료")
    except Exception as e:
        # Sentry 초기화 실패해도 앱 실행에 영향 없도록
        logger.error(f"Sentry 초기화 실패: {str(e)}")

# Sentry 이벤트 전송 전 처리 함수
def before_send_event(event, hint):
    """
    Sentry 이벤트가 전송되기 전에 호출되는 함수
    추가 컨텍스트 정보를 첨부하거나 이벤트를 필터링할 수 있음
    """
    try:
        # 추가 컨텍스트 정보
        if 'extra' not in event:
            event['extra'] = {}
            
        # 현재 시간 추가
        event['extra']['local_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 메모리 사용량 추가
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        event['extra']['memory_usage_mb'] = memory_info.rss / (1024 * 1024)
        
        # 예외 정보가 있는 경우 추가 컨텍스트 수집
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info']
            if exc_type and exc_value:
                # 에러 타입과 메시지를 분리하여 저장
                event['extra']['error_type'] = exc_type.__name__
                event['extra']['error_value'] = str(exc_value)
                
                # 현재 로깅 설정 추가
                event['extra']['logging_config'] = {
                    'root_level': logging.getLevelName(logging.getLogger().level),
                    'app_level': logging.getLevelName(logging.getLogger('dNote').level)
                }
    except Exception as e:
        # before_send 내부 오류는 무시 (앱에 영향 없도록)
        pass
        
    return event

# 유틸리티 함수: 에러 로깅 및 Sentry 캡처를 동시에 처리
def log_error(message, exc_info=None, extra_context=None, level="error"):
    """
    에러를 로깅하고 Sentry에 전송하는 유틸리티 함수
    
    Args:
        message: 에러 메시지
        exc_info: 예외 정보 (예외 객체, 또는 sys.exc_info())
        extra_context: 추가 컨텍스트 정보 (dict)
        level: 로그 레벨 (error, warning, info 등)
    """
    # 로컬 로깅
    if hasattr(logger, level):
        log_method = getattr(logger, level)
        if exc_info:
            log_method(message, exc_info=exc_info)
        else:
            log_method(message)
    
    try:
        # Sentry에 명시적으로 전송
        with sentry_sdk.push_scope() as scope:
            # 추가 컨텍스트 정보 설정
            if extra_context:
                for key, value in extra_context.items():
                    scope.set_extra(key, value)
            
            # 현재 모듈 이름 추가
            import inspect
            caller_frame = inspect.currentframe().f_back
            if caller_frame:
                module_name = caller_frame.f_globals.get('__name__', 'unknown')
                scope.set_tag("module", module_name)
            
            # 로그 레벨에 따라 적절한 Sentry 메서드 호출
            if level == "error" and exc_info:
                # 예외가 제공된 경우 예외로 캡처
                sentry_sdk.capture_exception(exc_info)
            else:
                # 그 외에는 메시지로 캡처
                sentry_sdk.capture_message(
                    message,
                    level=level
                )
    except Exception as e:
        # Sentry 전송 실패해도 앱 실행에 영향 없도록
        if hasattr(logger, 'error'):
            logger.error(f"Sentry 이벤트 전송 실패: {str(e)}")

# 전역 예외 처리기
def setup_global_exception_handler():
    """처리되지 않은 전역 예외를 처리하는 핸들러 설정"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # KeyboardInterrupt는 정상 종료로 간주
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        # 로컬 로깅
        logger.error("처리되지 않은 예외 발생", exc_info=(exc_type, exc_value, exc_traceback))
        
        # 추가 컨텍스트 정보 수집
        extra_context = {
            "time_of_error": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "app_uptime_seconds": (datetime.now() - app_start_time).total_seconds() if 'app_start_time' in globals() else 0
        }
        
        # Sentry에 명시적으로 전송
        try:
            with sentry_sdk.push_scope() as scope:
                # 추가 컨텍스트 정보 설정
                for key, value in extra_context.items():
                    scope.set_extra(key, value)
                
                # 사용자 정의 핑거프린트 설정
                scope.fingerprint = [
                    '{{ default }}',
                    str(exc_type.__name__),
                    str(exc_value)
                ]
                
                # 명시적으로 예외 캡처
                sentry_sdk.capture_exception((exc_type, exc_value, exc_traceback))
        except Exception as e:
            logger.error(f"Sentry에 예외 전송 중 오류 발생: {str(e)}")
    
    # 글로벌 예외 핸들러 설정
    sys.excepthook = handle_exception

# 애플리케이션 시작 시간 기록
app_start_time = datetime.now()

# 전역 업데이트 매니저 인스턴스
update_manager = None

def check_updates_manually():
    """메뉴에서 업데이트 수동 확인"""
    global update_manager
    if update_manager:
        update_manager.check_for_updates(auto_update=False)

# 중복 실행 방지
def prevent_multiple_instances():
    """프로그램의 중복 실행을 방지합니다."""
    try:
        # 뮤텍스 생성 시도
        mutex = ctypes.windll.kernel32.CreateMutexW(None, 1, "Global\\dNoteMutex")
        error = ctypes.GetLastError()
        
        # 이미 뮤텍스가 존재하면 프로그램이 이미 실행 중
        if error == 183:  # ERROR_ALREADY_EXISTS
            messagebox.showerror("실행 오류", "dNote가 이미 실행 중입니다.")
            sys.exit(0)
            
        return mutex
    except Exception as e:
        logging.error(f"중복 실행 확인 중 오류 발생: {e}")
        return None

# 프로그램 설정 관련 함수
def load_settings():
    """설정 파일에서 사용자 설정을 로드합니다."""
    global PRESS_THRESHOLD, TARGET_BUTTON, MAX_RECORDING_DURATION, MODEL_MODE
    global DENTWEB_RECORDING_ENABLED, ALLOWED_LANGUAGES, input_device_index
    global SEPARATE_EXTEND_BUTTON, EXTEND_BUTTON, EXTEND_THRESHOLD
    global TERMS_ACCEPTED, TERMS_VERSION, SAVE_PATH  # SAVE_PATH 추가
    global DENTWEB_CHART_UPLOAD_ENABLED  # 차트 업로드 기능 추가
    global UPLOAD_FILES_TO_DENTWEB  # 파일 업로드 기능 추가
    global CHART_PROGRAM  # 차트 프로그램 설정 추가
    global SHOW_NOTIFICATION_OVERLAY  # 알림 UI 표시 기능 추가
    global WATCH_FOLDER_PATH, WATCH_FOLDER_ENABLED  # 파일 감시 기능 추가
    global SUMMARY_LENGTH_SETTING  # 요약 길이 설정 추가
    global DELETE_ORIGINAL_AUDIO_ENABLED  # 원본 음성 파일 삭제 옵션 추가

    # %APPDATA% 폴더 내에 dNote 폴더와 설정 파일 경로 설정
    app_data_dir = os.getenv('APPDATA')
    if not app_data_dir:
        app_data_dir = os.path.expanduser('~')  # 폴백으로 홈 디렉토리 사용
        
    settings_dir = os.path.join(app_data_dir, 'dNote')
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir)
        
    settings_file = os.path.join(settings_dir, 'dNote_settings.json')
    
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
                # 설정값 로드
                PRESS_THRESHOLD = settings.get('PRESS_THRESHOLD', PRESS_THRESHOLD)
                MAX_RECORDING_DURATION = settings.get('MAX_RECORDING_DURATION', MAX_RECORDING_DURATION)
                
                # TARGET_BUTTON 문자열을 실제 Button 객체로 변환
                target_button_str = settings.get('TARGET_BUTTON', 'middle')
                if target_button_str == 'left':
                    TARGET_BUTTON = mouse.Button.left
                elif target_button_str == 'right':
                    TARGET_BUTTON = mouse.Button.right
                else:
                    TARGET_BUTTON = mouse.Button.middle
                
                MODEL_MODE = settings.get('MODEL_MODE', MODEL_MODE)
                DENTWEB_RECORDING_ENABLED = settings.get('DENTWEB_RECORDING_ENABLED', DENTWEB_RECORDING_ENABLED)
                DENTWEB_CHART_UPLOAD_ENABLED = settings.get('DENTWEB_CHART_UPLOAD_ENABLED', DENTWEB_CHART_UPLOAD_ENABLED)
                UPLOAD_FILES_TO_DENTWEB = settings.get('UPLOAD_FILES_TO_DENTWEB', UPLOAD_FILES_TO_DENTWEB)
                SHOW_NOTIFICATION_OVERLAY = settings.get('SHOW_NOTIFICATION_OVERLAY', SHOW_NOTIFICATION_OVERLAY)
                WATCH_FOLDER_PATH = settings.get('WATCH_FOLDER_PATH', None)
                WATCH_FOLDER_ENABLED = settings.get('WATCH_FOLDER_ENABLED', False)
                SUMMARY_LENGTH_SETTING = settings.get('SUMMARY_LENGTH_SETTING', SUMMARY_LENGTH_SETTING)
                DELETE_ORIGINAL_AUDIO_ENABLED = settings.get('DELETE_ORIGINAL_AUDIO_ENABLED', DELETE_ORIGINAL_AUDIO_ENABLED)
                ALLOWED_LANGUAGES = settings.get('ALLOWED_LANGUAGES', ALLOWED_LANGUAGES)
                input_device_index = settings.get('input_device_index', input_device_index)
                
                # 녹음 연장 버튼 설정 로드
                SEPARATE_EXTEND_BUTTON = settings.get('SEPARATE_EXTEND_BUTTON', SEPARATE_EXTEND_BUTTON)
                EXTEND_THRESHOLD = settings.get('EXTEND_THRESHOLD', EXTEND_THRESHOLD)
                
                # 사용자 지정 저장 경로 로드
                SAVE_PATH = settings.get('SAVE_PATH', None)
                
                # 차트 프로그램 설정 로드
                CHART_PROGRAM = settings.get('CHART_PROGRAM', CHART_PROGRAM)

                # EXTEND_BUTTON 문자열을 실제 Button 객체로 변환
                extend_button_str = settings.get('EXTEND_BUTTON', 'left')
                
                # EXTEND_BUTTON 문자열을 실제 Button 객체로 변환
                extend_button_str = settings.get('EXTEND_BUTTON', 'left')
                if extend_button_str == 'left':
                    EXTEND_BUTTON = mouse.Button.left
                elif extend_button_str == 'right':
                    EXTEND_BUTTON = mouse.Button.right
                else:
                    EXTEND_BUTTON = mouse.Button.middle
                
                # 약관 동의 여부 로드
                TERMS_ACCEPTED = settings.get('TERMS_ACCEPTED', False)
                TERMS_VERSION = settings.get('TERMS_VERSION', TERMS_VERSION)
                                                
                logging.info("설정 파일을 성공적으로 로드했습니다.")
                return True
    except Exception as e:
        logging.error(f"설정 로드 중 오류 발생: {e}")
    
    return False

def save_settings():
    """현재 사용자 설정을 파일에 저장합니다."""
    global PRESS_THRESHOLD, TARGET_BUTTON, MAX_RECORDING_DURATION, MODEL_MODE
    global DENTWEB_RECORDING_ENABLED, ALLOWED_LANGUAGES, input_device_index
    global SEPARATE_EXTEND_BUTTON, EXTEND_BUTTON, EXTEND_THRESHOLD
    global TERMS_ACCEPTED, TERMS_VERSION, SAVE_PATH  # SAVE_PATH 추가
    global DENTWEB_CHART_UPLOAD_ENABLED  # 차트 업로드 기능 추가
    global UPLOAD_FILES_TO_DENTWEB  # 파일 업로드 기능 추가
    global CHART_PROGRAM  # 차트 프로그램 설정 추가
    global SHOW_NOTIFICATION_OVERLAY  # 알림 UI 표시 기능 추가
    global SUMMARY_LENGTH_SETTING  # 요약 길이 설정 추가
    global DELETE_ORIGINAL_AUDIO_ENABLED  # 원본 음성 파일 삭제 옵션 추가

    # %APPDATA% 폴더 내에 dNote 폴더와 설정 파일 경로 설정
    app_data_dir = os.getenv('APPDATA')
    if not app_data_dir:
        app_data_dir = os.path.expanduser('~')  # 폴백으로 홈 디렉토리 사용
        
    settings_dir = os.path.join(app_data_dir, 'dNote')
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir)
        
    settings_file = os.path.join(settings_dir, 'dNote_settings.json')
    
    try:
        # TARGET_BUTTON 객체를 문자열로 변환
        target_button_str = 'middle'
        if TARGET_BUTTON == mouse.Button.left:
            target_button_str = 'left'
        elif TARGET_BUTTON == mouse.Button.right:
            target_button_str = 'right'
            
        # EXTEND_BUTTON 객체를 문자열로 변환
        extend_button_str = 'left'
        if EXTEND_BUTTON == mouse.Button.left:
            extend_button_str = 'left'
        elif EXTEND_BUTTON == mouse.Button.right:
            extend_button_str = 'right'
        elif EXTEND_BUTTON == mouse.Button.middle:
            extend_button_str = 'middle'
        
        settings = {
            'PRESS_THRESHOLD': PRESS_THRESHOLD,
            'TARGET_BUTTON': target_button_str,
            'MAX_RECORDING_DURATION': MAX_RECORDING_DURATION,
            'MODEL_MODE': MODEL_MODE,
            'DENTWEB_RECORDING_ENABLED': DENTWEB_RECORDING_ENABLED,
            'DENTWEB_CHART_UPLOAD_ENABLED': DENTWEB_CHART_UPLOAD_ENABLED,
            'UPLOAD_FILES_TO_DENTWEB': UPLOAD_FILES_TO_DENTWEB,
            'SHOW_NOTIFICATION_OVERLAY': SHOW_NOTIFICATION_OVERLAY,
            'WATCH_FOLDER_PATH': WATCH_FOLDER_PATH,
            'WATCH_FOLDER_ENABLED': WATCH_FOLDER_ENABLED,
            'SUMMARY_LENGTH_SETTING': SUMMARY_LENGTH_SETTING,
            'DELETE_ORIGINAL_AUDIO_ENABLED': DELETE_ORIGINAL_AUDIO_ENABLED,
            'ALLOWED_LANGUAGES': ALLOWED_LANGUAGES,
            'input_device_index': input_device_index,
            'SEPARATE_EXTEND_BUTTON': SEPARATE_EXTEND_BUTTON,
            'EXTEND_BUTTON': extend_button_str,
            'EXTEND_THRESHOLD': EXTEND_THRESHOLD,
            'TERMS_ACCEPTED': TERMS_ACCEPTED,  # 약관 동의 여부 저장
            'TERMS_VERSION': TERMS_VERSION,    # 약관 버전 저장
            'SAVE_PATH': SAVE_PATH,            # 저장 경로 추가
            'CHART_PROGRAM': CHART_PROGRAM     # 차트 프로그램 설정 저장
        }
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
            
        logging.info("설정이 성공적으로 저장되었습니다.")
        return True
    except Exception as e:
        logging.error(f"설정 저장 중 오류 발생: {e}")
        return False
    
def register_startup_task():
    """
    Windows 작업 스케줄러에 dNote 프로그램을 등록하여 시스템 시작 시 자동으로 실행되도록 합니다.
    UAC 확인 없이 관리자 권한으로 실행됩니다.
    """
    import os
    import sys
    
    try:
        # 실행 파일 경로 가져오기 (현재 실행 중인 exe 파일)
        exe_path = os.path.abspath(sys.executable)
        
        # 작업 이름
        task_name = "dNote_AutoStart"
        
        # XML 파일 생성 경로
        xml_path = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'dNote_task.xml')
        
        # XML 내용 생성 (작업 스케줄러 작업 정의)
        xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>dNote 자동 시작 작업</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{exe_path}"</Command>
    </Exec>
  </Actions>
</Task>"""
        
        # XML 파일 저장
        with open(xml_path, 'w', encoding='utf-16') as f:
            f.write(xml_content)
        
        # 기존 작업 제거 (있으면)
        subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                      shell=True, check=False)
        
        # 새 작업 등록
        result = subprocess.run(
            ["schtasks", "/create", "/xml", xml_path, "/tn", task_name], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            shell=True, text=True
        )
        
        # 등록 결과 확인
        if result.returncode == 0:
            print(f"작업 '{task_name}'가 성공적으로 등록되었습니다.")
            return True
        else:
            print(f"작업 등록 실패: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"작업 등록 중 오류 발생: {str(e)}")
        return False
    finally:
        # 임시 XML 파일 삭제
        try:
            if os.path.exists(xml_path):
                os.remove(xml_path)
        except:
            pass

def custom_askstring(title, prompt):
    """customtkinter를 사용한 문자열 입력 대화상자"""
    result = [None]  # 결과값을 저장할 리스트
    
    dialog = ctk.CTkToplevel()
    dialog.title(title)
    dialog.geometry("400x180")
    dialog.resizable(False, False)
    dialog.transient(overlay if overlay else None)  # 부모 창 설정
    dialog.grab_set()  # 모달 대화상자로 설정
    
    # 화면 중앙에 위치
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    # 프롬프트 텍스트
    prompt_label = ctk.CTkLabel(dialog, text=prompt, font=("Malgun Gothic", 14))
    prompt_label.pack(pady=(20, 10))
    
    # 입력 필드
    entry = ctk.CTkEntry(dialog, width=300, font=("Malgun Gothic", 13))
    entry.pack(pady=10)
    entry.focus_set()  # 포커스 설정
    
    # 버튼 프레임
    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    button_frame.pack(pady=15)
    
    def on_ok():
        result[0] = entry.get()
        dialog.destroy()
    
    def on_cancel():
        dialog.destroy()
    
    # 확인 및 취소 버튼
    ok_button = ctk.CTkButton(button_frame, text="확인", width=100, 
                              command=on_ok, font=("Malgun Gothic", 12))
    ok_button.grid(row=0, column=0, padx=10)
    
    cancel_button = ctk.CTkButton(button_frame, text="취소", width=100, 
                                 command=on_cancel, font=("Malgun Gothic", 12))
    cancel_button.grid(row=0, column=1, padx=10)
    
    # Enter 키와 Escape 키 바인딩
    dialog.bind("<Return>", lambda event: on_ok())
    dialog.bind("<Escape>", lambda event: on_cancel())
    
    # 대화상자가 닫힐 때까지 대기
    dialog.wait_window()
    
    return result[0]

# 약관 동의 창 함수 추가
def show_terms_agreement():
    from terms_agreement import show_terms_agreement_dialog
    return show_terms_agreement_dialog(resource_path)

# 로깅 설정은 이미 setup_logging()에서 수행됨
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )

# 중복 실행 방지
mutex = prevent_multiple_instances()

loop = asyncio.new_event_loop()

# 전역 변수
cpName = None
record_button_location = None
driver = None

# --- "녹음 상태" 오버레이 관련 전역 ---
rid = 0 # 녹음 ID
safety_task = None  # 안전장치 Task 관리
overlay = None
button_overlay = None  # 버튼 오버레이 전역 변수
overlay_running = False
recording = False
recording_handle_overlay = None  # 녹음 핸들바 오버레이
dictation_handle_overlay = None  # 받아쓰기 핸들바 오버레이
# 일시정지 관련 전역 변수 추가
recording_paused = False  # 녹음 일시정지 상태
pause_start_time = None   # 일시정지 시작 시간
total_paused_time = 0     # 총 일시정지된 시간 (초)
paused_audio_data = []    # 일시정지 중 임시 저장된 오디오 데이터

# 환자 이름 관련 전역 변수 추가
patient_names_list = []  # 녹음 중 감지된 환자 이름 목록
original_patient_name = None  # 녹음 시작 시 최초 환자 이름
patient_name_update_interval = 10  # 환자 이름 업데이트 간격 (초)
patient_name_monitor_task = None  # 환자 이름 모니터링 태스크

recording_timer_task = None  # 현재 실행 중인 녹음 타이머 태스크 저장
listener = None
listener_active = False  # 마우스 리스너 활성화 상태
mic_detected = False  # 마이크 감지 여부
guard_lock = threading.Lock()
uploading = False
upload_queue = Queue()

press_start_time = None # 버튼 눌림 시작 시간

# 서버주소 (라이선스)
servers = [
    "https://license-dnote.imovement.co.kr",
    # "k9av8u8shp.imm.kro.kr:28212",
]

# 약관 동의 관련 전역 변수
TERMS_ACCEPTED = False  # 약관 동의 여부
TERMS_VERSION = "1.0"   # 약관 버전 (향후 약관 변경시 업데이트 가능)
SHORTCUT_CREATED = False  # 바탕화면 바로가기 생성 여부

# 설정 가능한 변수
IMMEDIATE_THRESHOLD = 0.1  # 즉시 녹음 시작 임계값. PRESS_THRESHOLD가 IMMEDIATE_THRESHOLD보다 작으면 즉시 녹음 시작. (초)
PRESS_THRESHOLD_MIDDLE = 2.6  # 마우스 휠 버튼 눌림 지속 시간 임계값. (초)
PRESS_THRESHOLD = 0.32  # 타겟버튼 눌림 지속 시간 임계값 (초)
TARGET_BUTTON = mouse.Button.middle  # 트리거 버튼 (마우스 휠 버튼)
SEPARATE_EXTEND_BUTTON = True  # 녹음 연장 버튼을 분리할지 여부
EXTEND_BUTTON = mouse.Button.right  # 녹음 연장용 버튼 (기본값: 왼쪽 버튼)
EXTEND_THRESHOLD = 1.6  # 녹음 연장 버튼 눌림 지속 시간 임계값 (초)
extend_press_start_time = None  # 연장 버튼 눌림 시작 시간
extend_threshold_timer = None  # 연장 버튼 타이머
extend_threshold_executed = False  # 연장 버튼 실행 여부
input_device_index = None
wheel_press_start_time = None
wheel_threshold_timer = None
wheel_threshold_executed = False
target_button_active = False  # TARGET_BUTTON 처리 활성화 상태
wheel_button_active = False   # 휠 버튼 처리 활성화 상태
target_extend_timer = None  # TARGET_BUTTON 연장 타이머

# 녹음 관련 설정
SAMPLE_RATE = 32000  # 샘플링레이트 (Hz)
CHANNELS = 1 # 채널 수
SAVE_PATH = "C:\\Temp\\DenNote_Records"  # 파일 저장 폴더
default_folder = "C:\\Temp\\DenNote_Records"  # 파일 저장 폴더
subfolder = None  # 하위 폴더 (환자명+날짜)

# 오디오 처리 관련 설정
AUDIO_PROCESSING_ENABLED = True  # 오디오 처리 기능 활성화 여부
AUDIO_TARGET_DB = 0         # 목표 볼륨 레벨 (dB)

# 음성 처리 언어 (한국어, 영어)
ALLOWED_LANGUAGES = ['korean', 'english']

# 시간 관련
MAX_RECORDING_TIME = 3000  # 시스템상 최대 녹음 시간 (초 단위)
MAX_RECORDING_DURATION = 600  # 사용자의 녹음 최대 지속 시간 설정 (초 단위, 10분 = 600초)
SET_RECORDING_DURATION = 0 # 실제 녹음 시간 (변경안됨)
RECORDING_EXTENSION_TIME = 300  # 녹음 종료 후 추가 시간 (초 단위)
overlay_total_time = None  # 오버레이에서 사용하는 총 시간 변수
PROGRESSBAR_ANIMATION_DURATION = 1000  # 프로그레스바 애니메이션 지속 시간 (밀리초 단위)

# 덴트웹 자체 녹음 기능 On/Off
DENTWEB_RECORDING_ENABLED = False

# 덴트웹 차트 업로드 기능 On/Off (실험실 기능)
DENTWEB_CHART_UPLOAD_ENABLED = True

# 덴트웹에 본문(파일) 업로드 기능 On/Off (실험실 기능)
UPLOAD_FILES_TO_DENTWEB = False

# 알림 UI 표시 기능 On/Off (실험실 기능)
SHOW_NOTIFICATION_OVERLAY = True

# 차트 프로그램 설정
CHART_PROGRAM = "dentweb"  # 기본값: 덴트웹

# 파일 감시 기능 설정
WATCH_FOLDER_PATH = None        # 감시할 폴더 경로
WATCH_FOLDER_ENABLED = False    # 파일 감시 활성화 여부

# 요약 길이 설정
SUMMARY_LENGTH_SETTING = "짧게"  # "짧게"(120자), "중간"(180자), "길게"(240자)

# STT 변환 성공 시 원본 음성 파일 삭제 옵션 설정
DELETE_ORIGINAL_AUDIO_ENABLED = True

# Tkinter 메인 root 윈도우 생성, 숨기기
root = tk.Tk()
root.withdraw()

# 사용자 정보
USER_NAME = ""
USER_EMAIL = ""
EXP_AT = None  # 만료일
REMAINING_CREDITS = 0
IS_ACTIVE = False

# 평가판 관련 전역 변수
USE_TRIAL_MODE = False
TRIAL_INFO = None

# 오디오 데이터 저장할 전역변수
audio_data_cache = {}

# 크레딧 사용 모드 (standard, premium)
MODEL_MODE = "premium"  # 기본값
STANDARD_PRICE = 10
PREMIUM_PRICE = 15

## 메모장 포커스 상태
focused_on_notepad = False
monitoring_thread = None

# 설정 로드
load_settings()

MODEL_MODE = "premium"  # 기본값
UPLOAD_FILES_TO_DENTWEB = False

# DPI 스케일링 관련 변수 및 함수
_dpi_scale_cache = None

def get_system_dpi_scale():
    """
    현재 시스템의 DPI 배율을 감지합니다.
    성능 최적화를 위해 첫 번째 호출 후 결과를 캐시합니다.
    
    Returns:
        float: DPI 배율 (1.0 = 100%, 1.25 = 125%, 1.5 = 150% 등)
    """
    global _dpi_scale_cache
    
    # 캐시된 값이 있으면 반환
    if _dpi_scale_cache is not None:
        return _dpi_scale_cache
    
    try:
        # Windows DPI 감지를 위한 API 호출
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        
        # 주 모니터의 DPI 가져오기
        hdc = user32.GetDC(0)
        dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        user32.ReleaseDC(0, hdc)
        
        # DPI를 배율로 변환 (96 DPI = 100%)
        scale_ratio = dpi_x / 96.0
        
        # 캐시에 저장
        _dpi_scale_cache = scale_ratio
        
        logging.info(f"DPI 감지 완료 - DPI: {dpi_x}, 배율: {scale_ratio:.2f}")
        return scale_ratio
        
    except Exception as e:
        logging.warning(f"DPI 배율 감지 실패: {e}. 기본값 1.0 사용")
        _dpi_scale_cache = 1.0
        return 1.0

def scale_px(pixel_value):
    """픽셀 값에 DPI 배율을 적용합니다."""
    return int(pixel_value * get_system_dpi_scale())

# 차트 프로그램 매니저 초기화
try:
    if set_chart_program(CHART_PROGRAM):
        logging.info(f"차트 프로그램 설정 완료: {CHART_PROGRAM}")
    else:
        # 설정된 차트 프로그램이 유효하지 않으면 자동 감지 시도
        detected_program = auto_detect_chart_program()
        if detected_program:
            CHART_PROGRAM = detected_program
            set_chart_program(CHART_PROGRAM)
            logging.info(f"차트 프로그램 자동 감지 및 설정: {CHART_PROGRAM}")
        else:
            # 자동 감지도 실패하면 수동 입력 모드로 설정
            CHART_PROGRAM = "manual"
            set_chart_program(CHART_PROGRAM)
            logging.info("차트 프로그램을 수동 입력 모드로 설정")
except Exception as e:
    logging.error(f"차트 프로그램 초기화 중 오류: {e}")
    CHART_PROGRAM = "manual"
    set_chart_program(CHART_PROGRAM)

PRESS_THRESHOLD = 0.3  # 타겟버튼 눌림 지속 시간 임계값 (초)
EXTEND_BUTTON = mouse.Button.right
EXTEND_THRESHOLD = 1.3

def Model_Price():
    if MODEL_MODE == "standard":
        return STANDARD_PRICE
    elif MODEL_MODE == "premium":
        return PREMIUM_PRICE
    else:
        return PREMIUM_PRICE

# PyInstaller 리소스 경로 처리 함수
def resource_path(relative_path):
    """PyInstaller 환경에서 리소스 파일 경로를 반환"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller로 패키징된 경우
        base_path = sys._MEIPASS
    else:
        # 개발 환경 (스크립트 실행)
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# def show_loading_screen():
#     """
#     프로그램 실행 시 로딩 화면을 중앙에 표시합니다.
#     """
#     global root
#     loading_screen = tk.Toplevel(root)
#     loading_screen.title("로딩 중")
#     loading_screen.overrideredirect(True)  # 창 테두리 제거
#     loading_screen.attributes("-topmost", True)  # 항상 위에 표시

#     # 화면 중앙에 표시하기 위한 위치 계산
#     screen_width = loading_screen.winfo_screenwidth()
#     screen_height = loading_screen.winfo_screenheight()
#     window_width = 320  # 창 너비
#     window_height = 240  # 창 높이
#     x_coord = (screen_width // 2) - (window_width // 2)
#     y_coord = (screen_height // 2) - (window_height // 2)

#     loading_screen.geometry(f"{window_width}x{window_height}+{x_coord}+{y_coord}")

#     # 중앙에 로딩 이미지 표시
#     try:
#         img = tk.PhotoImage(file=resource_path(f"src\\img\\app\\loading_image.png"))
#         label = tk.Label(loading_screen, image=img)
#         label.img = img  # 참조 유지
#     except:
#         # 이미지가 없을 경우 기본 텍스트 표시
#         label = tk.Label(loading_screen, text="로딩 중...", font=("Helvetica", 16))
#     label.pack(expand=True, fill="both")

#     return loading_screen

# # 로딩 화면 표시
# try:
#     loading_screen = show_loading_screen()
#     root.update()
# except Exception as e:
#     logging.error(f"로딩 화면 표시 중 오류 발생: {e}")

# 평가판 클라이언트 클래스 추가
class DentalTrialClient:
    def __init__(self):
        self.base_url = "https://trial-dnote.imovement.co.kr"  # 기본 서버
        self.backup_url = "https://trial-dnote.imovement.co.kr"  # 백업 서버
        self.session_id = str(uuid.uuid4())
        self.trial_info = None
        
    def check_trial(self, dental_name=None):
        """평가판 등록 또는 확인"""
        try:
            # 기본 서버 시도
            try:
                response = requests.post(
                    f"{self.base_url}/api/trial/check",
                    json={"dental_name": dental_name},
                    timeout=10
                )
                if response.status_code == 200:
                    self.trial_info = response.json()
                    return self.trial_info
            except:
                # 백업 서버 시도
                response = requests.post(
                    f"{self.backup_url}/api/trial/check",
                    json={"dental_name": dental_name},
                    timeout=10
                )
                if response.status_code == 200:
                    self.trial_info = response.json()
                    return self.trial_info
                
            logging.error(f"평가판 확인 오류: {response.status_code}")
            return None
        except Exception as e:
            logging.error(f"평가판 확인 중 오류 발생: {str(e)}")
            return None

    def get_trial_status(self, max_retries=4, retry_delay=10):
        """평가판 상태 확인 (재시도 메커니즘 추가)"""
        retry_count = 0
        overlay_win = None
        update_message = None
        destroy_overlay = None
        
        try:
            # 오버레이 창 표시
            overlay_win, update_message, destroy_overlay = create_task_overlay("사용자 정보 불러오는 중...")
            
            while retry_count <= max_retries:
                try:
                    # 기본 서버 시도
                    try:
                        update_message(f"dNote 서버와 통신 중입니다... ({retry_count+1}/{max_retries+1})")
                        response = requests.get(f"{self.base_url}/api/trial/status", timeout=10)
                        if response.status_code == 200:
                            self.trial_info = response.json()
                            # 성공 시 캐시 저장
                            self.save_trial_info_cache()
                            if destroy_overlay:
                                destroy_overlay()
                            return self.trial_info
                    except:
                        # 백업 서버 시도
                        update_message(f"백업 서버와 통신 중입니다... ({retry_count+1}/{max_retries+1})")
                        response = requests.get(f"{self.backup_url}/api/trial/status", timeout=10)
                        if response.status_code == 200:
                            self.trial_info = response.json()
                            # 성공 시 캐시 저장
                            self.save_trial_info_cache()
                            if destroy_overlay:
                                destroy_overlay()
                            return self.trial_info
                    
                    # 모든 서버 연결 실패
                    retry_count += 1
                    if retry_count <= max_retries:
                        update_message(f"서버 연결 실패. {retry_delay}초 후 재시도할게요 ({retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                    
                except Exception as e:
                    logging.error(f"상태 확인 중 오류 발생: {str(e)}")
                    retry_count += 1
                    if retry_count <= max_retries:
                        update_message(f"서버 연결 실패. {retry_delay}초 후 재시도할게요 ({retry_count}/{max_retries})")
                        time.sleep(retry_delay)
            
            # 최대 재시도 횟수 초과 시 사용자에게 선택권 제공
            if destroy_overlay:
                destroy_overlay()
            
            # 백그라운드 재시도 여부
            background_retry = [False]
            background_thread = [None]
            
            # 10초 타이머 후 자동으로 재시도하는 기능
            def auto_retry():
                dialog.destroy()
                background_retry[0] = True
            
            # 메시지 박스 생성
            dialog = ctk.CTkToplevel()
            dialog.title("서버 연결 실패")
            dialog.geometry("400x300")
            dialog.resizable(False, False)
            dialog.attributes("-topmost", True)
            
            # 화면 중앙에 위치
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")
            
            # 경고 아이콘 및 메시지
            icon_label = ctk.CTkLabel(dialog, text="⚠", font=("Malgun Gothic", 36))
            icon_label.pack(pady=(20, 5))
            
            msg_label = ctk.CTkLabel(dialog, text="dNote 서버와 연결할 수 없습니다.\n계속 시도하시겠습니까?", 
                                    font=("Malgun Gothic", 14))
            msg_label.pack(pady=10)
            
            # 자동 재시도 카운트다운 레이블
            countdown_label = ctk.CTkLabel(dialog, text="10초 후 자동으로 재시도합니다...", 
                                        font=("Malgun Gothic", 12))
            countdown_label.pack(pady=5)
            
            # 버튼 프레임
            button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            button_frame.pack(pady=15)
            
            # 1시간 동안 백그라운드에서 재시도하는 함수
            def background_retry_func():
                bg_overlay_win = None
                bg_update_message = None
                bg_destroy_overlay = None
                
                try:
                    # 백그라운드 재시도 오버레이 생성
                    bg_overlay_win, bg_update_message, bg_destroy_overlay = create_task_overlay("서버 연결 재시도 중...")
                    
                    start_time = time.time()
                    end_time = start_time + 3600  # 1시간 (3600초)
                    retry_interval = 30  # 30초마다 재시도
                    
                    while time.time() < end_time:
                        try:
                            # 남은 시간 계산 (분:초)
                            remaining = int(end_time - time.time())
                            mins = remaining // 60
                            secs = remaining % 60
                            
                            # 기본 서버 시도
                            bg_update_message(f"서버 연결 재시도 중... (남은 시간: {mins:02d}:{secs:02d})")
                            
                            response = requests.get(f"{self.base_url}/api/trial/status", timeout=10)
                            if response.status_code == 200:
                                self.trial_info = response.json()
                                self.save_trial_info_cache()
                                if bg_destroy_overlay:
                                    bg_destroy_overlay()
                                
                                # 연결 성공 알림
                                asyncio.run_coroutine_threadsafe(
                                    show_notification_overlay("서버 연결 성공! 사용자 정보를 불러왔습니다.", duration=3),
                                    loop
                                )
                                return self.trial_info
                        except:
                            try:
                                # 백업 서버 시도
                                bg_update_message(f"백업 서버 연결 재시도 중... (남은 시간: {mins:02d}:{secs:02d})")
                                
                                response = requests.get(f"{self.backup_url}/api/trial/status", timeout=10)
                                if response.status_code == 200:
                                    self.trial_info = response.json()
                                    self.save_trial_info_cache()
                                    if bg_destroy_overlay:
                                        bg_destroy_overlay()
                                    
                                    # 연결 성공 알림
                                    asyncio.run_coroutine_threadsafe(
                                        show_notification_overlay("서버 연결 성공! 사용자 정보를 불러왔습니다.", duration=3),
                                        loop
                                    )
                                    return self.trial_info
                            except Exception as e:
                                logging.error(f"백그라운드 재시도 중 오류: {str(e)}")
                        
                        # 일정 시간 대기
                        time.sleep(retry_interval)
                    
                    # 1시간 후 캐시된 정보 확인
                    if bg_destroy_overlay:
                        bg_destroy_overlay()
                    
                    cached_info = self.load_cached_trial_info()
                    if cached_info:
                        # 이전 캐시 정보로 진행
                        asyncio.run_coroutine_threadsafe(
                            show_notification_overlay("서버 연결 실패. 캐시된 정보로 계속합니다.", duration=3),
                            loop
                        )
                        return cached_info
                    else:
                        # 제한된 오프라인 정보 제공
                        asyncio.run_coroutine_threadsafe(
                            show_notification_overlay("서버 연결 실패. 제한된 기능으로 실행합니다.", duration=3),
                            loop
                        )
                        return {"status": "limited", "is_active": True, 
                                "dental_name": "오프라인 사용자", 
                                "remaining_credits": 5}
                except Exception as e:
                    logging.error(f"백그라운드 재시도 프로세스 오류: {str(e)}")
                    if bg_destroy_overlay:
                        bg_destroy_overlay()
                    return {"status": "error", "is_active": True, 
                            "dental_name": "오류 발생", 
                            "remaining_credits": 1}
            
            # 버튼 클릭 핸들러
            def on_continue():
                dialog.destroy()
                background_retry[0] = True
            
            def on_exit():
                dialog.destroy()
                # 프로그램 종료
                sys.exit(0)
            
            # 버튼 생성
            continue_btn = ctk.CTkButton(button_frame, text="계속 시도", width=120, 
                                        command=on_continue, font=("Malgun Gothic", 13))
            continue_btn.grid(row=0, column=0, padx=10)
            
            exit_btn = ctk.CTkButton(button_frame, text="종료", width=120, 
                                command=on_exit, font=("Malgun Gothic", 13))
            exit_btn.grid(row=0, column=1, padx=10)
            
            # 10초 카운트다운 시작
            remain_time = 10
            
            def update_countdown():
                nonlocal remain_time
                if remain_time > 0:
                    countdown_label.configure(text=f"{remain_time}초 후 자동으로 재시도합니다...")
                    remain_time -= 1
                    dialog.after(1000, update_countdown)
                else:
                    auto_retry()
            
            update_countdown()
            
            # 대화상자가 닫힐 때까지 대기
            dialog.wait_window()
            
            # 백그라운드 재시도 선택 시
            if background_retry[0]:
                # 캐시된 정보 먼저 확인
                cached_info = self.load_cached_trial_info()
                
                # 백그라운드 스레드 시작
                background_thread[0] = threading.Thread(target=background_retry_func, daemon=True)
                background_thread[0].start()
                
                # 캐시된 정보가 있으면 즉시 반환하고 백그라운드에서 계속 시도
                if cached_info:
                    return cached_info
                
                # 캐시된 정보가 없으면 최소한의 기능을 위한 정보 제공
                return {"status": "reconnecting", "is_active": True, 
                        "dental_name": "네트워크 재연결 중", 
                        "remaining_credits": 5}
            
            return None
            
        except Exception as e:
            logging.error(f"상태 확인 프로세스 중 치명적 오류: {str(e)}")
            if destroy_overlay:
                destroy_overlay()
            # 치명적 오류 발생 시 사용자에게 알림
            ctk.CTkMessagebox(
                title="오류 발생",
                message=f"서버 연결 중 오류가 발생했습니다:\n{str(e)}\n프로그램을 종료합니다.",
                icon="error"
            )
            sys.exit(1)
    
    def load_cached_trial_info(self):
        """캐시된 평가판 정보 로드"""
        try:
            cache_path = os.path.join(os.getenv('APPDATA'), 'dNote', 'trial_cache.json')
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_info = json.load(f)
                    # 캐시 유효성 검사 (예: 24시간 이내 저장된 캐시만 유효)
                    cached_time = cached_info.get('cached_time', 0)
                    if time.time() - cached_time < 86400:  # 24시간
                        return cached_info
        except Exception as e:
            logging.error(f"캐시된 정보 로드 중 오류: {str(e)}")
        return None

    def save_trial_info_cache(self):
        """평가판 정보 캐싱"""
        if self.trial_info:
            try:
                cache_dir = os.path.join(os.getenv('APPDATA'), 'dNote')
                os.makedirs(cache_dir, exist_ok=True)
                cache_path = os.path.join(cache_dir, 'trial_cache.json')
                
                # 현재 시간 추가
                cache_data = self.trial_info.copy()
                cache_data['cached_time'] = time.time()
                
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logging.error(f"평가판 정보 캐싱 중 오류: {str(e)}")

def preload_audio_files():
    """
    프로그램 시작 시 오디오 파일을 미리 메모리에 로드합니다.
    """
    global audio_data_cache
    
    try:
        audio_files = {
            'AP_Engage': 'src\\sounds\\AP_Engage.mp3',
            'AP_Disengage': 'src\\sounds\\AP_Disengage.mp3',
            'NoA_Engage': 'src\\sounds\\NoA_Engage.mp3',
            'rec_start_voice': 'src\\sounds\\rec_start_voice.mp3',
            'rec_stop_voice': 'src\\sounds\\rec_stop_voice.mp3'
        }
        
        for key, file_path in audio_files.items():
            resolved_path = resource_path(file_path)
            data, fs = sf.read(resolved_path)
            # 모노 채널인 경우 처리
            if len(data.shape) == 1:
                data = np.column_stack((data, data))
            
            audio_data_cache[key] = {
                'data': data,
                'fs': fs
            }
        
        print("오디오 파일 로드 완료")
    except Exception as e:
        print(f"오디오 파일 로드 중 오류: {e}")

# --- 오디오 처리 기능 ---
def process_audio(audio_data, sr=16000, target_db=-3):
    """
    오디오 데이터를 처리하여 품질을 개선합니다.
    
    Args:
        audio_data: 오디오 데이터 (numpy 배열)
        sr: 샘플링 레이트
        target_db: 목표 데시벨 레벨 (정규화에 사용)
        high_pass_cutoff: 사용하지 않음 (이전 버전과의 호환성을 위해 유지)
        low_pass_cutoff: 사용하지 않음 (이전 버전과의 호환성을 위해 유지)
        
    Returns:
        처리된 오디오 데이터
    """
    try:
        # 1차원 배열로 변환
        if audio_data.ndim > 1:
            audio_data = audio_data.flatten()
        
        # 1. 노이즈 게이트 (아주 작은 소리는 제거)
        noise_gate_threshold = 0.0005
        is_signal = np.abs(audio_data) > noise_gate_threshold
        if np.sum(is_signal) > 0:  # 신호가 있을 경우에만 처리
            # 2. 볼륨 정규화만 적용 (주파수 필터링 제거)
            audio_normalized = normalize_audio(audio_data, target_db=target_db)
            return audio_normalized
        else:
            return audio_data  # 신호가 없는 경우 원본 반환
    except Exception as e:
        logging.error(f"오디오 처리 중 오류: {e}")
        return audio_data  # 오류 발생 시 원본 반환

def normalize_audio(audio_data, target_db=-3):
    """
    RMS 기반으로 오디오의 볼륨을 정규화하여 목표 데시벨로 조정합니다.
    
    Args:
        audio_data: 오디오 데이터 (numpy 배열)
        target_db: 목표 데시벨 레벨
        
    Returns:
        정규화된 오디오 데이터
    """
    # 무음인 경우 처리
    if np.all(np.abs(audio_data) < 1e-10):
        return audio_data
    
    # RMS 값 계산
    rms = np.sqrt(np.mean(np.square(audio_data)))
    
    # 현재 RMS dB 계산 (참조 레벨은 1.0)
    current_db = 20 * np.log10(rms)
    
    # 목표 dB와의 차이 계산
    db_change = target_db - current_db
    
    # 증폭 비율 계산
    gain = 10 ** (db_change / 20)
    
    # 오디오 증폭
    normalized_audio = audio_data * gain
    
    # 클리핑 방지: 진폭이 1.0을 넘지 않도록 조정
    if np.max(np.abs(normalized_audio)) > 1.0:
        normalized_audio = normalized_audio / np.max(np.abs(normalized_audio))
    
    return normalized_audio

def prepare_audio_for_recording(audio_key, target_db=-3):
    """
    미리 로드된 오디오 파일을 녹음 설정에 맞게 변환합니다.
    
    Args:
        audio_key: 오디오 파일 키 ('rec_start_voice' 또는 'rec_stop_voice')
        target_db: 목표 데시벨 레벨 (녹음본과 동일하게 정규화)
        
    Returns:
        변환된 오디오 데이터 (numpy 배열, int16 형식, 녹음 데이터와 같은 차원)
    """
    if audio_key not in audio_data_cache:
        logging.error(f"오디오 키 '{audio_key}'를 찾을 수 없습니다.")
        return None
    
    try:
        audio = audio_data_cache[audio_key]
        audio_data = audio['data']
        original_fs = audio['fs']
        
        # 스테레오인 경우 모노로 변환
        if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 1차원으로 만들기 (다중 채널인 경우를 위해)
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()
        
        # 샘플레이트 변환 (필요한 경우)
        if original_fs != SAMPLE_RATE:
            # numpy를 사용한 간단한 선형 보간 리샘플링
            original_length = len(audio_data)
            new_length = int(original_length * SAMPLE_RATE / original_fs)
            
            # 선형 보간을 사용한 리샘플링
            old_indices = np.linspace(0, original_length - 1, original_length)
            new_indices = np.linspace(0, original_length - 1, new_length)
            audio_data = np.interp(new_indices, old_indices, audio_data)
            
            logging.info(f"오디오 샘플레이트 변환: {original_fs}Hz -> {SAMPLE_RATE}Hz")
        
        # 볼륨 정규화 적용 (녹음본과 동일한 레벨로)
        if AUDIO_PROCESSING_ENABLED:
            audio_data = normalize_audio(audio_data, target_db=target_db)
        
        # int16 형식으로 변환 (녹음 데이터와 동일한 형식)
        audio_data_int16 = (audio_data * 32767).astype(np.int16)
        
        # 녹음 데이터와 같은 형태로 변환: (n_frames, 1) 형태로 만들기
        # CHANNELS = 1 (모노)이므로 2차원 배열로 변환
        audio_data_reshaped = audio_data_int16.reshape(-1, 1)
        
        return audio_data_reshaped
        
    except Exception as e:
        logging.error(f"오디오 변환 중 오류 ({audio_key}): {e}")
        return None
        
def play_audio_fast(audio_key):
    """
    미리 로드된 오디오를 빠르게 재생합니다.
    """
    if audio_key not in audio_data_cache:
        print(f"오디오 키 '{audio_key}'를 찾을 수 없습니다.")
        return
    
    def _play_thread():
        try:
            audio = audio_data_cache[audio_key]
            sd.play(audio['data'], audio['fs'])
        except Exception as e:
            print(f"오디오 재생 중 오류: {e}")
    
    # 오디오 재생을 별도 스레드에서 실행
    threading.Thread(target=_play_thread, daemon=True).start()

preload_audio_files()

# def get_free_port():
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         s.bind(("", 0))  # 운영 체제가 사용 가능한 포트를 자동으로 할당
#         return s.getsockname()[1]  # 할당된 포트 반환

def start_loop(loop):
    """Async 이벤트 루프를 별도 스레드에서 실행."""
    asyncio.set_event_loop(loop)
    loop.run_forever()

loop_thread = threading.Thread(target=start_loop, args=(loop,), daemon=True)
loop_thread.start()

def set_recording_duration():
    """
    녹음 최대 지속 시간을 설정합니다.
    """
    global SET_RECORDING_DURATION
    
    model_price = Model_Price()

    if REMAINING_CREDITS < 1:
        SET_RECORDING_DURATION = 0
        print(f"남은 크레딧이 적어 녹음할 수 없습니다. 남은 크레딧: {REMAINING_CREDITS}")
        return False

    if REMAINING_CREDITS < MAX_RECORDING_DURATION / 60 * model_price:
        SET_RECORDING_DURATION = int(REMAINING_CREDITS * 60 / (model_price/10))
        print(f"남은 크레딧: {REMAINING_CREDITS}분 → 녹음 시간: {SET_RECORDING_DURATION}초")
        return True
    else:
        SET_RECORDING_DURATION = MAX_RECORDING_DURATION
        print(f"설정된 녹음 시간: {SET_RECORDING_DURATION}초")
        return True

async def recording_timer():
    """
    녹음 타이머를 실행하여 지정된 시간이 지나면 녹음을 자동으로 종료합니다.
    일시정지 중에는 타이머가 멈추고, 재개 시 남은 시간으로 다시 시작합니다.
    오버레이와 동일한 정확한 시간 계산 방식을 사용합니다.
    """
    global SET_RECORDING_DURATION, recording_paused, pause_start_time, total_paused_time, recording, rid, listener_active, start_time
    
    # 최대 녹음 시간 검증 및 제한
    if SET_RECORDING_DURATION <= 0:
        SET_RECORDING_DURATION = 1200  # 기본 20분
        logging.warning(f"녹음 시간이 올바르게 설정되지 않아 기본값({SET_RECORDING_DURATION}초)으로 설정합니다.")
    elif SET_RECORDING_DURATION > MAX_RECORDING_TIME:
        SET_RECORDING_DURATION = MAX_RECORDING_TIME
        logging.warning(f"녹음 시간이 최대 허용 시간을 초과하여 {MAX_RECORDING_TIME}초로 제한합니다.")
        
    print(f"최대 녹음 시간: {SET_RECORDING_DURATION}초")
    
    try:
        rsvd_rid = rid
        
        while recording and rsvd_rid == rid:
            # 오버레이와 동일한 방식으로 실제 경과 시간 계산
            if recording_paused:
                # 일시정지 상태에서는 시간 계산 중지
                if pause_start_time:
                    effective_elapsed_time = pause_start_time - start_time - total_paused_time
                else:
                    effective_elapsed_time = time.time() - start_time - total_paused_time
            else:
                # 정상 상태에서는 일시정지된 총 시간을 빼고 계산
                effective_elapsed_time = time.time() - start_time - total_paused_time
            
            # 남은 시간 계산
            remaining_time = SET_RECORDING_DURATION - effective_elapsed_time
            
            # 타이머 만료 확인
            if remaining_time <= 0:
                logging.info(f"녹음이 {SET_RECORDING_DURATION}초 동안 유지되어 자동 종료됩니다.")
                await stop_recording()
                break
            
            # 일시정지 상태에 따라 체크 간격 조정
            if recording_paused:
                # 일시정지 중에는 0.2초마다 상태 체크 (더 빠른 반응)
                await asyncio.sleep(0.2)
            else:
                # 정상 상태에서는 0.1초마다 체크하여 정확성 향상
                await asyncio.sleep(0.1)
                
                # 디버깅용 로그 (매 10초마다)
                if effective_elapsed_time > 0 and int(effective_elapsed_time) % 10 == 0 and effective_elapsed_time - 0.1 < int(effective_elapsed_time):
                    logging.debug(f"녹음 타이머: {remaining_time:.1f}초 남음 (경과: {effective_elapsed_time:.1f}초)")
        
        # 녹음이 종료된 경우
        if not recording:
            logging.info("녹음이 이미 종료되어 타이머를 중단합니다.")
        elif rsvd_rid != rid:
            logging.info("새로운 녹음 세션이 시작되어 기존 타이머를 중단합니다.")
            
    except asyncio.CancelledError:
        # 타이머가 취소됨 (녹음 시간 연장 등으로 인해)
        logging.info("녹음 타이머가 취소되었습니다.")
    except Exception as e:
        logging.error(f"녹음 타이머 중 예외 발생: {e}")
        # 예외 발생 시에도 리스너를 활성화하여 사용자가 녹음을 종료할 수 있도록 함
        listener_active = True
        asyncio.create_task(ensure_listener_recovery())

# --- 오버레이 애니메이션 관련 유틸리티 함수 ---
def ease_out_cubic(t):
    """
    큐빅 이징 아웃 함수 - 빠르게 시작하여 부드럽게 감속
    t: 0.0~1.0 사이의 진행도
    """
    return 1 - (1 - t) ** 3

def ease_in_cubic(t):
    """
    큐빅 이징 인 함수 - 천천히 시작하여 빠르게 가속
    t: 0.0~1.0 사이의 진행도
    """
    return t ** 3

def animate_overlay_in(window, start_y, end_y, duration=300):
    """
    오버레이를 위에서 아래로 내려오는 애니메이션
    window: Toplevel 창
    start_y, end_y: 시작/종료 y좌표
    duration: 애니메이션 지속시간 (밀리초)
    """
    start_time = time.time() * 1000  # 밀리초 단위
    geo = window.geometry().split("+")
    width_height = geo[0]
    x_pos = geo[1]
    
    def update_position():
        current_time = time.time() * 1000
        progress = min(1.0, (current_time - start_time) / duration)
        eased_progress = ease_out_cubic(progress)
        current_y = int(start_y + (end_y - start_y) * eased_progress)
        
        window.geometry(f"{width_height}+{x_pos}+{current_y}")
        
        if progress < 1.0:
            window.after(15, update_position)
    
    update_position()

def animate_overlay_out(window, start_y, end_y, duration=700, destroy_after=True):
    """
    오버레이를 위로 올라가게 하는 애니메이션
    destroy_after: True면 애니메이션 후 창 제거
    """
    start_time = time.time() * 1000
    geo = window.geometry().split("+")
    width_height = geo[0]
    x_pos = geo[1]
    
    def update_position():
        if not window.winfo_exists():
            return
            
        current_time = time.time() * 1000
        progress = min(1.0, (current_time - start_time) / duration)
        eased_progress = ease_in_cubic(progress)  # 느리게 시작해서 빠르게 끝나도록 ease_in 적용
        current_y = int(start_y + (end_y - start_y) * eased_progress)
        
        window.geometry(f"{width_height}+{x_pos}+{current_y}")
        
        if progress < 1.0:
            window.after(15, update_position)
        elif destroy_after and window.winfo_exists():
            window.destroy()
    
    update_position()

def create_rounded_bottom_corners(window, radius=5, smooth=True):
    """
    Windows API를 사용하여 창의 하단 모서리를 부드럽게 둥글게 만드는 함수
    
    Args:
        window: tkinter window 객체
        radius: 모서리의 반경 (픽셀)
        smooth: True일 경우 부드러운 모서리를 위한 추가 처리 적용
    """
    try:
        import ctypes
        from ctypes import windll, byref, c_int
        from ctypes.wintypes import HWND, RECT, HRGN, BOOL, COLORREF, HDC, HPEN
        
        # Win32 함수와 상수 정의
        CreateRectRgn = windll.gdi32.CreateRectRgn
        CreateRoundRectRgn = windll.gdi32.CreateRoundRectRgn
        CombineRgn = windll.gdi32.CombineRgn
        SetWindowRgn = windll.user32.SetWindowRgn
        DeleteObject = windll.gdi32.DeleteObject
        
        # 창의 DPI 설정 가져오기 (고해상도 디스플레이 대응)
        try:
            GetDpiForWindow = windll.user32.GetDpiForWindow
            hwnd = HWND(int(window.winfo_id()))
            dpi = GetDpiForWindow(hwnd)
            # DPI에 따라 반경 조정 (기본 96 DPI 기준)
            dpi_scale = dpi / 96.0 if dpi > 0 else 1.0
            radius = int(radius * dpi_scale)
        except (AttributeError, ValueError):
            # Windows 8.1 이하에서는 GetDpiForWindow가 없을 수 있음
            pass
        
        # 창의 크기 가져오기
        width = window.winfo_width()
        height = window.winfo_height()
        
        # 크기가 0이면 지정된 geometry 값 사용
        if width <= 1 or height <= 1:
            geo = window.geometry().split('+')[0].split('x')
            width = int(geo[0])
            height = int(geo[1])
        
        # 창의 핸들 가져오기
        hwnd = HWND(int(window.winfo_id()))
        
        # 리전 조합 모드 상수
        RGN_OR = 2
        
        if smooth and radius > 0:
            # 부드러운 모서리를 위한 다층 리전 생성
            # 주요 리전 생성
            main_region = CreateRoundRectRgn(0, 0, width+1, height+1, radius, radius)
            
            # 상단 직사각형 리전 (각진 부분)
            top_region = CreateRectRgn(0, 0, width+1, height-radius+1)
            
            # 최종 리전 생성 및 합치기
            final_region = CreateRectRgn(0, 0, width+1, height+1)
            CombineRgn(final_region, main_region, top_region, RGN_OR)
            
            # 창에 최종 리전 적용
            # 창에 최종 리전 적용
            result = SetWindowRgn(hwnd, final_region, True)
            
            # 리소스 해제
            DeleteObject(main_region)
            DeleteObject(top_region)
            DeleteObject(final_region)
        else:
            # 기본 둥근 모서리 처리 (이전 코드)
            top_region = CreateRectRgn(0, 0, width+1, height-radius+1)
            bottom_region = CreateRoundRectRgn(0, height-radius*2, width+1, height+1, radius*2, radius*2)
            
            final_region = CreateRectRgn(0, 0, width+1, height+1)
            CombineRgn(final_region, top_region, bottom_region, RGN_OR)
            
            SetWindowRgn(hwnd, final_region, True)
            
            DeleteObject(top_region)
            DeleteObject(bottom_region)
            DeleteObject(final_region)
        
        return True
    except Exception as e:
        print(f"둥근 모서리 창 생성 중 오류 발생: {e}")
        return False

# --- "다운로드/업로드"용 독립 오버레이 수정 ---
def create_task_overlay(initial_message: str):
    """
    다운로드/업로드 진행 상태를 표시하는 오버레이를 생성.
    안티앨리어싱이 적용된 현대적인 로딩 스피너 적용.
    """
    global SHOW_NOTIFICATION_OVERLAY
    
    # 알림 UI 표시가 비활성화된 경우 더미 함수들 반환
    if not SHOW_NOTIFICATION_OVERLAY:
        def dummy_update(message):
            pass
        def dummy_destroy():
            pass
        return None, dummy_update, dummy_destroy
    
    # 오버레이 윈도우
    toplevel_win = tk.Toplevel(root)

    screen_width = toplevel_win.winfo_screenwidth()
    overlay_width = scale_px(360)
    overlay_height = scale_px(23)

    x_position = screen_width - overlay_width - scale_px(360)
    y_final = 0  # 최종 위치 (최상단)
    y_start = -overlay_height - scale_px(10)  # 초기 위치 (화면 밖)

    toplevel_win.geometry(f"{overlay_width}x{overlay_height}+{x_position}+{y_start}")
    toplevel_win.overrideredirect(True)
    toplevel_win.attributes("-topmost", True)

    # 프레임 생성 - 색상 변경
    frame = tk.Frame(toplevel_win, bg='#3c3c3c')
    frame.pack(fill=tk.BOTH, expand=True)

    # 캔버스 생성 - 색상 변경
    canvas = tk.Canvas(frame, width=overlay_width, height=overlay_height,
                   bg='#3c3c3c', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # 스피너 사이즈와 위치 조정
    offset_x = scale_px(6)
    status_circle_x, status_circle_y = scale_px(12) + offset_x, overlay_height // 2
    
    # 안티앨리어싱된 스피너 이미지 생성 함수
    def create_spinner_image(angle, size=scale_px(12)):
        # 이미지 크기를 실제 표시 크기보다 크게 만들어 더 부드럽게 표현
        scale_factor = 4
        img_size = size * scale_factor
        
        # 투명한 이미지 생성
        image = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # 원 중심
        center = img_size // 2
        
        # 외부/내부 반지름 (두께 조정)
        outer_radius = img_size // 2 - 1
        inner_radius = outer_radius - 2 * scale_factor
        
        # 배경 원 그리기 (옅은 회색)
        draw.ellipse((center - outer_radius, center - outer_radius, 
                     center + outer_radius, center + outer_radius), 
                     outline=(180, 180, 180, 100), width=1)

        # 회전하는 호(arc) 그리기
        # PIL에는 직접적인 arc 함수가 없으므로 start와 end 각도 사이의 점들로 그립니다
        arc_length = 120  # 호의 길이(각도)
        start_angle = angle
        end_angle = (angle + arc_length) % 360
        
        # 점들의 집합으로 부드러운 호를 그립니다
        points = []
        steps = 60  # 더 많은 단계 = 더 부드러운 곡선
        
        for i in range(steps + 1):
            # 바깥쪽 점
            current_angle = start_angle + (i / steps) * arc_length
            rad = math.radians(current_angle)
            x = center + outer_radius * math.cos(rad)
            y = center + outer_radius * math.sin(rad)
            points.append((x, y))
        
        # 안쪽 점 (역순)
        for i in range(steps, -1, -1):
            current_angle = start_angle + (i / steps) * arc_length
            rad = math.radians(current_angle)
            x = center + inner_radius * math.cos(rad)
            y = center + inner_radius * math.sin(rad)
            points.append((x, y))
        
        # 폴리곤으로 채우기
        draw.polygon(points, fill=(255, 255, 255, 255))
        
        # 이미지 크기 조정 (원래 표시 크기로)
        image = image.resize((size, size), Image.LANCZOS)
        
        return ImageTk.PhotoImage(image)
    
    # 초기 스피너 이미지 생성
    spinner_image = create_spinner_image(0)
    spinner_item = canvas.create_image(status_circle_x, status_circle_y, image=spinner_image)
    
    # 텍스트 위치 조정
    text_item = canvas.create_text(
        overlay_width // 2 + scale_px(10), overlay_height // 2,
        text=initial_message, fill="white", font=("Malgun Gothic", 10, "bold")
    )

    # 슬라이드 인 애니메이션 시작
    animate_overlay_in(toplevel_win, y_start, y_final)
    
    # Win32 API로 둥근 모서리 적용
    toplevel_win.update_idletasks()
    create_rounded_bottom_corners(toplevel_win)

    start_time = time.time()
    angle = 0
    spinner_frames = []  # 메모리 관리를 위해 이미지 참조 유지
    
    # 회전 애니메이션과 메시지 업데이트를 위한 내부 함수
    def update_message_func(new_message: str):
        elapsed_time = int(time.time() - start_time)
        minutes = elapsed_time // 60
        seconds = elapsed_time % 60
        formatted_time = f"{minutes:02}:{seconds:02}"
        full_text = new_message
        canvas.itemconfig(text_item, text=full_text)

    # 스피너 회전 애니메이션
    def animate_circle():
        nonlocal angle, spinner_image, spinner_frames
        if not toplevel_win.winfo_exists():
            return
        
        # 일정한 속도로 회전
        angle = (angle + 8) % 360
        
        # 새 이미지 생성 및 업데이트
        new_spinner = create_spinner_image(angle)
        spinner_frames.append(new_spinner)  # 참조 유지
        if len(spinner_frames) > 10:  # 메모리 관리: 일정 개수 이상이면 오래된 이미지 참조 제거
            spinner_frames.pop(0)
            
        canvas.itemconfig(spinner_item, image=new_spinner)
        toplevel_win.after(25, animate_circle)

    animate_circle()  # 회전 애니메이션 시작

    # 오버레이 닫기 함수
    def destroy_func():
        if toplevel_win and toplevel_win.winfo_exists():
            # 위로 슬라이드 아웃 애니메이션
            current_geo = toplevel_win.geometry().split("+")
            current_y = int(current_geo[2])
            animate_overlay_out(toplevel_win, current_y, -overlay_height)

    # 초기에 메시지 반영
    update_message_func(initial_message)

    return toplevel_win, update_message_func, destroy_func

async def show_notification_overlay(message, duration=4):
    """
    일정 시간 동안 최상단에 알림 오버레이를 표시 (Toplevel).
    슬라이드 인/아웃 애니메이션 적용.
    """
    global root, SHOW_NOTIFICATION_OVERLAY
    
    # 알림 UI 표시가 비활성화된 경우 바로 반환
    if not SHOW_NOTIFICATION_OVERLAY:
        return
    
    notification_overlay = tk.Toplevel(root)

    screen_width = notification_overlay.winfo_screenwidth()
    overlay_width = scale_px(360)
    overlay_height = scale_px(23)

    # 화면 중앙에 위치하도록 조정
    x_position = screen_width - overlay_width - scale_px(360)
    y_final = 0  # 최종 위치
    y_start = -overlay_height - scale_px(10)  # 시작 위치 (화면 밖)

    notification_overlay.geometry(f"{overlay_width}x{overlay_height}+{x_position}+{y_start}")
    notification_overlay.overrideredirect(True)
    notification_overlay.attributes("-topmost", True)

    # 프레임 생성 - 색상 변경
    frame = tk.Frame(notification_overlay, bg='#3c3c3c')
    frame.pack(fill=tk.BOTH, expand=True)

    # 캔버스 생성 - 색상 변경
    canvas = tk.Canvas(frame, width=overlay_width, height=overlay_height,
                   bg='#3c3c3c', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # 텍스트 추가
    text_id = canvas.create_text(overlay_width//2, overlay_height//2, 
                              text=message, fill="#ffffff", font=("Malgun Gothic", 10, "bold"))
    
    # 슬라이드 인 애니메이션
    animate_overlay_in(notification_overlay, y_start, y_final)
    
    # Win32 API로 둥근 모서리 적용
    notification_overlay.update_idletasks()
    create_rounded_bottom_corners(notification_overlay)
    
    # 지정된 시간 동안 표시
    await asyncio.sleep(duration)
    
    # 슬라이드 아웃 애니메이션
    animate_overlay_out(notification_overlay, y_final, -overlay_height)

async def show_credit_toast_popup(remaining_credits, duration=99999):
    """
    크레딧 부족 시 오른쪽 아래에서 나타나는 예쁜 토스트 팝업
    - 화면 오른쪽 아래에서 slide in/out
    - 충전하기 버튼과 X 버튼 포함
    - 자동 종료 없음 (구매 유도를 위해)
    """
    global root
    
    toast_popup = tk.Toplevel(root)
    
    # 팝업 크기 설정 (조금 더 크게)
    popup_width = scale_px(300)
    popup_height = scale_px(160)
    
    # 화면 크기 가져오기
    screen_width = toast_popup.winfo_screenwidth()
    screen_height = toast_popup.winfo_screenheight()
    
    # 위치 계산 (오른쪽 아래 모서리에서 약간 떨어진 위치)
    margin = scale_px(20)
    x_final = screen_width - popup_width - margin
    y_final = screen_height - popup_height - margin - scale_px(40)  # 작업표시줄 고려
    
    # 시작 위치 (화면 오른쪽 바깥)
    x_start = screen_width + 10
    y_start = y_final
    
    toast_popup.geometry(f"{popup_width}x{popup_height}+{x_start}+{y_start}")
    toast_popup.overrideredirect(True)
    toast_popup.attributes("-topmost", True)
    
    # 메인 프레임 (그라데이션과 그림자 효과)
    main_frame = tk.Frame(toast_popup, bg='#ffffff', relief='flat', bd=0)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
    
    # 그라데이션 효과를 위한 상단 색상 프레임
    gradient_frame = tk.Frame(main_frame, bg='#f8f9ff', height=4)
    gradient_frame.pack(fill=tk.X)
    gradient_frame.pack_propagate(False)
    
    # 헤더 프레임 (제목과 X 버튼) - 간격 줄이기
    header_frame = tk.Frame(main_frame, bg='#ffffff', height=40)
    header_frame.pack(fill=tk.X, padx=18, pady=(18, 8))
    header_frame.pack_propagate(False)
    
    # 경고 아이콘과 제목을 담는 프레임 - 더 타이트하게
    title_content_frame = tk.Frame(header_frame, bg='#ffffff')
    title_content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # 경고 아이콘 (더 큰 이모지와 색상 개선)
    icon_label = tk.Label(title_content_frame, text="⚠", font=("Arial", 16), bg='#ffffff', fg='#ff6b35')
    icon_label.pack(side=tk.LEFT, padx=(0, 6))
    
    # 제목 텍스트 (더 세련된 폰트와 색상)
    title_label = tk.Label(title_content_frame, text="포인트가 거의 소진되었어요", 
                          font=("Malgun Gothic", 12, "bold"), 
                          bg='#ffffff', fg='#2c3e50')
    title_label.pack(side=tk.LEFT, anchor='w')
    
    # X 버튼 (더 세련된 디자인)
    def close_popup():
        # 슬라이드 아웃 애니메이션으로 닫기
        animate_toast_out(toast_popup, x_final, screen_width + 10, duration=800)
    
    # close_button = tk.Button(header_frame, text="✕", font=("Arial", 14, "bold"),
    #                        bg='#ffffff', fg='#bdc3c7', relief='flat', bd=0,
    #                        activebackground='#ecf0f1', activeforeground='#7f8c8d',
    #                        command=close_popup, width=2, height=1,
    #                        cursor='hand2')
    # close_button.pack(side=tk.RIGHT)
    
    # 내용 프레임
    content_frame = tk.Frame(main_frame, bg='#ffffff')
    content_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
    
    # 크레딧 정보 텍스트 (더 세련된 스타일)
    credit_text = f"현재 {remaining_credits:,}포인트가 남아있습니다."
    info_label = tk.Label(content_frame, text=credit_text, 
                         font=("Malgun Gothic", 10), 
                         bg='#ffffff', fg='#5d6d7e',
                         justify='left', wraplength=300)
    info_label.pack(anchor='w', pady=(0, 18))
    
    # 버튼 프레임
    button_frame = tk.Frame(content_frame, bg='#ffffff')
    button_frame.pack(anchor='w')
    
    # 충전하기 버튼 (더 매력적인 디자인)
    def open_charge_website():
        try:
            webbrowser.open("https://i-movement.liveklass.com/classes/249862")
            logging.info("충전하기 버튼 클릭 - 웹사이트 열기")
            close_popup()
        except Exception as e:
            logging.error(f"웹사이트 열기 실패: {e}")
    
    charge_button = tk.Button(button_frame, text="💳 포인트 충전하기", 
                             font=("Malgun Gothic", 10, "bold"),
                             bg='#3498db', fg='white', relief='flat', bd=0,
                             activebackground='#2980b9', activeforeground='white',
                             command=open_charge_website, 
                             width=16, height=2, cursor='hand2')
    charge_button.pack(side=tk.LEFT, padx=(0, 12))
    
    # 나중에 하기 버튼 (더 부드러운 디자인)
    later_button = tk.Button(button_frame, text="나중에 하기", 
                           font=("Malgun Gothic", 10),
                           bg='#ecf0f1', fg='#7f8c8d', relief='flat', bd=0,
                           activebackground='#d5dbdb', activeforeground='#5d6d7e',
                           command=close_popup, 
                           width=12, height=2, cursor='hand2')
    later_button.pack(side=tk.LEFT)
    
    # 팝업 그림자 효과 개선
    toast_popup.configure(bg='#bdc3c7')  # 더 부드러운 그림자 색상
    
    # 슬라이드 인 애니메이션 (조금 더 부드럽게)
    animate_toast_in(toast_popup, x_start, x_final, duration=900)
    
    # 둥근 모서리 적용 (윈도우 API 사용)
    try:
        toast_popup.update_idletasks()
        hwnd = toast_popup.winfo_id()
        # 둥근 모서리 적용
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
        )
    except Exception as e:
        logging.debug(f"둥근 모서리 적용 실패: {e}")
    
    # 지정된 시간 후 자동 닫기 (매우 긴 시간으로 설정하여 실질적으로 비활성화)
    async def auto_close():
        await asyncio.sleep(duration)
        if toast_popup.winfo_exists():
            close_popup()
    
    # 자동 닫기 태스크 시작 (사실상 비활성화됨)
    asyncio.create_task(auto_close())

def animate_toast_in(window, start_x, end_x, duration=900):
    """
    토스트 팝업을 오른쪽에서 왼쪽으로 슬라이드 인 애니메이션
    """
    start_time = time.time() * 1000
    geo = window.geometry().split("+")
    width_height = geo[0]
    y_pos = geo[2]
    
    def update_position():
        if not window.winfo_exists():
            return
            
        current_time = time.time() * 1000
        progress = min(1.0, (current_time - start_time) / duration)
        
        # cubic ease-out 적용
        eased_progress = 1 - (1 - progress) ** 3
        current_x = int(start_x + (end_x - start_x) * eased_progress)
        
        window.geometry(f"{width_height}+{current_x}+{y_pos}")
        
        if progress < 1.0:
            window.after(15, update_position)  # ~60fps
    
    update_position()

def animate_toast_out(window, start_x, end_x, duration=800):
    """
    토스트 팝업을 왼쪽에서 오른쪽으로 슬라이드 아웃 애니메이션
    """
    start_time = time.time() * 1000
    geo = window.geometry().split("+")
    width_height = geo[0]
    y_pos = geo[2]
    
    def update_position():
        if not window.winfo_exists():
            return
            
        current_time = time.time() * 1000
        progress = min(1.0, (current_time - start_time) / duration)
        
        # cubic ease-in 적용
        eased_progress = progress ** 3
        current_x = int(start_x + (end_x - start_x) * eased_progress)
        
        window.geometry(f"{width_height}+{current_x}+{y_pos}")
        
        if progress < 1.0:
            window.after(15, update_position)
        else:
            # 애니메이션 완료 후 창 제거
            if window.winfo_exists():
                window.destroy()
    
    update_position()

# 오버레이 타이머 업데이트 함수 수정
def create_overlay():
    global overlay, overlay_running, root, start_time, overlay_total_time, recording_paused, total_paused_time, button_overlay
    overlay_running = True
    overlay = tk.Toplevel(root)

    start_time = time.time()
    overlay_total_time = SET_RECORDING_DURATION  # 전역 변수 사용

    screen_width = overlay.winfo_screenwidth()
    screen_height = overlay.winfo_screenheight()
    overlay_width = scale_px(150)
    overlay_height = scale_px(23)
    
    # 버튼 관련 설정
    button_width = scale_px(75)  # 버튼 3개 수용을 위해 확장

    # 오버레이는 원래 크기로 유지 (둥근 모서리 문제 해결)
    x_position = screen_width - overlay_width - scale_px(190)
    y_final = 0
    y_start = -overlay_height - scale_px(10)

    overlay.geometry(f"{overlay_width}x{overlay_height}+{x_position}+{y_start}")
    overlay.overrideredirect(True)
    overlay.attributes("-topmost", True)

    # 메인 프레임 생성
    frame = tk.Frame(overlay, bg='#3c3c3c')
    frame.pack(fill=tk.BOTH, expand=True)

    # 메인 캔버스 (타이머 표시용) - 전체 영역 사용
    canvas = tk.Canvas(frame, width=overlay_width, height=overlay_height,
                       bg='#3c3c3c', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # 독립적인 버튼 윈도우 생성 (처음에는 숨김)
    button_overlay = tk.Toplevel(root)
    button_overlay.overrideredirect(True)
    button_overlay.attributes("-topmost", True)
    button_overlay.withdraw()  # 처음에는 완전히 숨김
    
    # 버튼 윈도우 위치 (타이머 오른쪽에 3px 간격)
    button_x = x_position + overlay_width + scale_px(3)  # 3px 간격 추가
    button_y_hidden = -overlay_height - scale_px(10)  # 화면 위쪽 바깥 (숨겨진 위치)
    button_y_visible = y_final  # 타이머와 같은 높이 (보이는 위치)
    
    button_overlay.geometry(f"{button_width}x{overlay_height}+{button_x}+{button_y_hidden}")
    
    # 버튼 프레임 (투명 배경)
    button_frame = tk.Frame(button_overlay, bg='#3c3c3c')
    button_frame.pack(fill=tk.BOTH, expand=True)
    
    # 버튼 프레임을 투명하게 만들기 위해 배경색을 버튼 오버레이와 동일하게 설정
    button_overlay.configure(bg='black')
    button_overlay.attributes('-transparentcolor', 'black')
    button_frame.configure(bg='black')
    
    # 연장 버튼 중복 클릭 방지를 위한 변수
    last_extend_time = 0
    
    def handle_extend_recording():
        """녹음 연장 버튼 클릭 핸들러 (중복 클릭 방지 포함)"""
        nonlocal last_extend_time
        current_time = time.time()
        
        # 0.3초 내 중복 클릭 방지
        if current_time - last_extend_time < 0.3:
            return
        
        last_extend_time = current_time
        execute_wheel_middle_function()
    
    # 일시정지/재개 버튼
    pause_button = tk.Button(button_frame, text="Ⅱ" if not recording_paused else "▶", 
                            font=("Segoe UI Symbol", 9), bg='#5a5a5a', fg='white', 
                            activebackground='#7a7a7a', bd=0, width=2, height=1,
                            command=toggle_recording_pause)
    pause_button.pack(side=tk.LEFT, padx=2, pady=2)
    
    # 녹음 연장 버튼
    extend_button = tk.Button(button_frame, text="＋", 
                             font=("Segoe UI Symbol", 9), bg='#3a8a3a', fg='white', 
                             activebackground='#5aaa5a', bd=0, width=2, height=1,
                             command=handle_extend_recording)
    extend_button.pack(side=tk.LEFT, padx=2, pady=2)
    
    # 취소 버튼
    cancel_button = tk.Button(button_frame, text="✕", 
                             font=("Segoe UI Symbol", 9), bg='#8a3a3a', fg='white', 
                             activebackground='#aa5a5a', bd=0, width=2, height=1,
                             command=lambda: asyncio.run_coroutine_threadsafe(cancel_recording(), loop))
    cancel_button.pack(side=tk.LEFT, padx=2, pady=2)

    # 호버 상태 관리 변수
    hover_timer = None
    buttons_visible = False
    animation_active = False
    
    def animate_buttons_in():
        """버튼을 위에서 슬라이드 인 애니메이션으로 표시"""
        nonlocal buttons_visible, animation_active
        if buttons_visible or animation_active:
            return
            
        animation_active = True
        buttons_visible = True
        
        # 버튼 윈도우 표시
        button_overlay.deiconify()
        
        # 애니메이션 설정 (위에서 아래로)
        start_y = -overlay_height - 10  # 시작 위치 (화면 위쪽 바깥)
        end_y = button_y_visible  # 끝 위치 (타이머와 같은 높이)
        duration = 256  # 256ms
        steps = 20
        step_time = duration // steps
        
        def animate_step(step):
            nonlocal animation_active
            if step <= steps:
                # ease-out 효과 적용
                progress = step / steps
                eased_progress = 1 - (1 - progress) ** 3  # cubic ease-out
                current_y = start_y + (end_y - start_y) * eased_progress
                
                button_overlay.geometry(f"{button_width}x{overlay_height}+{button_x}+{int(current_y)}")
                
                if step < steps:
                    overlay.after(step_time, lambda: animate_step(step + 1))
                else:
                    animation_active = False
                    logging.info("오버레이 제어 버튼 슬라이드 인 완료")
        
        animate_step(0)
        logging.info("오버레이 제어 버튼 슬라이드 인 시작")
    
    def animate_buttons_out():
        """버튼을 위로 슬라이드 아웃 애니메이션으로 숨김"""
        nonlocal buttons_visible, animation_active, hover_timer
        if not buttons_visible or animation_active:
            return
            
        animation_active = True
        buttons_visible = False
        
        # 애니메이션 설정 (아래에서 위로)
        start_y = button_y_visible  # 시작 위치 (타이머와 같은 높이)
        end_y = -overlay_height - 20  # 끝 위치 (화면 위쪽 바깥)
        duration = 96  # 96ms (숨김은 더 빠르게)
        steps = 15
        step_time = duration // steps
        
        def animate_step(step):
            nonlocal animation_active
            if step <= steps:
                # ease-in 효과 적용
                progress = step / steps
                eased_progress = progress ** 2  # quadratic ease-in
                current_y = start_y + (end_y - start_y) * eased_progress
                
                button_overlay.geometry(f"{button_width}x{overlay_height}+{button_x}+{int(current_y)}")
                
                if step < steps:
                    overlay.after(step_time, lambda: animate_step(step + 1))
                else:
                    animation_active = False
                    button_overlay.withdraw()  # 애니메이션 완료 후 완전히 숨김
                    logging.info("오버레이 제어 버튼 슬라이드 아웃 완료")
        
        animate_step(0)
        logging.info("오버레이 제어 버튼 슬라이드 아웃 시작")
        
        # 타이머 취소
        if hover_timer:
            overlay.after_cancel(hover_timer)
            hover_timer = None
    
    def on_enter(event=None):
        """마우스가 오버레이 영역에 들어왔을 때"""
        nonlocal hover_timer
        # 기존 타이머가 있다면 취소
        if hover_timer:
            overlay.after_cancel(hover_timer)
            hover_timer = None
        animate_buttons_in()
    
    def on_leave(event=None):
        """마우스가 오버레이 영역을 벗어났을 때"""
        nonlocal hover_timer
        # 0.256초 후 버튼 숨김
        if hover_timer:
            overlay.after_cancel(hover_timer)
        hover_timer = overlay.after(256, animate_buttons_out)
    
    def update_pause_button_text():
        """일시정지 버튼 텍스트 업데이트"""
        if recording_paused:
            pause_button.config(text="▶")  # 재생 아이콘
        else:
            pause_button.config(text="Ⅱ")  # 일시정지 아이콘
    
    # 마우스 이벤트 바인딩 (메인 오버레이와 버튼 윈도우 모두)
    overlay.bind("<Enter>", on_enter)
    overlay.bind("<Leave>", on_leave)
    frame.bind("<Enter>", on_enter)
    frame.bind("<Leave>", on_leave)
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    
    # 버튼 윈도우에도 마우스 이벤트 바인딩
    button_overlay.bind("<Enter>", on_enter)
    button_overlay.bind("<Leave>", on_leave)
    button_frame.bind("<Enter>", on_enter)
    button_frame.bind("<Leave>", on_leave)
    pause_button.bind("<Enter>", on_enter)
    pause_button.bind("<Leave>", on_leave)
    extend_button.bind("<Enter>", on_enter)
    extend_button.bind("<Leave>", on_leave)
    cancel_button.bind("<Enter>", on_enter)
    cancel_button.bind("<Leave>", on_leave)

    # 그라데이션 프로그레스바를 위한 설정
    num_segments = 30  # 그라데이션을 위한 세그먼트 수
    segment_width = overlay_width / num_segments
    start_color = (128, 128, 128)  # rgb(0, 212, 28) # 기존: (102, 213, 117)
    end_color = (204, 204, 204)    # rgb(0, 162, 255) # 기존: (135, 206, 235)

    # 각 세그먼트의 색상을 계산하여 저장할 리스트
    gradient_colors = []
    progress_segments = []
    
    # 각 세그먼트의 색상 계산 및 초기 세그먼트 생성
    for i in range(num_segments):
        # 현재 세그먼트의 비율 (0 ~ 1)
        ratio = i / (num_segments - 1) if num_segments > 1 else 0
        
        # 시작 색상에서 끝 색상으로 선형 보간
        r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
        g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
        b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
        
        # RGB 색상을 16진수 코드로 변환
        color = f'#{r:02x}{g:02x}{b:02x}'
        gradient_colors.append(color)
        
        # 각 세그먼트의 위치 계산
        x0 = i * segment_width
        x1 = (i + 1) * segment_width
        
        # 세그먼트 생성 (처음에는 너비 0)
        segment = canvas.create_rectangle(0, 0, 0, overlay_height, fill=color, outline="")
        progress_segments.append(segment)

    # 텍스트 설정
    initial_text = "00:00"
    font_spec = ("Malgun Gothic", 11, "bold")
    font = tkfont.Font(family=font_spec[0], size=font_spec[1], weight=font_spec[2])

    text_width = font.measure(initial_text)
    start_x = (overlay_width - text_width) // 2
    center_y = overlay_height // 2

    # 문자별 위치 측정
    char_positions = []
    current_x = start_x
    for ch in initial_text:
        ch_width = font.measure(ch)
        char_positions.append((current_x + ch_width // 2, ch))  # 중심 좌표
        current_x += ch_width

    time_text_items = []
    for x, ch in char_positions:
        item = canvas.create_text(x, center_y, text=ch, fill="white", font=font, anchor="center")
        time_text_items.append(item)

    animate_overlay_in(overlay, y_start, y_final)

    overlay.update_idletasks()
    create_rounded_bottom_corners(overlay)

    # 애니메이션 관련 변수
    is_animating = False
    animation_start_time = 0
    start_progress_ratio = 0
    target_progress_ratio = 0
    
    def start_progress_animation(from_ratio, to_ratio):
        """프로그레스바 애니메이션 시작"""
        nonlocal is_animating, animation_start_time, start_progress_ratio, target_progress_ratio
        is_animating = True
        animation_start_time = time.time() * 1000  # 밀리초 단위로 변환
        start_progress_ratio = from_ratio
        target_progress_ratio = to_ratio
    
    def update_time():
        if not overlay_running:
            return

        nonlocal is_animating, animation_start_time, start_progress_ratio, target_progress_ratio
        
        # 일시정지 상태에 따른 시간 계산
        if recording_paused:
            # 일시정지 상태에서는 시간 업데이트 중지
            if pause_start_time:
                effective_elapsed_time = pause_start_time - start_time - total_paused_time
            else:
                effective_elapsed_time = time.time() - start_time - total_paused_time
        else:
            # 정상 상태에서는 일시정지된 총 시간을 빼고 계산
            effective_elapsed_time = time.time() - start_time - total_paused_time
        
        # 시간 표시용 정수 변환
        int_elapsed_time = max(0, int(effective_elapsed_time))
        minutes = int_elapsed_time // 60
        seconds = int_elapsed_time % 60
        formatted = f"{minutes:02}:{seconds:02}"

        # 일시정지 버튼 텍스트 업데이트
        update_pause_button_text()

        # 일시정지 상태에서는 프로그레스바 업데이트 중지
        if not recording_paused:
            # 프로그레스바 애니메이션 또는 일반 업데이트
            if is_animating:
                # 애니메이션 진행 시간 계산 (밀리초)
                animation_elapsed = (time.time() * 1000) - animation_start_time
                animation_progress = min(animation_elapsed / PROGRESSBAR_ANIMATION_DURATION, 1.0)
                
                # 이징 함수 적용 (ease-out cubic)
                t = 1 - (1 - animation_progress) ** 3
                
                # 현재 진행률 계산
                current_ratio = start_progress_ratio + (target_progress_ratio - start_progress_ratio) * t
                
                # 애니메이션 완료 체크
                if animation_progress >= 1.0:
                    is_animating = False
                    current_ratio = target_progress_ratio
            else:
                # 일반 업데이트 - 현재 경과 시간 기반 진행률
                current_ratio = min(effective_elapsed_time / overlay_total_time, 1.0)
            
            # 프로그레스바 업데이트 (그라데이션 세그먼트)
            total_width = int(overlay_width * current_ratio)
            
            for i, segment in enumerate(progress_segments):
                # 각 세그먼트의 시작 위치와 너비 계산
                x0 = i * segment_width
                x1 = (i + 1) * segment_width
                
                if x0 < total_width:
                    # 세그먼트가 표시되어야 하는 경우
                    end_x = min(x1, total_width)
                    segment_visible_width = end_x - x0
                    canvas.coords(segment, x0, 0, x0 + segment_visible_width, overlay_height)
                else:
                    # 세그먼트가 표시되지 않아야 하는 경우
                    canvas.coords(segment, 0, 0, 0, 0)

            # 문자별 업데이트
            for i, ch in enumerate(formatted):
                item = time_text_items[i]
                x = canvas.coords(item)[0]
                color = "black" if x <= total_width else "white"
                canvas.itemconfig(item, text=ch, fill=color)
        else:
            # 일시정지 상태에서는 텍스트만 업데이트 (프로그레스바는 멈춤)
            for i, ch in enumerate(formatted):
                item = time_text_items[i]
                canvas.itemconfig(item, text=ch)

        # 더 짧은 간격(20ms = 약 50fps)으로 업데이트하여 부드러운 애니메이션 제공
        # 애니메이션 중일 때는 더 높은 빈도로 업데이트
        update_interval = 20 if is_animating else 200
        overlay.after(update_interval, update_time)
    
    # 오버레이에 애니메이션 메서드 추가
    overlay.start_progress_animation = start_progress_animation
    
    # 오버레이에 버튼 숨기기 메서드 추가 (종료 시 정리용)
    overlay.hide_buttons = animate_buttons_out

    update_time()

def close_overlay():
    """
    녹음 오버레이 종료 - 슬라이드 아웃 효과 적용
    """
    global overlay_running, overlay, button_overlay
    overlay_running = False
    
    # 버튼 오버레이 정리
    if 'button_overlay' in globals() and button_overlay is not None:
        try:
            if button_overlay.winfo_exists():
                button_overlay.destroy()
            button_overlay = None
        except Exception as e:
            logging.warning(f"버튼 오버레이 종료 중 예외 발생: {e}")
            button_overlay = None
    
    if overlay is not None:
        try:
            # 오버레이 종료 전 버튼 정리
            if hasattr(overlay, 'hide_buttons'):
                overlay.hide_buttons()
            
            # 현재 위치에서 화면 위로 슬라이드 아웃
            if overlay.winfo_exists():
                current_geo = overlay.geometry().split("+")
                current_y = int(current_geo[2])
                animate_overlay_out(overlay, current_y, -50)
                overlay = None
        except Exception as e:
            logging.warning(f"오버레이 종료 중 예외 발생: {e}")
            if overlay and overlay.winfo_exists():
                overlay.destroy()
            overlay = None

def create_recording_handle_overlay():
    """화면 오른쪽 베젤에 녹음 핸들바 오버레이 생성"""
    global recording_handle_overlay, root, recording
    
    if recording_handle_overlay is not None:
        return  # 이미 생성된 경우 중복 생성 방지
    
    # 메인 윈도우 생성
    recording_handle_overlay = tk.Toplevel(root)
    recording_handle_overlay.overrideredirect(True)
    recording_handle_overlay.attributes("-topmost", True)
    
    # 화면 크기 가져오기
    screen_width = recording_handle_overlay.winfo_screenwidth()
    screen_height = recording_handle_overlay.winfo_screenheight()
    
    # 핸들바 크기 설정 (32x32 정사각형)
    handle_width = scale_px(32)
    handle_height = scale_px(32)
    
    # 호버 효과 설정
    hover_enabled = False  # 사용자 요청에 따라 비활성화, 필요시 True로 변경
    
    # 위치 계산 (hover_enabled 상태에 따라 다르게 설정)
    if hover_enabled:
        # 호버 활성화 시: 처음에는 숨겨진 상태 (베젤 밖으로)
        x_position = screen_width - handle_width + scale_px(16)  # 16px 정도 베젤 밖으로 나가게
    else:
        # 호버 비활성화 시: 완전히 보이는 상태
        x_position = screen_width - handle_width  # 화면 끝에 딱 맞게
    
    y_position = int(screen_height * 0.20)
    
    recording_handle_overlay.geometry(f"{handle_width}x{handle_height}+{x_position}+{y_position}")
    
    # 배경을 투명하게 만들기 위한 트릭
    bg_color = '#010101'  # 거의 검은색 (투명색으로 사용)
    recording_handle_overlay.configure(bg=bg_color)
    recording_handle_overlay.attributes('-transparentcolor', bg_color)
    
    # 메인 캔버스 (도형 그리기용)
    canvas = tk.Canvas(recording_handle_overlay, width=handle_width, height=handle_height,
                      bg=bg_color, highlightthickness=0, bd=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # 애니메이션 상태 관리 변수
    animation_in_progress = False
    hover_timer = None
    is_hovered = False
    
    # 녹음 버튼 클릭 이벤트
    def on_record_button_click(event=None):
        """녹음 버튼 클릭 이벤트"""
        global recording
        if not recording:
            # 녹음 시작
            start_recording_via_tray(None, None)
        else:
            # 녹음 중단
            stop_recording_via_tray(None, None)
        
        # 버튼 그래픽 업데이트
        draw_button_graphics()
    
    # 더 간단한 대안: 둥근 사각형을 여러 도형으로 조합
    def draw_rounded_background_simple():
        """간단한 둥근 모서리 배경 - 조합 방식"""
        canvas.delete("background")
        
        frame_color = '#3c3c3c'
        radius = scale_px(3)
        
        # 메인 사각형들로 둥근 사각형 구성
        # 중앙 사각형
        canvas.create_rectangle(
            radius, 0, handle_width, handle_height,
            fill=frame_color, outline='', tags="background"
        )
        
        # 왼쪽 중간 사각형
        canvas.create_rectangle(
            0, radius, radius, handle_height - radius,
            fill=frame_color, outline='', tags="background"
        )
        
        # 왼쪽 상단 원형
        canvas.create_oval(
            0, 0, radius*2, radius*2,
            fill=frame_color, outline='', tags="background"
        )
        
        # 왼쪽 하단 원형
        canvas.create_oval(
            0, (handle_height-1) - radius*2, radius*2, handle_height-1,
            fill=frame_color, outline='', tags="background"
        )
    
    # 버튼 그래픽 그리기 (유니코드 문자 사용)
    def draw_button_graphics():
        """녹음 상태에 따라 버튼 그래픽 그리기"""
        global recording
        canvas.delete("icon")  # 기존 아이콘 삭제
        
        center_x = handle_width // 2
        center_y = (handle_height // 2) - 1
        
        if recording:
            # 녹음 중 - 정지 아이콘 (유니코드 사각형)
            canvas.create_text(
                center_x, center_y,
                text="⏹",  # 유니코드 정지 기호
                font=("Segoe UI Symbol", 14, "bold"),
                fill='white',
                tags="icon"
            )
        else:
            # 녹음 대기 - 녹음 아이콘 (유니코드 원형)
            canvas.create_text(
                center_x, center_y,
                text="⏺",  # 유니코드 녹음 기호
                font=("Segoe UI Symbol", 14, "bold"),
                fill='white',
                tags="icon"
            )
    
    # 초기 배경 및 버튼 그래픽 그리기
    draw_rounded_background_simple()  # 간단한 방식 사용
    draw_button_graphics()
    
    # 호버 효과 (개선된 버전)
    if hover_enabled:
        # 호버 애니메이션 위치
        original_x = x_position
        hover_x = screen_width - handle_width + scale_px(2)  # 더 많이 나오게
        
        def on_enter(event=None):
            """마우스 진입 이벤트"""
            nonlocal animation_in_progress, is_hovered, hover_timer
            
            if animation_in_progress:
                return
            
            is_hovered = True
            
            # 기존 타이머 취소
            if hover_timer:
                recording_handle_overlay.after_cancel(hover_timer)
                hover_timer = None
            
            # 슬라이드 인 애니메이션
            animate_handle_in_improved(original_x, hover_x)
        
        def on_leave(event=None):
            """마우스 이탈 이벤트"""
            nonlocal animation_in_progress, is_hovered, hover_timer
            
            if animation_in_progress:
                return
            
            is_hovered = False
            
            # 잠시 후 슬라이드 아웃 (마우스가 다시 들어올 수 있도록 지연)
            if hover_timer:
                recording_handle_overlay.after_cancel(hover_timer)
            
            hover_timer = recording_handle_overlay.after(200, lambda: delayed_slide_out())
        
        def delayed_slide_out():
            """지연된 슬라이드 아웃"""
            nonlocal is_hovered, animation_in_progress
            
            if not is_hovered and not animation_in_progress:
                animate_handle_out_improved(hover_x, original_x)
        
        def animate_handle_in_improved(start_x, end_x):
            """개선된 슬라이드 인 애니메이션"""
            nonlocal animation_in_progress
            animation_in_progress = True
            
            duration = 200
            steps = 12
            step_time = duration // steps
            
            def animate_step(step):
                nonlocal animation_in_progress
                if step <= steps and recording_handle_overlay is not None:
                    # ease-out 효과
                    progress = step / steps
                    eased_progress = 1 - (1 - progress) ** 2
                    current_x = start_x + (end_x - start_x) * eased_progress
                    
                    try:
                        current_geometry = recording_handle_overlay.geometry()
                        width_height = current_geometry.split('+')[0]
                        y_pos = current_geometry.split('+')[2]
                        recording_handle_overlay.geometry(f"{width_height}+{int(current_x)}+{y_pos}")
                    except:
                        pass
                    
                    if step < steps:
                        recording_handle_overlay.after(step_time, lambda: animate_step(step + 1))
                    else:
                        animation_in_progress = False
                else:
                    animation_in_progress = False
            
            animate_step(0)
        
        def animate_handle_out_improved(start_x, end_x):
            """개선된 슬라이드 아웃 애니메이션"""
            nonlocal animation_in_progress
            animation_in_progress = True
            
            duration = 150
            steps = 10
            step_time = duration // steps
            
            def animate_step(step):
                nonlocal animation_in_progress
                if step <= steps and recording_handle_overlay is not None:
                    # ease-in 효과
                    progress = step / steps
                    eased_progress = progress ** 2
                    current_x = start_x + (end_x - start_x) * eased_progress
                    
                    try:
                        current_geometry = recording_handle_overlay.geometry()
                        width_height = current_geometry.split('+')[0]
                        y_pos = current_geometry.split('+')[2]
                        recording_handle_overlay.geometry(f"{width_height}+{int(current_x)}+{y_pos}")
                    except:
                        pass
                    
                    if step < steps:
                        recording_handle_overlay.after(step_time, lambda: animate_step(step + 1))
                    else:
                        animation_in_progress = False
                else:
                    animation_in_progress = False
            
            animate_step(0)
        
        # 이벤트 바인딩 (캔버스에만 바인딩하여 이벤트 중복 방지)
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<Button-1>", on_record_button_click)
    else:
        # 호버 비활성화 시 클릭 이벤트만 바인딩
        canvas.bind("<Button-1>", on_record_button_click)
        canvas.config(cursor="hand2")
    
    # 전역 업데이트 함수 저장
    def update_button_graphics():
        draw_rounded_background_simple()
        draw_button_graphics()
    
    recording_handle_overlay.update_button_graphics = update_button_graphics
    
    logging.info("녹음 핸들바 오버레이 생성 완료 (32x32 정사각형, 둥근 모서리, 유니코드 아이콘)")

def close_recording_handle_overlay():
    """녹음 핸들바 오버레이 닫기"""
    global recording_handle_overlay
    
    if recording_handle_overlay is not None:
        try:
            recording_handle_overlay.destroy()
        except:
            pass
        recording_handle_overlay = None
        logging.info("녹음 핸들바 오버레이 닫기 완료")

def update_recording_handle_overlay():
    """녹음 상태 변경 시 핸들바 오버레이 업데이트"""
    global recording_handle_overlay
    
    if recording_handle_overlay is not None:
        try:
            recording_handle_overlay.update_button_graphics()
        except:
            pass

def create_dictation_handle_overlay():
    """화면 오른쪽 베젤에 받아쓰기 핸들바 오버레이 생성"""
    global dictation_handle_overlay, root
    
    if dictation_handle_overlay is not None:
        return  # 이미 생성된 경우 중복 생성 방지
    
    # 메인 윈도우 생성
    dictation_handle_overlay = tk.Toplevel(root)
    dictation_handle_overlay.overrideredirect(True)
    dictation_handle_overlay.attributes("-topmost", True)
    
    # 화면 크기 가져오기
    screen_width = dictation_handle_overlay.winfo_screenwidth()
    screen_height = dictation_handle_overlay.winfo_screenheight()
    
    # 핸들바 크기 설정 (32x32 정사각형, 녹음 핸들과 동일)
    handle_width = scale_px(32)
    handle_height = scale_px(32)
    
    # 호버 효과 설정 (비활성화)
    hover_enabled = False
    
    # 위치 계산 (녹음 핸들 아래쪽에 배치)
    x_position = screen_width - handle_width  # 화면 끝에 딱 맞게
    y_position = int(screen_height * 0.234)  # 녹음 핸들(19%) 아래쪽에 배치
    
    dictation_handle_overlay.geometry(f"{handle_width}x{handle_height}+{x_position}+{y_position}")
    
    # 배경을 투명하게 만들기 위한 트릭
    bg_color = '#010101'  # 거의 검은색 (투명색으로 사용)
    dictation_handle_overlay.configure(bg=bg_color)
    dictation_handle_overlay.attributes('-transparentcolor', bg_color)
    
    # 메인 캔버스 (도형 그리기용)
    canvas = tk.Canvas(dictation_handle_overlay, width=handle_width, height=handle_height,
                      bg=bg_color, highlightthickness=0, bd=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    def is_notepad_focused():
        active = gw.getActiveWindow()
        return active and ("메모장" in active.title or "Notepad" in active.title)

    def monitor_notepad_focus():
        global focused_on_notepad, monitoring_thread
        while True:
            time.sleep(2)
            if not is_notepad_focused():
                time.sleep(0.5)
                focused_on_notepad = False
                monitoring_thread = None
                break

    # 받아쓰기 버튼 클릭 이벤트
    def on_dictation_button_click(event=None):
        global focused_on_notepad, monitoring_thread

        try:
            print(f"focused_on_notepad: {focused_on_notepad}")
            if focused_on_notepad:
                logging.info("메모장 포커스 상태 - 받아쓰기 종료 매크로 실행")

                notepads = [w for w in gw.getWindowsWithTitle("메모장") if w.title.endswith("메모장")]

                window = notepads[0]
                if window.isMinimized:
                    window.restore()
                window.activate()
                logging.info("기존 메모장 창에 포커스 이동")

                pyautogui.press('esc')
                ## 전체 선택 후 복사 뒤 닫기
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.2)
                pyautogui.press('end')
                focused_on_notepad = False
                monitoring_thread = None
                return

            # # 메모장 창 탐색
            # notepads = [w for w in gw.getWindowsWithTitle("메모장") if w.title.endswith("메모장")]

            # if notepads:
            #     window = notepads[0]
            #     if window.isMinimized:
            #         window.restore()
            #     window.activate()
            #     logging.info("기존 메모장 창에 포커스 이동")
            # else:
            # 새 메모장 실행
            subprocess.Popen(["notepad.exe"])
            logging.info("메모장 실행 중...")
            
            # 메모장이 뜰 때까지 기다림 (최대 6초)
            for _ in range(15):
                notepads = [w for w in gw.getWindowsWithTitle("메모장") if w.title.endswith("메모장")]
                if notepads:
                    notepads[0].activate()
                    break
                time.sleep(0.4)

            # 받아쓰기 단축키 실행
            time.sleep(1)
            pyautogui.hotkey('win', 'h')
            logging.info("Win+H 단축키 실행")

            focused_on_notepad = True

            if monitoring_thread is None:
                monitoring_thread = threading.Thread(target=monitor_notepad_focus, daemon=True)
                monitoring_thread.start()

        except Exception as e:
            logging.error(f"Win+H 단축키 실행 실패: {e}")
    
    # 간단한 둥근 배경 그리기
    def draw_rounded_background_simple():
        """간단한 둥근 모서리 배경 - 조합 방식"""
        canvas.delete("background")
        
        frame_color = '#2c5aa0'  # 파란색 계열 (받아쓰기 구분)
        radius = scale_px(3)
        
        # 메인 사각형들로 둥근 사각형 구성
        # 중앙 사각형
        canvas.create_rectangle(
            radius, 0, handle_width, handle_height,
            fill=frame_color, outline='', tags="background"
        )
        
        # 왼쪽 중간 사각형
        canvas.create_rectangle(
            0, radius, radius, handle_height - radius,
            fill=frame_color, outline='', tags="background"
        )
        
        # 왼쪽 상단 원형
        canvas.create_oval(
            0, 0, radius*2, radius*2,
            fill=frame_color, outline='', tags="background"
        )
        
        # 왼쪽 하단 원형
        canvas.create_oval(
            0, (handle_height-1) - radius*2, radius*2, handle_height-1,
            fill=frame_color, outline='', tags="background"
        )
    
    # 버튼 그래픽 그리기 (받아쓰기 아이콘)
    def draw_button_graphics():
        """받아쓰기 아이콘 그리기"""
        canvas.delete("icon")  # 기존 아이콘 삭제
        
        center_x = handle_width // 2
        center_y = (handle_height // 2) - 1
        
        # 받아쓰기 아이콘 (마이크 유니코드)
        canvas.create_text(
            center_x, center_y,
            text="🎤",  # 마이크 이모지
            font=("Segoe UI Emoji", 16, "bold"),
            fill='white',
            tags="icon"
        )
    
    # 초기 배경 및 버튼 그래픽 그리기
    draw_rounded_background_simple()
    draw_button_graphics()
    
    # 클릭 이벤트 바인딩
    canvas.bind("<Button-1>", on_dictation_button_click)
    canvas.config(cursor="hand2")
    
    logging.info("받아쓰기 핸들바 오버레이 생성 완료 (32x32 정사각형, 파란색 배경, 마이크 아이콘)")

def close_dictation_handle_overlay():
    """받아쓰기 핸들바 오버레이 닫기"""
    global dictation_handle_overlay
    
    if dictation_handle_overlay is not None:
        try:
            dictation_handle_overlay.destroy()
        except:
            pass
        dictation_handle_overlay = None
        logging.info("받아쓰기 핸들바 오버레이 닫기 완료")

def safe_block_input(block):
    """ctypes.windll.user32.BlockInput을 thread-safe하게 처리"""
    try:
        ctypes.windll.user32.BlockInput(block)
    except Exception as e:
        logging.error(f"BlockInput 호출 중 예외 발생: {e}")

def run_dentweb_upload_with_guard(download_dir, block_input=True, original_patient=None, current_patient=None):
    logging.info("덴트웹 업로드 시작")
    success = False
    cursor_blocked = False  # 커서 블록 상태 추적
    
    try:
        if block_input:
            logging.info(f"마우스/키보드 입력 차단 활성화 (환자: {current_patient})")
            safe_block_input(True)  # 필요시 주석 처리
            # 마우스 커서를 금지 아이콘으로 변경
            cursor_blocked = set_block_cursor()
        else:
            logging.info(f"마우스/키보드 입력 차단 비활성화 (환자: {current_patient})")
            
        success = run_dentweb_upload(download_dir, tk_root=root, model_mode=MODEL_MODE, 
                                     original_patient=original_patient, current_patient=current_patient,
                                     chart_upload_disabled=not DENTWEB_CHART_UPLOAD_ENABLED,
                                     upload_files_enabled=UPLOAD_FILES_TO_DENTWEB)
        if success:
            logging.info("덴트웹 업로드 완료")
        else:
            logging.error("덴트웹 업로드 실패")
        return success
    except Exception as e:
        logging.error(f"덴트웹 업로드 중 예외 발생: {e}")
        success = False
        return False
    finally:
        # 입력 차단 및 커서 복원 처리
        restore_failed = False
        
        if block_input:
            logging.info("마우스/키보드 입력 차단 해제")
            try:
                safe_block_input(False)
            except Exception as block_error:
                logging.error(f"입력 차단 해제 중 오류: {block_error}")
                
            # 커서가 블록된 경우에만 복원 시도
            if cursor_blocked:
                try:
                    # 마우스 커서를 원래대로 복원
                    if not restore_default_cursor():
                        logging.warning("첫 번째 커서 복원 시도 실패, 두 번째 시도 중...")
                        # 두 번째 시도
                        restore_failed = not restore_default_cursor()
                except Exception as cursor_error:
                    logging.error(f"커서 복원 중 오류: {cursor_error}")
                    restore_failed = True
                    
                # 복원 실패 시 로그 기록
                if restore_failed:
                    logging.error("마우스 커서 복원에 여러 번 실패했습니다. 시스템 재시작이 필요할 수 있습니다.")
        
        # 업로드 성공 시 block_input 값과 관계없이 붙여넣기 안내 메시지 표시
        try:
            if success:
                if not DENTWEB_CHART_UPLOAD_ENABLED:
                    # 붙여넣기 안내 메시지 표시
                    show_paste_tip()
                    # 활성화 상태 설정
                    auto_hide_paste_tip.active = True
        except Exception as tip_error:
            logging.error(f"붙여넣기 팁 표시 중 오류: {tip_error}")

# [변경] 다운로드/업로드를 백그라운드에서 처리하기 위한 함수
async def do_download_and_upload_in_background():
    global uploading, record_button_location, REMAINING_CREDITS
    global original_patient_name, cpName, subfolder, filename, recording_data, SAMPLE_RATE, CHANNELS, servers, ALLOWED_LANGUAGES, MODEL_MODE
    
    with guard_lock:
        if uploading:
            logging.info("업로드 중입니다. 작업을 대기열에 추가합니다.")
            upload_queue.put(())
            return
        uploading = True

    # 오버레이 생성
    overlay_win, update_task_msg, destroy_overlay = create_task_overlay("필기노트를 저장하고 있어요.")
    loop = asyncio.get_running_loop()
    download_dir = None  # 변수 초기화

    try:
        # --- 다운로드 (병렬 처리 시도) -> run_in_executor ---
        # 병렬 처리 가능 여부와 조건 사전 확인
        should_use_parallel = False
        if PARALLEL_PROCESSING_AVAILABLE and recording_data:
            try:
                # 오디오 지속 시간 계산
                total_samples = sum(len(data) for data in recording_data)
                if total_samples > 0:
                    audio_duration_seconds = total_samples / SAMPLE_RATE
                    audio_duration_minutes = audio_duration_seconds / 60
                    
                    # 오디오 지속 시간 유효성 검증
                    if 0 < audio_duration_seconds <= 7200:  # 최대 2시간 제한
                        # 병렬 처리 임계값 확인 (8분 이상)
                        from audio_parallel_config import get_parallel_threshold_minutes
                        threshold_minutes = get_parallel_threshold_minutes()
                        
                        if audio_duration_minutes >= threshold_minutes:
                            should_use_parallel = True
                            logging.info(f"병렬 처리 사용: {audio_duration_minutes:.1f}분 오디오")
                        else:
                            logging.info(f"단일 처리 사용: {audio_duration_minutes:.1f}분 오디오 (병렬 처리 임계값: {threshold_minutes}분)")
                    else:
                        logging.warning(f"비정상적인 오디오 지속 시간: {audio_duration_seconds:.1f}초")
                else:
                    logging.warning("녹음 데이터의 총 샘플 수가 0입니다")
            except Exception as e:
                logging.warning(f"병렬 처리 조건 확인 중 오류: {e}")
        else:
            if not PARALLEL_PROCESSING_AVAILABLE:
                logging.info("병렬 처리 모듈이 없어 기존 방식으로 STT 처리")
            else:
                logging.info("녹음 데이터가 없어 기존 방식으로 STT 처리")

        # 병렬 처리 실행 (조건을 만족하는 경우만)
        if should_use_parallel:
            try:
                logging.info(f"병렬 처리 시도: 오디오 길이 {audio_duration_seconds:.1f}초")
                update_task_msg(f"긴 녹음을 빠르게 처리하고 있어요! ({audio_duration_minutes:.1f}분)")
                
                # 폴더 경로 검증
                folder_path = Path(subfolder)
                if not folder_path.exists():
                    folder_path.mkdir(parents=True, exist_ok=True)
                    logging.info(f"병렬 처리: 출력 폴더 생성됨: {folder_path}")
                
                # 병렬 처리 실행
                parallel_result = await asyncio.wait_for(
                    process_audio_parallel(
                        recording_data=recording_data,
                        sample_rate=SAMPLE_RATE,
                        channels=CHANNELS,
                        audio_duration_seconds=audio_duration_seconds,
                        output_folder=folder_path,
                        base_filename=filename,
                        servers=servers,
                        mode=MODEL_MODE
                    ),
                    timeout=1800  # 30분 타임아웃
                )
                
                if parallel_result is not None and isinstance(parallel_result, dict):
                    text_content = parallel_result.get("text", "")
                    
                    # 병렬 처리 성공 검증
                    if text_content and text_content.strip():
                        logging.info(f"병렬 처리 성공: {len(text_content)}자 텍스트 생성")
                        
                        # 병렬 처리 결과를 기존 형식으로 변환
                        result = {
                            "folder_path": subfolder,
                            "credits_used": parallel_result.get("credits_used", 0),
                            "remaining_credits": parallel_result.get("remaining_credits", 0)
                        }
                        
                        # 병렬 처리된 텍스트를 파일로 저장
                        try:
                            # 파일명 생성 (dnote_main.py의 기존 로직과 동일)
                            if "_음성_" in filename:
                                text_filename = filename.replace("_음성_", "_본문_")
                            else:
                                text_filename = filename.replace("_", "_본문_")
                            
                            text_file_path = folder_path / f"{text_filename}.txt"
                            
                            with open(text_file_path, 'w', encoding='utf-8-sig') as f:
                                f.write(text_content)
                                
                            logging.info(f"병렬 처리 결과 저장: {text_file_path}")
                            update_task_msg("병렬 처리 완료!")
                            
                        except Exception as e:
                            logging.error(f"병렬 처리 결과 파일 저장 실패: {e}")
                            # 파일 저장 실패해도 처리는 성공한 것으로 간주
                            pass
                    else:
                        logging.warning("병렬 처리: 텍스트 결과가 비어 있습니다")
                        if parallel_result.get("credits_used", 0) > 0:
                            logging.warning("크레딧은 사용되었지만 텍스트 결과가 없음 - 서버 오류 가능성")
                        raise ValueError("병렬 처리 결과가 비어 있음")
                else:
                    # 병렬 처리 결과가 올바르지 않음
                    logging.warning("병렬 처리 결과가 올바르지 않음, 기존 방식으로 처리")
                    raise ValueError("병렬 처리 결과 형식 오류")
                    
            except asyncio.TimeoutError:
                logging.error("병렬 처리 타임아웃 (30분), 기존 방식으로 처리")
                update_task_msg("처리 시간이 오래 걸려 기존 방식으로 전환합니다...")
                # 기존 방식으로 fallback
                result = await loop.run_in_executor(
                    None,
                    lambda: run_download_process(subfolder, filename, servers, ALLOWED_LANGUAGES, MODEL_MODE)
                )
                
            except Exception as e:
                logging.error(f"병렬 처리 중 오류 발생, 기존 방식으로 처리: {e}")
                update_task_msg("기존 방식으로 처리합니다...")
                # Sentry에 병렬 처리 실패 로깅 (실제 오류만)
                log_error(f"병렬 처리 실패: {str(e)}", exc_info=True, level="error", 
                         extra_context={
                             "audio_duration": audio_duration_seconds if 'audio_duration_seconds' in locals() else 0,
                             "filename": filename,
                             "parallel_available": PARALLEL_PROCESSING_AVAILABLE
                         })
                
                # 기존 방식으로 fallback
                result = await loop.run_in_executor(
                    None,
                    lambda: run_download_process(subfolder, filename, servers, ALLOWED_LANGUAGES, MODEL_MODE)
                )
        else:
            # 병렬 처리 조건을 만족하지 않음 - 처음부터 기존 방식으로 처리 (ERROR 없음)
            logging.info("기존 방식으로 STT 처리")
            result = await loop.run_in_executor(
                None,
                lambda: run_download_process(subfolder, filename, servers, ALLOWED_LANGUAGES, MODEL_MODE)
            )
        
        # 결과 처리 (병렬 또는 기존 방식)
        if isinstance(result, dict):
            download_dir = result.get("folder_path")
            credits_used = result.get("credits_used", 0)
            remaining_credits = result.get("remaining_credits", 0)

            # 크레딧 정보 로깅
            logging.info(f"다운로드 완료: (기존 크레딧: {remaining_credits + credits_used} → 남은 크레딧: {remaining_credits})")
            update_task_msg(f"다운로드 끝! {remaining_credits}크레딧 남았어요.")

            REMAINING_CREDITS = remaining_credits  # 전역 변수 업데이트
        else:
            # 이전 버전 호환성을 위한 처리
            download_dir = result
            update_task_msg("다운로드 끝!")

        logging.info(f"다운로드 완료: {download_dir}")
        
    except Exception as e:
        logging.error(f"다운로드 작업 중 예외 발생: {e}")
        log_error(f"다운로드 작업 실패: {str(e)}", exc_info=True, level="error", 
                 extra_context={"filename": filename})
        download_dir = None
        update_task_msg("다운로드 중 오류가 발생했습니다...")

    # --- 업로드 ---
    if download_dir:
        # 환자 이름이 "무제"인 경우 메시지 변경
        if cpName == "무제":
            update_task_msg("작업내용을 저장하고 있어요!")
        else:
            update_task_msg("마우스와 키보드 입력이 잠시 정지돼요!")
            
        logging.info(f"업로드 작업 시작: {download_dir}")
        try:
            # 환자 이름이 "무제"인 경우 마우스 입력 차단하지 않음
            block_input_setting = False if cpName == "무제" else True
            
            # 원래 환자 이름과 현재 환자 정보 전달
            success = await loop.run_in_executor(
                None,
                lambda: run_dentweb_upload_with_guard(download_dir, block_input=block_input_setting, 
                                                      original_patient=original_patient_name, 
                                                      current_patient=cpName)
            )
            if success:
                play_audio_fast('NoA_Engage')
                update_task_msg("다 적었어요!")
            else:
                update_task_msg("뭔가 잘못됐어요...")
        except Exception as e:
            logging.error(f"업로드 작업 중 예외 발생: {e}")
            log_error(f"업로드 작업 실패: {str(e)}", exc_info=True, level="error")
            update_task_msg("뭔가 잘못됐어요...")

    # 덴트웹 녹음 종료
    if DENTWEB_RECORDING_ENABLED:
        if not click_location(record_button_location):
            logging.error("덴트웹 녹음 종료 실패. 위치: " + str(record_button_location))

    # finally: 블록을 제거하고 일반 코드로 변경
    with guard_lock:
        uploading = False

    # 대기열 처리
    if not upload_queue.empty():
        next_note_url, next_cookies, next_ls = upload_queue.get()
        asyncio.create_task(do_download_and_upload_in_background())

    # "다운로드/업로드" 오버레이 닫기
    destroy_overlay()
    
    # 일정 시간 후 붙여넣기 팁 자동 숨김 (10초 후)
    asyncio.create_task(auto_hide_paste_tip())
    
    # 남은 크레딧이 500 이하일 경우, 남은 크레딧 정보 표시.
    try:
        if REMAINING_CREDITS < 500:
            # 예쁜 토스트 팝업으로 변경
            asyncio.create_task(show_credit_toast_popup(REMAINING_CREDITS, duration=99999))

        if REMAINING_CREDITS < MAX_RECORDING_DURATION / 60 * Model_Price():
            asyncio.create_task(show_notification_overlay(f"잔여 포인트가 적어 작업이 조기종료됩니다.", duration=3))

    except Exception as e:
        logging.error(f"잔여 크레딧 알림 중 예외 발생: {e}")

# 안전장치
async def ensure_listener_active(current_rid):
    """
    마우스 리스너와 녹음 타이머 안전장치
    Args:
        current_rid: 현재 녹음의 고유 ID
    """
    global listener_active, recording, rid
    try:
        await asyncio.sleep(4)  # 4초 후
        
        # 현재 녹음이 아니라면 종료 (다른 녹음이 시작된 경우)
        if rid != current_rid:
            logging.info(f"안전장치 종료: 녹음 ID 불일치 (현재: {rid}, 안전장치: {current_rid})")
            return
            
        if not listener_active:
            listener_active = True
            logging.info("안전장치: 마우스 리스너를 강제로 활성화했습니다.")
        
        # 비상 녹음 타이머 - 녹음이 시작된 후 MAX_RECORDING_TIME 시간이 지나면 강제 종료
        if recording and rid == current_rid:
            await asyncio.sleep(MAX_RECORDING_TIME)
            
            # 다시 한 번 확인: 여전히 같은 녹음이고 녹음 중인지
            if recording and rid == current_rid:
                logging.warning(f"비상 안전장치: 최대 녹음 시간을 초과하여 녹음을 강제 종료합니다. (녹음 ID: {current_rid})")
                try:
                    await stop_recording()
                except Exception as e:
                    logging.error(f"비상 녹음 종료 중 오류: {e}")
                    # 녹음 상태를 강제로 초기화하여 앱이 동작할 수 있게 함
                    recording = False
                    listener_active = True
                    asyncio.create_task(show_notification_overlay("작업이 너무 오래 지속되어 강제 종료되었습니다.", duration=5))
            else:
                logging.info(f"안전장치 종료: 녹음이 이미 종료되었거나 다른 녹음으로 변경됨 (현재: {rid}, 안전장치: {current_rid})")
                
    except asyncio.CancelledError:
        logging.info(f"안전장치 태스크가 취소되었습니다. (녹음 ID: {current_rid})")
    except Exception as e:
        logging.error(f"안전장치 실행 중 예외 발생: {e}")

# 안전장치
async def ensure_listener_recovery():
    await asyncio.sleep(3)  # 3초 후
    global listener_active
    if not listener_active:
        listener_active = True
        logging.info("안전장치: 마우스 리스너를 강제로 활성화했습니다.")

async def start_recording():
    """
    녹음 시작 코루틴.
    - 드라이버 초기화/로그인
    - 클로바노트 페이지에서 녹음 시작 버튼 클릭
    - 녹음중 오버레이, 포커스 유지 스레드 시작
    """
    global rid, overlay_running, recording, listener_active, record_button_location, recording_data, SET_RECORDING_DURATION, recording_timer_task
    global patient_names_list, original_patient_name, patient_name_monitor_task
    global recording_paused, pause_start_time, total_paused_time, paused_audio_data  # 일시정지 관련 변수 추가
    global safety_task  # 안전장치 Task 추가
    
    if recording:  # 이미 녹음 중이라면 중복 방지
        logging.warning("이미 녹음 중입니다.")
        return
    
    # 이전 안전장치 Task가 있다면 취소
    if safety_task and not safety_task.done():
        safety_task.cancel()
        try:
            await safety_task
        except asyncio.CancelledError:
            pass
        logging.info("이전 안전장치 Task가 취소되었습니다.")
    
    # 일시정지 관련 변수 초기화
    recording_paused = False
    pause_start_time = None
    total_paused_time = 0
    paused_audio_data = []
    
    # 마이크 검사 수행
    if not check_microphone():
        asyncio.create_task(show_notification_overlay("마이크가 연결되지 않았습니다. 마이크를 연결한 후 다시 시도해주세요.", duration=5))
        # 리스너 활성화를 보장하여 녹음 시작/종료 버튼이 작동하도록 함
        listener_active = True
        asyncio.create_task(ensure_listener_recovery())
        return
    
    # 디스크 공간 확인 (저장 경로)
    save_path = SAVE_PATH if SAVE_PATH and os.path.exists(SAVE_PATH) else str(get_desktop_path() / 'D-Note 파일')
    has_space, free_space_mb = check_disk_space(save_path, required_space_mb=300)  # 300MB 필요
    
    if not has_space:
        logging.warning(f"디스크 공간 부족: 남은 공간 {free_space_mb:.2f}MB (필요: 300MB)")
        asyncio.create_task(show_notification_overlay(f"디스크 공간 부족. 최소 300MB 필요. (남은 공간: {free_space_mb:.0f}MB)", duration=5))
        listener_active = True
        asyncio.create_task(ensure_listener_recovery())
        return
    
    # 녹음 시간 설정 확인
    if not set_recording_duration():
        asyncio.create_task(show_notification_overlay("작업 시간 설정에 실패했습니다. 다시 시도해주세요.", duration=4))
        listener_active = True  # 리스너를 활성화하여 버튼 작동 보장
        return
    
    play_audio_fast('AP_Engage')

    # 마우스 리스너 비활성화
    listener_active = False
    rid += 1
    print(f"녹음 시작. 현재 rid: {rid}")
    
    # 안전장치: 새로운 Task 생성 및 저장
    safety_task = asyncio.create_task(ensure_listener_active(rid))

    # 덴트웹에서 녹음 병행 수행
    if DENTWEB_RECORDING_ENABLED:
        try:
            try:
                activate_window2(" 사진 보기 ")
            except Exception as e:
                logging.info("사진보기 창 없음")
            activate_window(" 덴트웹 :")
            time.sleep(0.5)
            click_EMR_button()
            time.sleep(0.2)
            record_button_location = click_record_button()
            print(str(record_button_location))
            if not record_button_location:
                logging.info("덴트웹에서 녹음 버튼을 찾을 수 없습니다.")
                if not close_DUR_popup():
                    logging.error("DUR 팝업 닫기 실패")
                    asyncio.create_task(show_notification_overlay("덴트웹 작업 실패...", duration=1))
                    # raise Exception("덴트웹 녹음 클릭 실패")
                
                time.sleep(1.5)
                record_button_location = click_record_button()

                if not record_button_location:
                    asyncio.create_task(show_notification_overlay("덴트웹 작업 실패...", duration=1))
                    raise Exception("덴트웹 녹음 클릭 실패")
            
        except Exception as e:
            print(f"덴트웹 녹음 시작 실패: {e}")

    # 여기서부터 덴노트 녹음 시작
    overlay_running = True
    # [수정] 별도 Thread 사용 안 함, 바로 create_overlay() 호출

    create_overlay()
    asyncio.create_task(show_notification_overlay("시작할게요!", duration=2))

    #녹음 시작 시간
    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")

    # 환자 이름 관련 변수 초기화
    patient_names_list = []
    
    # 환자 이름 가져오기
    global cpName
    patient_info = get_patient_info()
    cpName = patient_info.display_name
    if cpName == "무제":
        logging.info("차트 프로그램에서 환자 정보를 찾을 수 없습니다.")
    else:
        print(f"환자 이름: {cpName}")
    
    # 원래 환자 이름 저장 및 환자 이름 목록에 추가
    original_patient_name = cpName
    patient_names_list.append(cpName)
    
    # 파일 이름 설정
    global filename
    filename = f"{cpName}_음성_{timestamp}"
    print(f"파일 이름: {filename}")

    recording_data = []
    recording_error_count = 0  # 콜백 오류 카운터
    
    def callback(indata, frames, time_info, status):
        """
        오디오 스트림 콜백 함수 - 데이터가 들어올 때마다 호출됨
        
        Args:
            indata: 입력 오디오 데이터 (numpy 배열)
            frames: 프레임 수
            time_info: 시간 정보 (may contain 'current_time' instead of 'time')
            status: 상태 플래그 (오류 등)
        """
        nonlocal recording_error_count
        
        try:
            if status:
                recording_error_count += 1
                logging.warning(f"오디오 콜백 상태 플래그: {status}, 오류 횟수: {recording_error_count}")
                
                # 오류가 지속적으로 발생하면 알림
                if recording_error_count % 5 == 0:
                    logging.error(f"지속적인 오디오 오류 발생 ({recording_error_count}회)")
                    asyncio.run_coroutine_threadsafe(
                        show_notification_overlay("마이크 오류가 발생하고 있습니다.", duration=2),
                        loop
                    )
                
                # 심각한 오류 수준에 도달하면 녹음 중단 요청
                if recording_error_count >= 20:
                    logging.critical(f"심각한 오디오 오류 발생 ({recording_error_count}회). 녹음을 중단합니다.")
                    asyncio.run_coroutine_threadsafe(
                        show_notification_overlay("마이크 오류로 작업을 중단합니다.", duration=4),
                        loop
                    )
                    asyncio.run_coroutine_threadsafe(stop_recording(), loop)
                    return
            
            # indata가 비어 있는지 또는 무음인지 확인
            if indata is None or len(indata) == 0 or np.all(np.abs(indata) < 1e-10):
                recording_error_count += 1
                if recording_error_count % 10 == 0:
                    logging.warning(f"무음 데이터 감지 ({recording_error_count}회)")
            
            # 정상 데이터 처리
            if indata is not None and len(indata) > 0:
                recording_data.append(indata.copy())
                # 성공적인 데이터 처리 시 오류 카운터 리셋 (간헐적 오류는 무시)
                if recording_error_count > 0:
                    recording_error_count = max(0, recording_error_count - 1)
            
        except Exception as e:
            recording_error_count += 1
            logging.error(f"오디오 콜백 중 예외 발생: {e}, 오류 횟수: {recording_error_count}")
            
            # 오류 복구 시도
            try:
                if indata is not None and len(indata) > 0:
                    recording_data.append(indata.copy())
            except:
                # 복구 실패 시 빈 데이터 추가 방지
                pass

    # 스트림 생성
    global stream
    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            callback=callback,
            dtype='int16',  # 데이터 타입 설정
            device=None
        )
        stream.start()
        # 사용하는 마이크 1개 출력
        print(f"녹음을 시작합니다. 파일 이름: {filename}.wav")

        recording = True
        logging.info("녹음 시작됨")

        try:
            update_recording_handle_overlay()
        except Exception as e:
            logging.error(f"핸들바 오버레이 업데이트 실패: {e}")

    except Exception as e:
        logging.error(f"마이크 스트림 생성 실패: {e}")
        asyncio.create_task(show_notification_overlay("마이크를 꽃은 상태에서, 프로그램을 재시작해주세요.", duration=6))
        
        # 오버레이 정리
        overlay_running = False
        close_overlay()
        
        # 리스너 활성화 복구
        listener_active = True
        asyncio.create_task(ensure_listener_recovery())
        
        # 안전장치 Task 취소
        if safety_task and not safety_task.done():
            safety_task.cancel()
            try:
                await safety_task
            except asyncio.CancelledError:
                pass
        
        return

    # 녹음 데이터 모니터링 및 백업 함수
    async def monitor_recording_data():
        try:
            # 15초마다 데이터 확인 및 백업
            check_interval = 15
            backup_interval = 30
            last_backup_time = time.time()
            data_check_consecutive_fails = 0
            max_consecutive_fails = 3
            
            while recording:
                await asyncio.sleep(check_interval)
                
                # 녹음이 종료된 경우 루프 종료
                if not recording:
                    break
                
                # 데이터 확인
                if not recording_data:
                    data_check_consecutive_fails += 1
                    logging.warning(f"녹음 데이터가 비어 있습니다. 마이크 문제가 있을 수 있습니다. (연속 {data_check_consecutive_fails}/{max_consecutive_fails})")
                    asyncio.create_task(show_notification_overlay("마이크 데이터가 수신되지 않고 있습니다.", duration=2))
                    
                    # 연속 3번 실패하면 데이터 수신이 안 된다고 판단하고 사용자에게 알림
                    if data_check_consecutive_fails >= max_consecutive_fails:
                        logging.error(f"마이크 데이터 수신 실패가 {max_consecutive_fails}회 연속 발생하여 녹음을 중단합니다.")
                        asyncio.create_task(show_notification_overlay("마이크 오류로 작업이 중단됩니다.", duration=4))
                        await asyncio.sleep(4)
                        await stop_recording()
                        break
                else:
                    current_data_count = len(recording_data)
                    logging.info(f"녹음 진행 중: {current_data_count}개 데이터 청크 수집됨")
                    data_check_consecutive_fails = 0  # 데이터가 정상적으로 들어오면 카운터 초기화
                
                # 백업 생성 (30초마다)
                current_time = time.time()
                if current_time - last_backup_time >= backup_interval and recording_data:
                    try:
                        # 백업 폴더 생성
                        backup_dir = Path.home() / 'AppData' / 'Local' / 'dNote' / 'backups'
                        backup_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 백업하기 전 디스크 공간 확인
                        has_space, free_space_mb = check_disk_space(str(backup_dir), required_space_mb=100)  # 백업에는 100MB 정도면 충분
                        if not has_space:
                            logging.warning(f"백업을 위한 디스크 공간 부족: 남은 공간 {free_space_mb:.2f}MB")
                            asyncio.create_task(show_notification_overlay("디스크 공간이 부족하여 백업을 건너뜁니다.", duration=2))
                            
                            # 기존 백업 파일 중 가장 오래된 파일 삭제 시도
                            try:
                                all_backups = sorted(list(backup_dir.glob(f"backup_{cpName}_*.wav")))
                                if all_backups:
                                    os.remove(all_backups[0])
                                    logging.info(f"공간 확보를 위해 오래된 백업 파일 삭제: {all_backups[0]}")
                            except Exception as e:
                                logging.error(f"오래된 백업 파일 삭제 실패: {e}")
                        
                        # 백업 파일 경로
                        backup_timestamp = datetime.now().strftime("%H%M%S")
                        backup_filepath = backup_dir / f"backup_{cpName}_{backup_timestamp}.wav"
                        
                        # 현재까지의 데이터를 임시 파일로 저장
                        with wave.open(str(backup_filepath), 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            wf.setsampwidth(2)  # 16비트 = 2바이트
                            wf.setframerate(SAMPLE_RATE)
                            wf.writeframes(b''.join([data.tobytes() for data in recording_data]))
                        
                        # 오래된 백업 파일 정리 (최대 2개 유지)
                        all_backups = sorted(list(backup_dir.glob(f"backup_{cpName}_*.wav")))
                        if len(all_backups) > 2:
                            for old_backup in all_backups[:-2]:
                                try:
                                    os.remove(old_backup)
                                except:
                                    pass
                        
                        logging.info(f"녹음 중간 백업 생성: {backup_filepath}")
                        last_backup_time = current_time  # 백업 시간 업데이트
                    except Exception as e:
                        # 디스크 공간 부족 오류 특별 처리
                        if isinstance(e, OSError) and e.errno == errno.ENOSPC:
                            logging.error(f"백업 생성 중 디스크 공간 부족 오류 발생")
                            asyncio.create_task(show_notification_overlay("디스크 공간이 부족하여 백업을 생성할 수 없습니다.", duration=3))
                        else:
                            logging.error(f"백업 생성 중 오류: {e}")
                
        except asyncio.CancelledError:
            logging.info("녹음 데이터 모니터링 태스크가 취소되었습니다.")
        except Exception as e:
            logging.error(f"녹음 데이터 모니터링 중 예외 발생: {e}")
            # 모니터링 실패 시에도 리스너 활성화 보장
            listener_active = True

    # 모니터링 시작
    asyncio.create_task(monitor_recording_data())

    # 마우스 리스너 재활성화
    async def activate_listener():
        try:
            await asyncio.sleep(0.95)
            global listener_active
            listener_active = True
            logging.info("녹음 종료 가능합니다.")
            await asyncio.sleep(2.2)
            if cpName == "무제":
                asyncio.create_task(show_notification_overlay("환자 이름이 감지되지 않았어요.", duration=2))
        except Exception as e:
            # 예외가 발생해도 listener_active를 True로 설정
            listener_active = True
            logging.error(f"리스너 활성화 중 예외 발생: {str(e)}")

    asyncio.create_task(activate_listener()) # 녹음 시작 후 5초 후 마우스 리스너 재활성화
    recording_timer_task = asyncio.create_task(recording_timer()) # 녹음 타이머 시작

    # 환자 이름 모니터링 태스크 시작
    patient_name_monitor_task = asyncio.create_task(monitor_patient_name())

async def stop_recording():
    """
    녹음 중지 코루틴.
    - 녹음 종료 버튼 클릭 시도
    - 오버레이 종료, 알림 표시
    """
    global overlay_running, recording, listener_active, stream, subfolder
    global cpName, patient_names_list, original_patient_name, patient_name_monitor_task, filename
    global recording_paused, pause_start_time, total_paused_time, paused_audio_data  # 일시정지 관련 변수 추가
    global safety_task  # 안전장치 Task 추가
    
    if not recording:  # 녹음 중이 아니라면 아무 작업도 하지 않음
        logging.warning("녹음이 진행 중이 아닙니다.")
        return
    
    # 안전장치 Task 취소
    if safety_task and not safety_task.done():
        safety_task.cancel()
        try:
            await safety_task
        except asyncio.CancelledError:
            pass
        logging.info("안전장치 Task가 취소되었습니다.")
    
    # 일시정지 상태였다면 먼저 재개하여 남은 데이터 처리
    if recording_paused:
        logging.info("일시정지 상태에서 녹음 종료 - 데이터 병합 중")
        if paused_audio_data:
            recording_data[:] = paused_audio_data
        recording_paused = False
    
    play_audio_fast('AP_Disengage')
    asyncio.create_task(show_notification_overlay("작업이 끝났어요!", duration=1))

    # 마우스 리스너 비활성화
    listener_active = False

    overlay_running = False
    close_overlay()
    
    recording = False

    # 핸들바 오버레이 업데이트
    try:
        update_recording_handle_overlay()
    except Exception as e:
        logging.error(f"핸들바 오버레이 업데이트 실패: {e}")

    # 환자 이름 모니터링 태스크 취소
    if patient_name_monitor_task:
        patient_name_monitor_task.cancel()
        try:
            await patient_name_monitor_task
        except asyncio.CancelledError:
            pass
    
    # 환자 이름 목록에서 최적의 환자 이름 선택
    if len(patient_names_list) > 1:  # 환자 이름이 한 번 이상 감지되었을 경우
        best_patient_name = get_best_patient_name(patient_names_list, default_name=original_patient_name)
        
        # 원래 cpName이 "무제"이고 실제 환자 이름이 감지된 경우 업데이트
        if original_patient_name == "무제" and best_patient_name != "무제":
            logging.info(f"환자 이름 업데이트: {original_patient_name} -> {best_patient_name}")
            
            # cpName 업데이트
            old_name = cpName
            cpName = best_patient_name
            
            # 파일 이름 업데이트 (현재 타임스탬프 유지)
            if filename.startswith(old_name):
                old_timestamp = filename[len(old_name):]  # "_음성_YYMMDD_HHMMSS" 형태의 타임스탬프 추출
                filename = f"{cpName}{old_timestamp}"
                logging.info(f"파일 이름 업데이트: {old_name}{old_timestamp} -> {filename}")
            
            # 사용자에게 알림
            asyncio.create_task(show_notification_overlay(f"환자 '{best_patient_name}'으로 저장합니다.", duration=2))
    
    logging.info("녹음 종료 코루틴 시작.")

    try:
        stream.stop()
        stream.close()

        # 저장 경로 설정
        if SAVE_PATH and os.path.exists(SAVE_PATH):
            # 사용자 설정 경로 사용
            save_directory = Path(SAVE_PATH)
            logging.info(f"사용자 지정 저장 경로 사용: {save_directory}")
        else:
            # 바탕화면 경로 사용 (기본값)
            desktop_path = get_desktop_path()
            save_directory = desktop_path / 'D-Note 파일'
            logging.info(f"기본 저장 경로 사용 (바탕화면): {save_directory}")
        
        # 저장하기 전 디스크 공간 확인
        has_space, free_space_mb = check_disk_space(str(save_directory), required_space_mb=300)  # 약 300MB 필요
        if not has_space:
            logging.warning(f"저장을 위한 디스크 공간 부족: 남은 공간 {free_space_mb:.2f}MB")
            asyncio.create_task(show_notification_overlay(f"디스크 공간이 부족합니다. (남은 공간: {free_space_mb:.0f}MB)", duration=5))
            
            # 공간 부족에도 계속 진행하기 (저장 시도는 함)
            
        # 저장 폴더 확인 및 생성
        if not save_directory.exists():
            os.makedirs(save_directory)

        # 하위 폴더 생성 (환자명+날짜)
        subfolder = save_directory / f"{cpName}_{datetime.now().strftime('%y%m%d_%H%M%S')}"
        if not subfolder.exists():
            os.makedirs(subfolder)

        # 파일 경로 설정
        wav_filepath = subfolder / f"{filename}.wav"

        # 녹음 데이터 병합 및 처리
        try:
            # 녹음 데이터가 비어 있는지 확인
            if not recording_data:
                logging.error("녹음 데이터가 비어 있습니다. 백업 파일에서 복구를 시도합니다.")
                
                # 백업 파일 확인
                backup_dir = Path.home() / 'AppData' / 'Local' / 'dNote' / 'backups'
                if backup_dir.exists():
                    # 현재 녹음과 관련된 백업 파일 검색
                    backup_files = sorted(list(backup_dir.glob(f"backup_{cpName}_*.wav")))
                    
                    if backup_files:
                        # 가장 최근 백업 파일 사용
                        latest_backup = backup_files[-1]
                        logging.info(f"백업 파일 발견: {latest_backup}")
                        
                        # 백업 파일 복사
                        shutil.copy2(str(latest_backup), str(wav_filepath))
                        logging.info(f"백업 파일에서 녹음 복구됨: {latest_backup} -> {wav_filepath}")
                        asyncio.create_task(show_notification_overlay("백업 파일에서 작업이 복구되었습니다.", duration=4))
                        
                        # 백업 파일 처리 후 다음 과정으로 넘어감
                    else:
                        logging.error("백업 파일을 찾을 수 없습니다.")
                        asyncio.create_task(show_notification_overlay("작업/백업 데이터가 없어 파일이 저장되지 않았어요.", duration=4))
                        
                        # 빈 파일 생성 (향후 디버깅 목적)
                        with wave.open(str(wav_filepath), 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            wf.setsampwidth(2)
                            wf.setframerate(SAMPLE_RATE)
                            wf.writeframes(b'')
                else:
                    logging.error("백업 디렉토리가 존재하지 않습니다.")
                    asyncio.create_task(show_notification_overlay("작업 데이터가 비어있어 오디오가 저장되지 않았어요.", duration=4))
                    
                    # 빈 파일 생성 (향후 디버깅 목적)
                    with wave.open(str(wav_filepath), 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(2)
                        wf.setframerate(SAMPLE_RATE)
                        wf.writeframes(b'')
            else:
                # 오디오 데이터를 numpy 배열로 변환
                audio_data = np.concatenate([data for data in recording_data])
                
                # 앞뒤에 음성 파일 추가
                try:
                    # 시작 음성 파일 준비
                    start_voice_data = prepare_audio_for_recording('rec_start_voice', target_db=AUDIO_TARGET_DB)
                    # 종료 음성 파일 준비  
                    stop_voice_data = prepare_audio_for_recording('rec_stop_voice', target_db=AUDIO_TARGET_DB)
                    
                    # 음성 파일이 성공적으로 로드된 경우에만 추가
                    if start_voice_data is not None and stop_voice_data is not None:
                        # 앞에 시작 음성, 녹음 데이터, 뒤에 종료 음성 순서로 결합
                        audio_data = np.concatenate([start_voice_data, audio_data, stop_voice_data])
                        logging.info("녹음 데이터에 시작/종료 음성이 추가되었습니다.")
                    elif start_voice_data is not None:
                        # 시작 음성만 추가
                        audio_data = np.concatenate([start_voice_data, audio_data])
                        logging.info("녹음 데이터에 시작 음성이 추가되었습니다.")
                    elif stop_voice_data is not None:
                        # 종료 음성만 추가
                        audio_data = np.concatenate([audio_data, stop_voice_data])
                        logging.info("녹음 데이터에 종료 음성이 추가되었습니다.")
                    else:
                        logging.warning("시작/종료 음성 파일을 로드할 수 없어 원본 녹음만 저장합니다.")
                        
                except Exception as e:
                    logging.error(f"음성 파일 추가 중 오류 발생: {e}")
                    logging.info("원본 녹음 데이터만 저장합니다.")
                
                # 오디오 처리 기능이 활성화되어 있고 데이터가 int16 타입이면 처리
                if AUDIO_PROCESSING_ENABLED and audio_data.dtype == np.int16:
                    # int16을 float32로 변환 (-1.0 ~ 1.0 범위)
                    audio_float = audio_data.astype(np.float32) / 32768.0
                    
                    # 오디오 처리 적용
                    processed_audio = process_audio(
                        audio_float, 
                        sr=SAMPLE_RATE, 
                        target_db=AUDIO_TARGET_DB
                    )
                    
                    # 다시 int16으로 변환
                    processed_audio_int = (processed_audio * 32767).astype(np.int16)
                    
                    # 처리된 오디오 저장
                    with wave.open(str(wav_filepath), 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(2)  # 16비트 = 2바이트
                        wf.setframerate(SAMPLE_RATE)
                        wf.writeframes(processed_audio_int.tobytes())
                    
                    logging.info("오디오 처리 완료: 볼륨 정규화 및 필터 적용됨")
                else:
                    # 원본 데이터를 그대로 저장
                    with wave.open(str(wav_filepath), 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(2)
                        wf.setframerate(SAMPLE_RATE)
                        wf.writeframes(b''.join([data.tobytes() for data in recording_data]))
        except Exception as e:
            logging.error(f"오디오 처리 중 오류 발생: {e}")
            try:
                # 오류 발생 시 원본 데이터 저장 시도
                if recording_data:
                    with wave.open(str(wav_filepath), 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(2)
                        wf.setframerate(SAMPLE_RATE)
                        wf.writeframes(b''.join([data.tobytes() for data in recording_data]))
                    logging.info("오류 발생 후 원본 데이터 저장 완료")
                else:
                    # 백업 파일 확인
                    backup_dir = Path.home() / 'AppData' / 'Local' / 'dNote' / 'backups'
                    if backup_dir.exists():
                        backup_files = sorted(list(backup_dir.glob(f"backup_{cpName}_*.wav")))
                        if backup_files:
                            # 가장 최근 백업 파일 복사
                            latest_backup = backup_files[-1]
                            shutil.copy2(str(latest_backup), str(wav_filepath))
                            logging.info(f"오류 복구: 백업 파일에서 녹음 복구됨: {latest_backup}")
                            asyncio.create_task(show_notification_overlay("오류 발생, 백업에서 복구되었습니다.", duration=3))
                        else:
                            logging.error("오류 복구 실패: 녹음 데이터가 비어 있고 백업 파일이 없습니다.")
                            with wave.open(str(wav_filepath), 'wb') as wf:
                                wf.setnchannels(CHANNELS)
                                wf.setsampwidth(2)
                                wf.setframerate(SAMPLE_RATE)
                                wf.writeframes(b'')
                    else:
                        logging.error("오류 복구 실패: 녹음 데이터가 비어 있고 백업 디렉토리가 없습니다.")
                        with wave.open(str(wav_filepath), 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            wf.setsampwidth(2)
                            wf.setframerate(SAMPLE_RATE)
                            wf.writeframes(b'')
            except Exception as inner_e:
                logging.error(f"오류 복구 중 추가 예외 발생: {inner_e}")
                # 마지막 시도 - 빈 파일 생성
                with wave.open(str(wav_filepath), 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(2)
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(b'')
        logging.info(f"녹음을 종료합니다. 저장된 파일: {wav_filepath}")

        # MP3 경로 및 변환
        mp3_filepath = subfolder / f"{filename}.mp3"
        try:
            with wave.open(str(wav_filepath), 'rb') as wf:
                encoder = lameenc.Encoder()
                encoder.set_bit_rate(64)
                encoder.set_in_sample_rate(SAMPLE_RATE)
                encoder.set_channels(CHANNELS)
                encoder.set_quality(7)

                mp3_data = b""
                chunk_size = 8192
                while True:
                    data = wf.readframes(chunk_size)
                    if not data:
                        break
                    mp3_data += encoder.encode(data)
                mp3_data += encoder.flush()

                # MP3 저장 전 디스크 공간 확인
                has_space, free_space_mb = check_disk_space(str(subfolder), required_space_mb=50)  # MP3는 작음, 50MB 정도면 충분
                if not has_space:
                    logging.warning(f"MP3 저장을 위한 디스크 공간 부족: 남은 공간 {free_space_mb:.2f}MB")
                    asyncio.create_task(show_notification_overlay("디스크 공간이 부족하여 MP3 압축 파일이 저장되지 않을 수 있습니다.", duration=4))
                
                with open(str(mp3_filepath), 'wb') as mp3_file:
                    mp3_file.write(mp3_data)

            logging.info(f"압축 완료: {mp3_filepath}")

            # WAV 파일이 존재하고 MP3 파일이 성공적으로 생성되었는지 확인 후 삭제
            if os.path.exists(wav_filepath) and os.path.exists(mp3_filepath) and os.path.getsize(mp3_filepath) > 0:
                os.remove(wav_filepath)
                logging.info(f"WAV 파일 삭제 완료: {wav_filepath}")
            else:
                logging.warning("MP3 파일이 제대로 생성되지 않아 WAV 파일을 유지합니다.")
        except OSError as e:
            # 디스크 용량 부족 오류 특별 처리
            if e.errno == errno.ENOSPC:
                logging.error(f"MP3 변환 중 디스크 공간 부족 오류 발생")
                asyncio.create_task(show_notification_overlay("디스크 공간이 부족해 MP3 파일 저장에 실패했습니다. WAV 파일은 유지됩니다.", duration=5))
                # WAV 파일을 삭제하지 않고 유지
            else:
                logging.error(f"MP3 변환 중 OSError 발생: {e}")
                # 다른 유형의 OSError - WAV 파일을 유지
        except Exception as e:
            logging.error(f"MP3 변환 중 예외 발생: {e}")
            # 예외 발생 시 WAV 파일은 유지

    except OSError as e:
        # 디스크 용량 부족 오류 특별 처리
        if e.errno == errno.ENOSPC:
            logging.error(f"녹음 파일 저장 중 디스크 공간 부족 오류 발생")
            asyncio.create_task(show_notification_overlay("디스크 공간이 부족하여 파일을 저장할 수 없습니다. 공간을 확보한 후 다시 시도해 주세요.", duration=6))
            
            # 백업 파일로 복구 시도
            try:
                logging.info("백업 파일에서 복구 시도 중...")
                backup_dir = Path.home() / 'AppData' / 'Local' / 'dNote' / 'backups'
                if backup_dir.exists():
                    backup_files = sorted(list(backup_dir.glob(f"backup_{cpName}_*.wav")))
                    if backup_files:
                        # 임시 폴더 사용 시도
                        temp_dir = Path(os.environ.get('TEMP', os.path.expanduser('~')))
                        temp_subfolder = temp_dir / f"dNote_emergency_{datetime.now().strftime('%y%m%d_%H%M%S')}"
                        try:
                            os.makedirs(temp_subfolder, exist_ok=True)
                            temp_filepath = temp_subfolder / f"{filename}.wav"
                            
                            # 백업 파일 복사
                            latest_backup = backup_files[-1]
                            shutil.copy2(str(latest_backup), str(temp_filepath))
                            
                            asyncio.create_task(show_notification_overlay(f"디스크 공간 부족: 임시 폴더에 파일 저장 - {temp_subfolder}", duration=6))
                        except Exception as temp_e:
                            logging.error(f"임시 폴더 저장 실패: {temp_e}")
                            raise
            except Exception as recovery_e:
                logging.error(f"백업 복구 실패: {recovery_e}")
        else:
            logging.error(f"녹음 중지 중 OSError 발생: {e}")
    except Exception as e:
        logging.error(f"녹음 중지 중 예외 발생: {e}")

    # [변경] stop_recording이 끝난 후에도 이벤트 루프는 바로 돌아가도록,
    # 다운로드/업로드는 백그라운드 Task에서 진행
    try:
        asyncio.create_task(do_download_and_upload_in_background())
    except Exception as e:
        logging.error(f"녹음 종료 처리 중 예외 발생: {e}")

    # stop_recording은 여기서 즉시 반환 -> 메인 이벤트 루프가 새 마우스 입력을 즉시 처리 가능
    async def activate_listener():
        try:
            await asyncio.sleep(0.8)
            global listener_active
            listener_active = True
            logging.info("녹음 시작 가능합니다.")
            
            # 안전장치 타이머 추가 - 리스너가 비활성화되어 있는지 3초마다 확인
            for i in range(3):  # 3번 추가 확인
                await asyncio.sleep(3)
                if not listener_active:
                    listener_active = True
                    logging.warning(f"리스너가 다시 비활성화되어 재활성화합니다 (확인 {i+1}/3)")
        except Exception as e:
            # 예외가 발생해도 listener_active를 True로 설정
            listener_active = True
            logging.error(f"리스너 활성화 중 예외 발생: {e}")

        # 안전장치 타이머 추가
        asyncio.create_task(ensure_listener_recovery())

    asyncio.create_task(activate_listener())

async def cancel_recording():
    """
    녹음 취소 코루틴.
    - 진행 중인 녹음을 저장하지 않고 취소
    - 오버레이 종료, 상태 초기화
    """
    global overlay_running, recording, listener_active, stream, recording_timer_task
    global patient_name_monitor_task
    global recording_paused, pause_start_time, total_paused_time, paused_audio_data  # 일시정지 관련 변수 추가
    
    if not recording:  # 녹음 중이 아니라면 아무 작업도 하지 않음
        logging.warning("취소할 녹음이 없습니다.")
        return
        
    # 안전장치 Task 취소
    if safety_task and not safety_task.done():
        safety_task.cancel()
        try:
            await safety_task
        except asyncio.CancelledError:
            pass
        logging.info("안전장치 Task가 취소되었습니다.")
    
    # 일시정지 관련 변수 초기화
    recording_paused = False
    pause_start_time = None
    total_paused_time = 0
    paused_audio_data = []
    
    # play_audio_fast('cancel')  # 취소 효과음 재생

    # 마우스 리스너 비활성화
    listener_active = False

    # 오버레이 종료
    overlay_running = False
    close_overlay()
    
    # 녹음 타이머 중단
    if recording_timer_task and not recording_timer_task.done():
        recording_timer_task.cancel()
    
    # 환자 이름 모니터링 태스크 취소
    if patient_name_monitor_task:
        patient_name_monitor_task.cancel()
    
    # 녹음 중지 및 데이터 폐기
    try:
        stream.stop()
        stream.close()
        # 녹음 데이터를 저장하지 않고 버림
        global recording_data
        recording_data = []
    except Exception as e:
        logging.error(f"녹음 취소 중 예외 발생: {e}")
    
    # 녹음 상태 초기화
    recording = False

    # 핸들바 오버레이 업데이트
    try:
        update_recording_handle_overlay()
    except Exception as e:
        logging.error(f"핸들바 오버레이 업데이트 실패: {e}")
    
    # 덴트웹 녹음도 취소 처리 (필요시)
    if DENTWEB_RECORDING_ENABLED and record_button_location:
        try:
            # 덴트웹 녹음 취소 로직 (녹음 중지 버튼 클릭 등)
            activate_window(" 덴트웹 :")
            # 필요한 경우 녹음 중지 버튼 클릭 또는 취소 버튼 클릭
            # click_cancel_record_button() 함수가 있다면 호출
        except Exception as e:
            logging.error(f"덴트웹 녹음 취소 중 예외 발생: {e}")
    
    # 사용자에게 알림
    asyncio.create_task(show_notification_overlay("작업이 취소되었습니다.", duration=2))
    
    # 일정 시간 후 리스너 다시 활성화
    async def activate_listener():
        try:
            await asyncio.sleep(0.95)
            global listener_active
            listener_active = True
            logging.info("녹음 시작 가능합니다.")
            
            # 안전장치 타이머 추가 - 리스너가 비활성화되어 있는지 3초마다 확인
            for i in range(3):  # 3번 추가 확인
                await asyncio.sleep(3)
                if not listener_active:
                    listener_active = True
                    logging.warning(f"리스너가 다시 비활성화되어 재활성화합니다 (확인 {i+1}/3)")
        except Exception as e:
            # 예외가 발생해도 listener_active를 True로 설정
            listener_active = True
            logging.error(f"리스너 활성화 중 예외 발생: {e}")

        # 안전장치 타이머 추가
        asyncio.create_task(ensure_listener_recovery())

    asyncio.create_task(activate_listener())

def check_microphone():
    """
    시스템에 마이크가 설치되어 있는지 확인하는 함수 (Windows 전용).
    """
    global mic_detected, input_device_index, SAMPLE_RATE, CHANNELS
    try:
        import sounddevice as sd
        
        # 1. Windows API로 기본 확인
        num_mics = ctypes.windll.winmm.waveInGetNumDevs()
        if num_mics == 0:
            mic_detected = False
            logging.warning("Windows API: 마이크가 감지되지 않았습니다.")
            return False
        
        # 2. sounddevice로 상세 확인
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        if not input_devices:
            mic_detected = False
            logging.warning("sounddevice: 입력 가능한 오디오 디바이스가 없습니다.")
            return False
        
        # 3. 디바이스 능력 확인 및 설정 최적화
        device_caps = get_device_capabilities(input_device_index)
        if device_caps is None:
            # 기본 디바이스로 재시도
            device_caps = get_device_capabilities()
        
        if device_caps:
            # 전역 설정 업데이트
            input_device_index = device_caps['device_index']
            SAMPLE_RATE = device_caps['sample_rate']
            CHANNELS = device_caps['channels']
            
            logging.info(f"마이크 설정 최적화 완료: 디바이스={input_device_index}, 샘플레이트={SAMPLE_RATE}Hz, 채널={CHANNELS}")
            mic_detected = True
            return True
        else:
            mic_detected = False
            logging.warning("마이크 능력 확인 실패")
            return False
            
    except Exception as e:
        mic_detected = False
        logging.error(f"마이크 감지 중 오류 발생: {e}")
        return False
    
def get_device_capabilities(device_index=None):
    """
    오디오 디바이스의 지원 가능한 설정을 확인하는 함수
    """
    try:
        import sounddevice as sd
        
        # 입력 가능한 디바이스 목록 먼저 가져오기
        devices = sd.query_devices()
        input_devices = [(i, d) for i, d in enumerate(devices) if d['max_input_channels'] > 0]
        
        if not input_devices:
            logging.error("입력 가능한 오디오 디바이스가 없습니다.")
            return None
        
        # 지정된 디바이스가 입력 가능한지 확인
        if device_index is not None:
            device_info = sd.query_devices(device_index)
            if device_info['max_input_channels'] == 0:
                logging.warning(f"디바이스 {device_index}는 입력 불가능, 다른 디바이스 검색 중...")
                device_index = None
        
        # 기본 입력 디바이스 사용하거나 첫 번째 입력 가능한 디바이스 사용
        if device_index is None:
            try:
                device_index = sd.default.device[0]  # 기본 입력 디바이스
                device_info = sd.query_devices(device_index)
                if device_info['max_input_channels'] == 0:
                    raise Exception("기본 입력 디바이스가 입력 불가능")
            except:
                # 첫 번째 입력 가능한 디바이스 사용
                device_index = input_devices[0][0]
                logging.info(f"첫 번째 입력 가능한 디바이스 사용: {device_index}")
        
        # 디바이스 정보 가져오기
        device_info = sd.query_devices(device_index)
        logging.info(f"선택된 디바이스 정보: {device_info}")
        
        # 입력 채널이 없으면 실패
        if device_info['max_input_channels'] == 0:
            logging.error(f"디바이스 {device_index}는 입력 채널이 없습니다.")
            return None
        
        # 지원하는 샘플레이트 확인 (낮은 것부터 시도)
        test_sample_rates = [32000, 44100, 48000, 16000, 22050]
        supported_sample_rate = None
        
        for rate in test_sample_rates:
            try:
                sd.check_input_settings(device=device_index, samplerate=rate, channels=1)
                supported_sample_rate = rate
                logging.info(f"지원되는 샘플레이트 발견: {rate}Hz")
                break
            except Exception as e:
                logging.debug(f"샘플레이트 {rate}Hz 지원하지 않음: {e}")
                continue
        
        if supported_sample_rate is None:
            logging.error("지원되는 샘플레이트를 찾을 수 없습니다.")
            return None
        
        # 채널 수 확인 (1채널 우선, 안되면 디바이스 최대 채널 사용)
        supported_channels = 1
        try:
            sd.check_input_settings(device=device_index, samplerate=supported_sample_rate, channels=1)
            supported_channels = 1
        except:
            try:
                max_channels = min(2, device_info['max_input_channels'])
                sd.check_input_settings(device=device_index, samplerate=supported_sample_rate, channels=max_channels)
                supported_channels = max_channels
                logging.info(f"1채널 지원하지 않음, {max_channels}채널 사용")
            except Exception as e:
                logging.error(f"채널 설정 확인 실패: {e}")
                return None
        
        return {
            'device_index': device_index,
            'sample_rate': supported_sample_rate,
            'channels': supported_channels,
            'device_info': device_info
        }
        
    except Exception as e:
        logging.error(f"디바이스 능력 확인 실패: {e}")
        return None

def on_click(x, y, button, pressed):
    """
    마우스 버튼 클릭 감지 함수.
    - TARGET_BUTTON을 PRESS_THRESHOLD초 이상 누르면 녹음 시작/종료
    - SEPARATE_EXTEND_BUTTON이 True인 경우 EXTEND_BUTTON을 EXTEND_THRESHOLD 이상 누르면 녹음 연장
    """
    global recording, listener_active, mic_detected, press_start_time, SET_RECORDING_DURATION
    global wheel_press_start_time, wheel_threshold_timer, wheel_threshold_executed
    global threshold_timer, threshold_executed, target_button_active, wheel_button_active
    global extend_press_start_time, extend_threshold_timer, extend_threshold_executed

    # TARGET_BUTTON이 휠 버튼과 동일한지 확인
    is_target_wheel = (TARGET_BUTTON == mouse.Button.middle)

    # 휠 버튼 처리 - 이전 코드 유지 (녹음 연장 기능과의 호환성을 위해)
    if button == mouse.Button.middle:
        if pressed:
            wheel_press_start_time = time.time()
            wheel_threshold_executed = False
            
            # TARGET_BUTTON 기능 처리 (TARGET_BUTTON이 휠 버튼인 경우)
            if is_target_wheel:
                press_start_time = time.time()
                threshold_executed = False
                target_button_active = True
                
                # 녹음 중이 아닐 때
                if not recording:
                    # recording이 False일 때만 즉시 실행 (IMMEDIATE_THRESHOLD > PRESS_THRESHOLD인 경우)
                    if IMMEDIATE_THRESHOLD > PRESS_THRESHOLD:
                        threshold_executed = True
                        execute_main_action()  # 녹음 시작
                    else:
                        # 녹음 시작을 위한 타이머 설정
                        def execute_threshold_action():
                            global threshold_executed
                            if not threshold_executed and press_start_time is not None:
                                threshold_executed = True
                                execute_main_action()  # 녹음 시작

                        threshold_timer = threading.Timer(PRESS_THRESHOLD, execute_threshold_action)
                        threshold_timer.start()
                # 녹음 중일 때
                else:
                    # 분리 모드인 경우(SEPARATE_EXTEND_BUTTON=True): TARGET_BUTTON은 녹음 종료만 담당
                    if SEPARATE_EXTEND_BUTTON:
                        def execute_threshold_action():
                            global threshold_executed
                            if not threshold_executed and press_start_time is not None:
                                threshold_executed = True
                                execute_main_action()  # 녹음 종료

                        threshold_timer = threading.Timer(PRESS_THRESHOLD, execute_threshold_action)
                        threshold_timer.start()
                    # 통합 모드인 경우(SEPARATE_EXTEND_BUTTON=False): TARGET_BUTTON은 녹음 종료와 연장을 모두 담당
                    # 녹음 연장 기능은 휠 버튼 중간 임계값 처리 부분에서 수행
                    
            
            # 휠 버튼 중간 임계값 처리 - SEPARATE_EXTEND_BUTTON이 False일 때만 실행
            # 이 부분이 녹음 연장 기능임
            if not SEPARATE_EXTEND_BUTTON and recording:
                def execute_wheel_middle_action():
                    global wheel_threshold_executed, threshold_executed
                    if not wheel_threshold_executed and wheel_press_start_time is not None:
                        wheel_threshold_executed = True
                        # 중요: 중간 임계값 기능이 실행되면 TARGET_BUTTON 처리도 완료로 표시
                        if is_target_wheel:
                            threshold_executed = True
                        # 휠 버튼 중간 임계값 기능 실행
                        execute_wheel_middle_function()
                
                wheel_threshold_timer = threading.Timer(PRESS_THRESHOLD_MIDDLE, execute_wheel_middle_action)
                wheel_threshold_timer.start()
            
        else:  # 휠 버튼 떼기
            # 휠 버튼 타이머 취소
            if 'wheel_threshold_timer' in globals() and wheel_threshold_timer and wheel_threshold_timer.is_alive():
                wheel_threshold_timer.cancel()
            
            # TARGET_BUTTON 타이머 취소 (TARGET_BUTTON이 휠 버튼인 경우)
            if is_target_wheel and 'threshold_timer' in globals() and threshold_timer and threshold_timer.is_alive():
                threshold_timer.cancel()
            
            # 휠 버튼 중간 임계값 처리 - SEPARATE_EXTEND_BUTTON이 False일 때만 실행
            if not SEPARATE_EXTEND_BUTTON and wheel_press_start_time is not None:
                duration = time.time() - wheel_press_start_time
                if not wheel_threshold_executed and duration >= PRESS_THRESHOLD_MIDDLE:
                    wheel_threshold_executed = True
                    # 중요: 중간 임계값 기능이 실행되면 TARGET_BUTTON 처리도 완료로 표시
                    if is_target_wheel:
                        threshold_executed = True
                    execute_wheel_middle_function()
                wheel_press_start_time = None
            
            # TARGET_BUTTON 처리 (TARGET_BUTTON이 휠 버튼인 경우)
            # 중간 임계값 기능이 이미 실행되었다면 무시
            if is_target_wheel and press_start_time is not None and not wheel_threshold_executed:
                duration = time.time() - press_start_time
                
                # 녹음 중이 아닐 때: PRESS_THRESHOLD 이상이면 녹음 시작
                if not recording and not threshold_executed and duration >= PRESS_THRESHOLD:
                    execute_main_action()  # 녹음 시작
                
                # 녹음 중일 때
                elif recording:
                    # 통합 모드(SEPARATE_EXTEND_BUTTON=False)일 때
                    if not SEPARATE_EXTEND_BUTTON:
                        # PRESS_THRESHOLD보다 오래 눌렀지만 PRESS_THRESHOLD_MIDDLE보다 짧게 눌렀으면 녹음 종료
                        if not threshold_executed and duration >= PRESS_THRESHOLD and duration < PRESS_THRESHOLD_MIDDLE:
                            execute_main_action()  # 녹음 종료
                        # PRESS_THRESHOLD_MIDDLE 이상은 wheel_threshold_executed에서 처리됨
                    # 분리 모드(SEPARATE_EXTEND_BUTTON=True)일 때
                    else:
                        # PRESS_THRESHOLD 이상 눌렀는데 아직 실행되지 않았으면 녹음 종료
                        if not threshold_executed and duration >= PRESS_THRESHOLD:
                            execute_main_action()  # 녹음 종료
                
                press_start_time = None
                target_button_active = False
            elif is_target_wheel:
                press_start_time = None
                target_button_active = False

    # TARGET_BUTTON 처리 (TARGET_BUTTON이 휠 버튼이 아닌 경우)
    elif button == TARGET_BUTTON:  # 휠 버튼이 아닌 TARGET_BUTTON
        if pressed:
            press_start_time = time.time()
            threshold_executed = False
            target_button_active = True
            
            # 녹음 중이 아닐 때
            if not recording:
                # recording이 False일 때만 즉시 실행 (IMMEDIATE_THRESHOLD > PRESS_THRESHOLD인 경우)
                if IMMEDIATE_THRESHOLD > PRESS_THRESHOLD:
                    threshold_executed = True
                    execute_main_action()
                else:
                    # 녹음 시작을 위한 타이머 설정
                    def execute_threshold_action():
                        global threshold_executed
                        if not threshold_executed and press_start_time is not None:
                            threshold_executed = True
                            execute_main_action()

                    threshold_timer = threading.Timer(PRESS_THRESHOLD, execute_threshold_action)
                    threshold_timer.start()
            # 녹음 중일 때
            else:
                # 분리 모드인 경우(SEPARATE_EXTEND_BUTTON=True): TARGET_BUTTON은 녹음 종료만 담당
                if SEPARATE_EXTEND_BUTTON:
                    def execute_threshold_action():
                        global threshold_executed
                        if not threshold_executed and press_start_time is not None:
                            threshold_executed = True
                            execute_main_action()  # 녹음 종료

                    threshold_timer = threading.Timer(PRESS_THRESHOLD, execute_threshold_action)
                    threshold_timer.start()
                # 통합 모드인 경우(SEPARATE_EXTEND_BUTTON=False): TARGET_BUTTON은 녹음 종료와 연장을 모두 담당
                else:
                    # 녹음 연장을 위한 타이머
                    def execute_target_extend_action():
                        global threshold_executed
                        if not threshold_executed and press_start_time is not None:
                            threshold_executed = True
                            execute_wheel_middle_function()  # 녹음 연장 기능 사용

                    target_extend_timer = threading.Timer(PRESS_THRESHOLD_MIDDLE, execute_target_extend_action)
                    target_extend_timer.start()
            
        else:  # TARGET_BUTTON 떼기
            # 타이머 취소
            if 'threshold_timer' in globals() and threshold_timer and threshold_timer.is_alive():
                threshold_timer.cancel()
            
            if not SEPARATE_EXTEND_BUTTON and 'target_extend_timer' in globals() and target_extend_timer and target_extend_timer.is_alive():
                target_extend_timer.cancel()
            
            # 버튼 뗌: 눌린 지속 시간 계산
            if press_start_time is not None:
                duration = time.time() - press_start_time
                
                # 녹음 중이 아닐 때: PRESS_THRESHOLD 이상이면 녹음 시작
                if not recording and not threshold_executed and duration >= PRESS_THRESHOLD:
                    execute_main_action()  # 녹음 시작
                
                # 녹음 중일 때
                elif recording:
                    # 통합 모드(SEPARATE_EXTEND_BUTTON=False)일 때
                    if not SEPARATE_EXTEND_BUTTON:
                        # PRESS_THRESHOLD보다 오래 눌렀지만 PRESS_THRESHOLD_MIDDLE보다 짧게 눌렀으면 녹음 종료
                        if not threshold_executed and duration >= PRESS_THRESHOLD and duration < PRESS_THRESHOLD_MIDDLE:
                            execute_main_action()  # 녹음 종료
                        # PRESS_THRESHOLD_MIDDLE 이상 눌렀는데 아직 실행되지 않았으면 녹음 연장
                        elif not threshold_executed and duration >= PRESS_THRESHOLD_MIDDLE:
                            execute_wheel_middle_function()  # 녹음 연장
                    # 분리 모드(SEPARATE_EXTEND_BUTTON=True)일 때
                    else:
                        # PRESS_THRESHOLD 이상 눌렀는데 아직 실행되지 않았으면 녹음 종료
                        if not threshold_executed and duration >= PRESS_THRESHOLD:
                            execute_main_action()  # 녹음 종료
                
                press_start_time = None
                target_button_active = False

    # 녹음 연장 버튼 처리 (SEPARATE_EXTEND_BUTTON이 True인 경우)
    if SEPARATE_EXTEND_BUTTON and button == EXTEND_BUTTON:
        if pressed:
            # 녹음 중인 경우에만 연장 기능 활성화
            if recording and listener_active:
                extend_press_start_time = time.time()
                extend_threshold_executed = False
                
                def execute_extend_action():
                    global extend_threshold_executed
                    if not extend_threshold_executed and extend_press_start_time is not None:
                        extend_threshold_executed = True
                        execute_wheel_middle_function()  # 녹음 연장 기능 사용
                
                extend_threshold_timer = threading.Timer(EXTEND_THRESHOLD, execute_extend_action)
                extend_threshold_timer.start()
        else:  # 연장 버튼 떼기
            # 타이머 취소
            if 'extend_threshold_timer' in globals() and extend_threshold_timer and extend_threshold_timer.is_alive():
                extend_threshold_timer.cancel()
            
            # 버튼 뗌: 눌린 지속 시간 계산
            if recording and listener_active and 'extend_press_start_time' in globals() and extend_press_start_time is not None:
                duration = time.time() - extend_press_start_time
                if not extend_threshold_executed and duration >= EXTEND_THRESHOLD:
                    extend_threshold_executed = True
                    execute_wheel_middle_function()
                extend_press_start_time = None

def execute_main_action():
    """주요 기능 실행 (녹음 시작/종료/일시정지 재개 등)"""
    global recording, listener_active, mic_detected, SET_RECORDING_DURATION, recording_paused
    
    if not listener_active:
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("잠시 후 다시 시도하세요.", duration=2),
            loop
        )
        return
    
    # 녹음 중이고 일시정지 상태라면 재개
    if recording and recording_paused:
        asyncio.run_coroutine_threadsafe(resume_recording(), loop)
        return
    
    if not check_license_and_update():
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("라이선스가 인증되지 않았습니다.", duration=4),
            loop
        )
        return

    check_microphone()
    if mic_detected:
        if not recording:
            if not set_recording_duration():
                asyncio.run_coroutine_threadsafe(
                    show_notification_overlay("남은 크레딧이 없습니다.", duration=4),
                    loop
                )
                return
            asyncio.run_coroutine_threadsafe(start_recording(), loop)
        else:
            # 녹음 중이고 일시정지 상태가 아니라면 종료
            asyncio.run_coroutine_threadsafe(stop_recording(), loop)
    else:
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("마이크가 없어 실행할 수 없습니다.", duration=3),
            loop
        )

def execute_wheel_middle_function():
    """휠 버튼 중간 임계값에서 실행할 녹음 시간 추가 함수"""
    global recording, SET_RECORDING_DURATION, REMAINING_CREDITS
    
    # 녹음 중이 아니면 실행하지 않음
    if not recording:
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("녹음 중이 아닙니다!", duration=2),
            loop
        )
        return
    
    # 필요한 크레딧 계산 (분 단위)
    required_credits = (SET_RECORDING_DURATION + RECORDING_EXTENSION_TIME) / 60
    
    # 크레딧 부족 여부 체크
    if REMAINING_CREDITS < required_credits:
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay(f"크레딧이 부족해 시간을 연장할 수 없어요!", duration=3),
            loop
        )
        return
    
    # 최대 녹음 시간 체크
    if SET_RECORDING_DURATION + RECORDING_EXTENSION_TIME > MAX_RECORDING_TIME:
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay(f"최대 녹음 시간({int(MAX_RECORDING_TIME / 60)}분)을 초과할 수 없어요!", duration=2),
            loop
        )
        return
    
    # 녹음 시간 추가 (크레딧 차감은 서버에서 처리)
    extend_recording_time(RECORDING_EXTENSION_TIME)

    play_audio_fast('NoA_Engage')
    
    # 사용자에게 알림
    asyncio.run_coroutine_threadsafe(
        show_notification_overlay(f"작업시간을 5분 연장했습니다! (총 작업시간: {int((SET_RECORDING_DURATION) / 60)}분)", duration=2),
        loop
    )

def extend_recording_time(extension_seconds):
    """녹음 시간을 연장하고 관련 UI 및 타이머를 업데이트하는 함수"""
    global SET_RECORDING_DURATION, recording_timer_task, overlay_total_time
    
    # 최대 시간 체크 (안전장치)
    if SET_RECORDING_DURATION + extension_seconds > MAX_RECORDING_TIME:
        extension_seconds = MAX_RECORDING_TIME - SET_RECORDING_DURATION
        if extension_seconds <= 0:
            return
    
    # 1. 녹음 시간 연장
    SET_RECORDING_DURATION += extension_seconds
    
    # 2. 기존 타이머 취소 및 새 타이머 시작
    asyncio.run_coroutine_threadsafe(restart_recording_timer(), loop)
    
    # 3. UI 업데이트 (오버레이가 실행 중인 경우)
    if 'overlay_running' in globals() and overlay_running and 'overlay' in globals():
        # 전역 총 시간 변수 업데이트
        elapsed_time = time.time() - start_time
        original_progress_ratio = elapsed_time / overlay_total_time
        
        # 새로운 총 시간 계산
        new_total_time = overlay_total_time + extension_seconds
        new_progress_ratio = elapsed_time / new_total_time
        
        # 오버레이 총 시간 업데이트
        overlay_total_time = new_total_time
            
        # 애니메이션 시작
        if hasattr(overlay, 'start_progress_animation'):
            overlay.start_progress_animation(original_progress_ratio, new_progress_ratio)

async def restart_recording_timer():
    """기존 녹음 타이머를 취소하고 새로운 타이머를 시작합니다."""
    global recording_timer_task, rid
    
    # 기존 타이머 취소
    if recording_timer_task and not recording_timer_task.done():
        recording_timer_task.cancel()
        try:
            await recording_timer_task
        except asyncio.CancelledError:
            pass  # 예상된 취소
    
    # 새 타이머 시작
    recording_timer_task = asyncio.create_task(recording_timer())

def create_image(path=None):
    if path:  # 사용자 지정 이미지가 있는 경우
        return Image.open(path).resize((64, 64))
    else:  # 기본 이미지 생성
        width = 64
        height = 64
        color1 = "black"
        color2 = "white"

        image = Image.new("RGB", (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle(
            (width // 4, height // 4, width * 3 // 4, height * 3 // 4),
            fill=color2
        )
        return image

def start_recording_via_tray(icon, item):
    if not listener_active:
        # 안내 오버레이를 표시
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("잠시 후 다시 시도하세요.", duration=2),
            loop
        )
        return

    check_microphone()
    if mic_detected:
        if not recording:
            if not set_recording_duration():
                asyncio.run_coroutine_threadsafe(
                    show_notification_overlay("남은 크레딧이 없습니다.", duration=4),
                    loop
                )
                return
            asyncio.run_coroutine_threadsafe(start_recording(), loop)
        else:
            asyncio.run_coroutine_threadsafe(
                show_notification_overlay("이미 녹음중입니다.", duration=3),
                loop
        )
    else:
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("마이크가 없어 실행할 수 없습니다.", duration=3),
            loop
        )

def stop_recording_via_tray(icon, item):
    if not listener_active:
        # 안내 오버레이를 표시
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("잠시 후 다시 시도하세요.", duration=2),
            loop
        )
        return

    if not recording:
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("진행중인 작업이 없습니다.", duration=3),
            loop
    )
    else:
        asyncio.run_coroutine_threadsafe(stop_recording(), loop)

def cancel_recording_via_tray(icon, item):
    if not listener_active:
        # 안내 오버레이를 표시
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("잠시 후 다시 시도하세요.", duration=2),
            loop
        )
        return

    if not recording:
        asyncio.run_coroutine_threadsafe(
            show_notification_overlay("진행중인 작업이 없습니다.", duration=3),
            loop
    )
    else:
        asyncio.run_coroutine_threadsafe(cancel_recording(), loop)

# 라이선스 인증 함수 수정 - 평가판 등록 기능 추가
def license_verify():
    global USE_TRIAL_MODE, TRIAL_INFO, USER_NAME, USER_EMAIL, REMAINING_CREDITS, IS_ACTIVE

    original_trial_mode = USE_TRIAL_MODE
    original_trial_info = TRIAL_INFO
    
    # # 현재 라이선스 또는 평가판 상태 확인
    # if USE_TRIAL_MODE and TRIAL_INFO:
    #     if not messagebox.askyesno("평가판 초기화", 
    #                             "현재 평가판이 등록되어 있습니다.\n평가판을 초기화하고 라이선스를 등록하시겠습니까?"):
    #         return True
    #     # 평가판 모드 해제
    #     USE_TRIAL_MODE = False
    #     set_trial_mode(False, None)
    # elif check_license_and_update() and not USE_TRIAL_MODE:
    #     if not messagebox.askyesno("라이선스 초기화", 
    #                             "현재 라이선스가 인증되어 있습니다.\n등록된 라이선스 정보를 초기화하시겠습니까?"):
    #         return True
    #     # 라이선스 삭제
    #     validator = LicenseValidator()
    #     validator.delete_license_info()
    #     print("라이선스 정보가 삭제되었습니다.")



    # 라이선스 또는 평가판 선택 옵션
    # choice = messagebox.askquestion("인증 방식 선택", 
    #                             "라이선스를 등록하시겠습니까?\n\n'아니오'를 선택하면 평가판으로 진행합니다.")
    USE_TRIAL_MODE = False  # 기본값 설정
    set_trial_mode(False, None)
    choice = 'yes' # 선택 없음

    if check_license_and_update() and not USE_TRIAL_MODE:
        if not messagebox.askyesno("라이선스 초기화", 
                                "현재 라이선스가 인증되어 있습니다.\n등록된 라이선스 정보를 초기화하시겠습니까?"):
            return True
        # 라이선스 삭제
        validator = LicenseValidator()
        validator.delete_license_info()
        choice = 'no'  # 평가판으로 진행
        logging.info("라이선스 정보가 삭제되었습니다.")
    
    if choice == 'yes':  # 라이선스 등록 선택
        # 결과 값을 저장할 객체
        result_container = {"authenticated": False, "completed": False}
        
        def on_verification_complete(authenticated):
            result_container["authenticated"] = authenticated
            result_container["completed"] = True
            logging.info(f"인증 결과: {authenticated}")
        
        # LicenseValidator 실행
        validator = LicenseValidator()
        root.update()  # UI 업데이트
        
        # 검증 창 표시
        validator.verify_license_with_callback(on_verification_complete)
        
        # 검증 창이 완료될 때까지 메인 루프 실행 (모달처럼 작동)
        while not result_container["completed"]:
            root.update()  # 메인 루프 업데이트
            time.sleep(0.04)  # CPU 사용량 감소
        
        # 인증 결과 처리
        if result_container["authenticated"]:
            logging.info("라이선스 인증 성공!")
            USE_TRIAL_MODE = False
            set_trial_mode(False, None)
            if not check_license_and_update():
                USER_NAME = "사용자"
                REMAINING_CREDITS = 0
                IS_ACTIVE = True
                return True

            
            # # 라이선스 정보 로드 및 업데이트
            # success, license_info = validator.get_license_info()
            # if success:
            #     USER_EMAIL = license_info.get("email", "")
                
            #     # 서버에서 추가 정보 가져오기 시도
            #     try:
            #         auth_success, auth_data = validator.authenticate_license(
            #             USER_EMAIL, license_info.get("license_key", ""), True
            #         )
                    
            #         if auth_success and isinstance(auth_data, dict):
            #             USER_NAME = auth_data.get("name", "사용자")
            #             REMAINING_CREDITS = auth_data.get("remaining_credits", 0)
            #             IS_ACTIVE = True
            #             return True
            #     except Exception as e:
            #         print(f"라이선스 정보 갱신 중 오류: {e}")
            
            # # 기본값 설정
            # USER_NAME = "인증된 사용자"
            # REMAINING_CREDITS = 0
            # IS_ACTIVE = True
            return True
        else:
            logging.info("라이선스 인증 취소됨")
            # 이전 평가판 상태로 복원
            if original_trial_mode and original_trial_info:
                USE_TRIAL_MODE = original_trial_mode
                TRIAL_INFO = original_trial_info
                USER_NAME = original_trial_info.get("dental_name", "평가판 사용자")
                REMAINING_CREDITS = original_trial_info.get("remaining_credits", 0)
                IS_ACTIVE = True
                set_trial_mode(True, TRIAL_INFO)
                # messagebox.showinfo("인증 취소", "라이선스 인증이 취소되었습니다. 평가판으로 계속 사용됩니다.")
            return False
        
    else:  # 평가판 선택
    # 먼저 현재 IP가 평가판에 이미 등록되어 있는지 확인
        trial_client = DentalTrialClient()
        trial_status = trial_client.get_trial_status()
        
        if trial_status and (trial_status.get("status") == "active" or trial_status.get("is_active")):
            # 이미 평가판 등록된 IP라면 그 정보를 사용
            USER_NAME = trial_status.get("dental_name", "평가판 사용자")
            USER_EMAIL = ""  # 평가판은 이메일 없음
            REMAINING_CREDITS = trial_status.get("remaining_credits", 0)
            IS_ACTIVE = True
            TRIAL_INFO = trial_status
            
            # 평가판 모드 설정
            USE_TRIAL_MODE = True
            set_trial_mode(True, TRIAL_INFO)
            # messagebox.showinfo("평가판 상태", f"'{USER_NAME}' 계정으로 평가판이 등록되었습니다.")
            return True
        
        dental_name = custom_askstring("치과명 입력", "평가판으로 사용할 치과 이름을 입력해주세요:")

        if dental_name is None:  # 취소 버튼 처리
            messagebox.showinfo("평가판 등록 취소", "평가판 등록이 취소되었습니다.")
            # 이전 평가판 상태로 복원
            if original_trial_mode and original_trial_info:
                USE_TRIAL_MODE = original_trial_mode
                TRIAL_INFO = original_trial_info
                set_trial_mode(True, TRIAL_INFO)
                return True
            return False

        if dental_name:
            trial_status = trial_client.check_trial(dental_name)
            if trial_status:
                logging.info("평가판이 등록되었습니다.")
                USER_NAME = trial_status.get("dental_name", "평가판 사용자")
                REMAINING_CREDITS = trial_status.get("remaining_credits", 0)
                IS_ACTIVE = True
                TRIAL_INFO = trial_status
                
                # 평가판 모드 설정
                USE_TRIAL_MODE = True
                set_trial_mode(True, TRIAL_INFO)
                return True
    
    return False
        
# 라이선스 크레딧 확인 (평가판 포함)
def check_license_and_update(info=True):
    """
    라이선스 크레딧 확인 함수.
    - 라이선스 정보가 없거나 유효하지 않으면 평가판 모드 확인
    - 라이선스 또는 평가판이 유효하면 True 반환
    """
    global USER_NAME, USER_EMAIL, REMAINING_CREDITS, IS_ACTIVE, USE_TRIAL_MODE, TRIAL_INFO, EXP_AT

    # 먼저 정식 라이선스 확인
    validator = LicenseValidator()
    license_success, license_result = validator.get_license_info()

    if license_success:
        # 라이선스 정보 추출
        email = license_result.get("email")
        license_key = license_result.get("license_key")

        license_valid, license_result = validator.authenticate_license(email, license_key, get_data=True)

        if license_valid:
            USER_NAME = license_result.get("license_info", {}).get("name", "")
            USER_EMAIL = license_result.get("license_info", {}).get("email", "")
            REMAINING_CREDITS = license_result.get("license_info", {}).get("remaining_credits", 0)
            IS_ACTIVE = license_result.get("license_info", {}).get("is_active", False)
            EXP_AT = license_result.get("license_info", {}).get("expires_at", None)
            if info:
                logging.info(f"라이선스가 확인되었습니다.\n사용자: {USER_NAME}, 남은 크레딧: {REMAINING_CREDITS}, 활성 상태: {IS_ACTIVE}")
            
            # 라이선스 모드 설정
            USE_TRIAL_MODE = False
            set_trial_mode(False, None)
            return True
    
    # 라이선스가 없거나 유효하지 않으면 평가판 확인
    if info:
        logging.info("라이선스가 없거나 유효하지 않습니다. 평가판 모드 확인...")
    trial_client = DentalTrialClient()
    trial_status = trial_client.get_trial_status()
    
    if trial_status and (trial_status.get("status") == "active" or trial_status.get("is_active")):
        USER_NAME = trial_status.get("dental_name", "평가판 사용자")
        USER_EMAIL = ""  # 평가판은 이메일 없음
        REMAINING_CREDITS = trial_status.get("remaining_credits", 0)
        IS_ACTIVE = True
        TRIAL_INFO = trial_status
        if info:
            logging.info(f"'{USER_NAME}' 로 평가판이 확인되었습니다.")
        
        # 평가판 모드 설정
        USE_TRIAL_MODE = True
        set_trial_mode(True, TRIAL_INFO)
        return True
    
    # 처음 실행 시 평가판 등록
    if not trial_status or trial_status.get("status") == "not_found":
        dental_name = custom_askstring("치과명 입력", "평가판으로 사용할 치과 이름을 입력해주세요:")
        if dental_name:
            trial_status = trial_client.check_trial(dental_name)
            if trial_status:
                logging.info("평가판이 등록되었습니다.")
                USER_NAME = trial_status.get("dental_name", "평가판 사용자")
                REMAINING_CREDITS = trial_status.get("remaining_credits", 0)
                IS_ACTIVE = True
                TRIAL_INFO = trial_status
                
                # 평가판 모드 설정
                USE_TRIAL_MODE = True
                set_trial_mode(True, TRIAL_INFO)
                return True
        elif dental_name is None:  # 취소 버튼 누른 경우
            messagebox.showinfo("평가판 등록 취소", "평가판 등록이 취소되었습니다.")
            return False
    
    logging.info("라이선스 또는 평가판이 확인되지 않았습니다.")
    return False

# 상단에 전역 변수 추가
# 창이 열리는 중인지 추적하는 플래그 변수
opening_settings_window = False

def open_settings_window():
    global PRESS_THRESHOLD, TARGET_BUTTON, MAX_RECORDING_DURATION, USE_TRIAL_MODE, TRIAL_INFO
    global REMAINING_CREDITS, MODEL_MODE, USER_NAME, USER_EMAIL, EXP_AT, DENTWEB_RECORDING_ENABLED, ALLOWED_LANGUAGES
    global opening_settings_window, SAVE_PATH  # SAVE_PATH 추가
    global DENTWEB_CHART_UPLOAD_ENABLED  # 차트 업로드 기능 추가
    global UPLOAD_FILES_TO_DENTWEB  # 파일 업로드 기능 추가
    global DELETE_ORIGINAL_AUDIO_ENABLED  # 원본 음성 파일 삭제 옵션 추가

    # SAVE_PATH가 정의되지 않은 경우 초기화
    try:
        if 'SAVE_PATH' not in globals():
            global SAVE_PATH
            SAVE_PATH = None
    except Exception as e:
        logging.error(f"SAVE_PATH 초기화 중 오류: {e}")
        SAVE_PATH = None
    
    # 창이 이미 열리는 중이면 중복 실행 방지
    if opening_settings_window:
        logging.info("환경설정 창이 이미 열리는 중입니다.")
        return
    
    # 기존 열려있는 창 확인
    if DentalAssistApp._instance is not None and DentalAssistApp._instance.winfo_exists():
        logging.info("환경설정 창이 이미 열려있습니다. 창을 활성화합니다.")
        DentalAssistApp._instance.lift()
        DentalAssistApp._instance.focus_force()
        return
    
    # 잠금 설정
    opening_settings_window = True
    
    try:
        check_license_and_update(info=False)  # 라이선스 확인 (정보는 표시하지 않음)
        
        # 사용자 정보 구성
        user_info = {
            "user_id": USER_NAME,
            "user_email": USER_EMAIL if not USE_TRIAL_MODE else "",
            "license_type": MODEL_MODE,
            "points": REMAINING_CREDITS,
            "expiry_date": TRIAL_INFO.get("expires_at", "").split("T")[0] if USE_TRIAL_MODE and TRIAL_INFO else EXP_AT.split("T")[0],
            "days_left": (datetime.fromisoformat(TRIAL_INFO.get("expires_at", datetime.now().isoformat())).date() - datetime.now().date()).days if USE_TRIAL_MODE and TRIAL_INFO else (datetime.fromisoformat(EXP_AT).date() - datetime.now().date()).days,
            "recording_time": int(MAX_RECORDING_DURATION / 60)
        }

        # 모드 변경 콜백 함수
        def on_mode_change(mode):
            global MODEL_MODE
            MODEL_MODE = mode
            logging.info(f"모드가 {mode}로 변경되었습니다.")
            save_settings()  # 설정 저장
        
        # 녹음 시간 변경 콜백 함수
        def on_recording_time_change(minutes):
            global MAX_RECORDING_DURATION
            MAX_RECORDING_DURATION = minutes * 60  # 분을 초로 변환
            logging.info(f"최대 녹음 시간이 {minutes}분({MAX_RECORDING_DURATION}초)으로 설정되었습니다.")
            save_settings()  # 설정 저장
        
        # 저장 경로 변경 콜백 함수 추가
        def on_save_path_change(new_path):
            global SAVE_PATH
            # None이거나 존재하는 경로인 경우만 처리
            if new_path is None or os.path.exists(new_path):
                SAVE_PATH = new_path
                logging.info(f"저장 경로가 변경되었습니다: {SAVE_PATH if SAVE_PATH else '기본 경로(바탕화면)'}")
                save_settings()  # 설정 저장
                return True
            else:
                logging.warning(f"존재하지 않는 경로입니다: {new_path}")
            return False
    
        # 차트 업로드 기능 변경 콜백 함수 추가
        def on_chart_upload_change(enabled):
            global DENTWEB_CHART_UPLOAD_ENABLED
            DENTWEB_CHART_UPLOAD_ENABLED = enabled
            logging.info(f"차트 업로드 기능이 {'활성화' if enabled else '비활성화'}되었습니다.")
            save_settings()  # 설정 저장
        
        # 파일 업로드 기능 변경 콜백 함수 추가
        def on_file_upload_change(enabled):
            global UPLOAD_FILES_TO_DENTWEB
            UPLOAD_FILES_TO_DENTWEB = enabled
            logging.info(f"차트 파일 업로드 기능이 {'활성화' if enabled else '비활성화'}되었습니다.")
            save_settings()  # 설정 저장
        
        # 차트 프로그램 변경 콜백 함수 추가
        def on_chart_program_change(program_name):
            global CHART_PROGRAM
            old_program = CHART_PROGRAM
            CHART_PROGRAM = program_name
            logging.info(f"차트 프로그램이 {old_program}에서 {program_name}으로 변경되었습니다.")
            
            # 차트 프로그램 매니저 업데이트
            try:
                if set_chart_program(CHART_PROGRAM):
                    logging.info(f"차트 프로그램 매니저 업데이트 완료: {CHART_PROGRAM}")
                else:
                    logging.error(f"차트 프로그램 매니저 업데이트 실패: {CHART_PROGRAM}")
                    # 실패 시 이전 설정으로 복원
                    CHART_PROGRAM = old_program
                    set_chart_program(CHART_PROGRAM)
            except Exception as e:
                logging.error(f"차트 프로그램 변경 중 오류: {e}")
                # 오류 발생 시 이전 설정으로 복원
                CHART_PROGRAM = old_program
                set_chart_program(CHART_PROGRAM)
            
            save_settings()  # 설정 저장
        
        # 알림 UI 표시 기능 변경 콜백 함수 추가
        def on_notification_overlay_change(enabled):
            global SHOW_NOTIFICATION_OVERLAY
            SHOW_NOTIFICATION_OVERLAY = enabled
            logging.info(f"알림 UI 표시 기능이 {'활성화' if enabled else '비활성화'}되었습니다.")
            save_settings()  # 설정 저장

        # 요약 길이 변경 콜백 함수 추가 (on_recording_time_change 함수 다음에):
        def on_summary_length_change(length_setting):
            global SUMMARY_LENGTH_SETTING
            SUMMARY_LENGTH_SETTING = length_setting
            logging.info(f"요약 길이 설정이 {length_setting}로 변경되었습니다.")
            save_settings()  # 설정 저장

        def on_delete_audio_change(enabled):
            global DELETE_ORIGINAL_AUDIO_ENABLED
            DELETE_ORIGINAL_AUDIO_ENABLED = enabled
            logging.info(f"원본 음성 파일 삭제 옵션이 {'활성화' if enabled else '비활성화'}되었습니다.")
            save_settings()  # 설정 저장

        # DentalAssistApp 창 열기
        settings_app = DentalAssistApp.get_instance(
            parent=root,
            user_info=user_info,
            on_mode_change=on_mode_change,
            on_recording_time_change=on_recording_time_change,
            on_save_path_change=on_save_path_change,
            on_chart_upload_change=on_chart_upload_change,
            on_file_upload_change=on_file_upload_change,
            current_chart_program=CHART_PROGRAM,
            on_chart_program_change=on_chart_program_change,
            on_notification_overlay_change=on_notification_overlay_change,
            on_summary_length_change=on_summary_length_change,
            on_delete_audio_change=on_delete_audio_change,
            license_verify=license_verify,
            main_quit_function=quit_program,  # 메인 종료 함수 전달
            version=VERSION,  # 버전 정보 전달
            save_path=SAVE_PATH if 'SAVE_PATH' in globals() else None,  # 저장 경로 전달 (안전 처리)
            toggle_console_callback=toggle_console,  # 콘솔 창 토글 콜백 함수 전달
            chart_upload_enabled=DENTWEB_CHART_UPLOAD_ENABLED,  # 차트 업로드 기능 현재 상태 전달
            file_upload_enabled=UPLOAD_FILES_TO_DENTWEB,  # 파일 업로드 기능 현재 상태 전달
            notification_overlay_enabled=SHOW_NOTIFICATION_OVERLAY,  # 알림 UI 표시 기능 현재 상태 전달
            summary_length_setting=SUMMARY_LENGTH_SETTING,  # 요약 길이 설정 현재 상태 전달
            delete_audio_enabled=DELETE_ORIGINAL_AUDIO_ENABLED  # 원본 음성 파일 삭제 옵션 현재 상태 전달
        )

        # 설정 변경 시 저장 함수 오버라이드
        original_on_close = settings_app.on_close
        def extended_on_close():
            global opening_settings_window, SAVE_PATH
            
            # SAVE_PATH가 존재하지 않는 경로로 설정되었는지 확인
            if SAVE_PATH and not os.path.exists(SAVE_PATH):
                logging.warning(f"설정된 저장 경로가 존재하지 않습니다: {SAVE_PATH}")
                # 존재하지 않는 경로면 None으로 재설정
                SAVE_PATH = None
                
            save_settings()  # 설정 저장
            original_on_close()  # 원래 종료 메서드 호출
            opening_settings_window = False  # 잠금 해제
        
        settings_app.on_close = extended_on_close
        
        # 사용자 정보 갱신 메소드 오버라이드
        def update_app_user_info():
            # 라이선스 인증 후 전역 변수가 변경되었을 것이므로
            # 새 정보로 업데이트된 사용자 정보 딕셔너리 생성
            updated_user_info = {
                "user_id": USER_NAME,
                "user_email": USER_EMAIL if not USE_TRIAL_MODE else "",
                "license_type": MODEL_MODE,
                "points": REMAINING_CREDITS,
                "expiry_date": TRIAL_INFO.get("expires_at", "").split("T")[0] if USE_TRIAL_MODE and TRIAL_INFO else EXP_AT.split("T")[0],
                "days_left": (datetime.fromisoformat(TRIAL_INFO.get("expires_at", datetime.now().isoformat())).date() - datetime.now().date()).days if USE_TRIAL_MODE and TRIAL_INFO else (datetime.fromisoformat(EXP_AT).date() - datetime.now().date()).days,
                "recording_time": int(MAX_RECORDING_DURATION / 60)
            }
            
            # UI 요소 업데이트
            settings_app.user_info = updated_user_info
            
            # 사용자 ID 라벨 갱신 - 이메일 유무에 따라 다르게 표시
            text_value = (f"{updated_user_info['user_id']} ({updated_user_info['user_email']})" 
                        if updated_user_info['user_email'] 
                        else f"{updated_user_info['user_id']}")
            settings_app.user_id_value.configure(text=text_value)
            
            # 포인트 라벨 갱신
            settings_app.point_value.configure(text=f"{updated_user_info['points']} point")
            
            # 만료일 라벨 갱신
            settings_app.expiry_value.configure(
                text=f"{updated_user_info['expiry_date']} ({updated_user_info['days_left']}일 남음)"
            )
        
        # 메소드 할당
        settings_app.update_user_info = update_app_user_info
    
    except Exception as e:
        logging.error(f"환경설정 창 열기 중 오류 발생: {e}")
    finally:
        # 작업 완료 후 잠금 해제
        opening_settings_window = False

def quit_program(icon=None, item=None):
    """모든 리소스를 정리하고 프로그램을 완전히 종료합니다."""
    global listener, recording, overlay_running, loop

    if recording or uploading:
        if not messagebox.askyesno("종료 확인", 
                                "녹음 또는 업로드가 진행 중입니다. 정말 종료하시겠습니까?"):
            return
    
    # 설정 저장
    save_settings()
    
    # 커서 체크 타이머 중지 및 커서 상태 확인
    try:
        from cursor_utils import stop_cursor_check_timer, restore_default_cursor, cursor_blocked_state
        stop_cursor_check_timer()
        
        # 혹시 모를 경우를 대비해 커서 상태 한 번 더 확인
        if cursor_blocked_state:
            logging.warning("프로그램 종료 시 커서가 여전히 차단된 상태입니다. 최종 복원 시도.")
            restore_default_cursor()
    except Exception as e:
        logging.error(f"커서 타이머 중지 중 오류: {e}")
        # 오류 발생 시 직접 복원 시도
        try:
            from cursor_utils import restore_default_cursor
            restore_default_cursor()
        except:
            pass
        
    # 트레이 아이콘 제거
    if icon:
        icon.stop()

    # 마우스 리스너 종료
    if listener:
        listener.stop()
        
    # 녹음 중이라면 중지
    if recording:
        close_overlay()
    
    # 열린 오버레이 종료
    if overlay_running and overlay:
        try:
            overlay.destroy()
        except:
            pass

    try:
        close_recording_handle_overlay()
    except Exception as e:
        logging.error(f"녹음 핸들바 오버레이 정리 실패: {e}")

    try:
        close_dictation_handle_overlay()
    except Exception as e:
        logging.error(f"받아쓰기 핸들바 오버레이 정리 실패: {e}")
    
    # asyncio 이벤트 루프에서 실행 중인 모든 작업 취소
    for task in asyncio.all_tasks(loop):
        task.cancel()
    
    # 이벤트 루프 중지
    loop.call_soon_threadsafe(loop.stop)
    
    # 모든 스레드와 프로세스를 강제 종료
    logging.info("프로그램을 종료합니다.")
    os._exit(0)  # 모든 프로세스 즉시 종료

def hide_console():
    """콘솔 창 숨기기"""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
            return True
        return False
    except Exception as e:
        logging.info(f"hide_console 오류: {e}")
        return False

def show_console():
    """콘솔 창 보이기 또는 새로 생성"""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # 콘솔 창이 존재하면 표시
            ctypes.windll.user32.ShowWindow(hwnd, 1)
            return True
        else:
            # 콘솔 창이 없으면 새로 생성 (--noconsole 환경)
            if ctypes.windll.kernel32.AllocConsole():
                # 새 콘솔 생성 성공
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    # 콘솔 창 제목 설정
                    ctypes.windll.kernel32.SetConsoleTitleW("dNote 콘솔")
                    
                    # 표준 입출력을 새 콘솔로 리디렉션
                    import sys
                    sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
                    sys.stderr = open('CONOUT$', 'w', encoding='utf-8')
                    sys.stdin = open('CONIN$', 'r', encoding='utf-8')
                    
                    logging.info("dNote 콘솔 창이 생성되었습니다.")
                    print("이 창에서 디버그 정보를 확인할 수 있습니다.")
                    
                    # 콘솔 로깅 핸들러 다시 설정
                    reinitialize_console_logging()
                    
                    return True
            return False
    except Exception as e:
        print(f"show_console 오류: {e}")
        return False

def toggle_console():
    """콘솔 창 보이기/숨기기 토글"""
    try:
        print("toggle_console 함수가 호출되었습니다.")  # 디버그 로그 추가
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        
        if hwnd:
            # 콘솔 창이 존재하는 경우
            is_visible = ctypes.windll.user32.IsWindowVisible(hwnd)
            print(f"콘솔 창 현재 상태: {'보임' if is_visible else '숨김'}")  # 상태 로그 추가
            if is_visible:
                print("콘솔 창을 숨깁니다.")
                hide_console()
            else:
                print("콘솔 창을 표시합니다.")
                show_console()
        else:
            # 콘솔 창이 없는 경우 (--noconsole 환경)
            print("콘솔 창이 없어서 새로 생성합니다.")
            success = show_console()
            if not success:
                print("콘솔 창 생성에 실패했습니다.")
    except Exception as e:
        print(f"toggle_console 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

# 트레이 메뉴 통합
menu = Menu(
    # MenuItem("녹음 시작", start_recording_via_tray),
    # MenuItem("녹음 종료", stop_recording_via_tray),
    # MenuItem("녹음 취소", cancel_recording_via_tray),
    # Menu.SEPARATOR,
    MenuItem("환경설정", open_settings_window, default=True),
    # MenuItem("업데이트 확인", lambda icon, item: check_updates_manually()),
    # MenuItem("콘솔 창 On/Off", lambda icon, item: toggle_console()),
    # # MenuItem("라이선스 인증", license_verify),
    # Menu.SEPARATOR,
    MenuItem("프로그램 종료", quit_program)
)

# 트레이 아이콘 생성
icon_path = resource_path(f"src\\img\\app\\icon.ico")
icon = Icon("dNote", create_image(icon_path), "dNote", menu)

def run_tray():
    icon.run()

# 콘솔 숨기기
hide_console()

listener_active = True
listener = mouse.Listener(on_click=on_click)
listener.start()

print("서비스가 시작되었습니다 \n")

check_microphone()
print("마우스 휠(기본값) 클릭으로 녹음 시작/종료를 토글할 수 있습니다.")

# # 로딩 화면 닫기
# loading_screen.destroy()

if not check_license_and_update():
    # 라이선스나 평가판이 없으면 라이선스 등록 또는 평가판 등록 창 표시
    if not license_verify():
        messagebox.showerror("인증 실패", "라이선스 또는 평가판 등록이 필요합니다.")
        icon.stop()
        os._exit(0)

def main():
    """
    메인 함수: 마우스 리스너 유지, 종료 시 리소스 정리.
    """
    global listener, driver, update_manager
    
    # Sentry 초기화 및 전역 예외 처리기 설정
    initialize_sentry()
    setup_global_exception_handler()
    
    # 로깅 시작 및 환경 정보 기록
    logger.info("-" * 80)
    logger.info(f"dNote 애플리케이션 시작 (버전: {VERSION})")
    logger.info(f"OS: {platform.system()} {platform.version()}")
    logger.info(f"Python: {platform.python_version()}")
    logger.info(f"로깅 경로: {os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'dNote', 'logs', 'dnote_main.log')}")
    
    # 주요 설정 상태 로그 기록
    logger.info(f"모델 모드: {MODEL_MODE}")
    logger.info(f"최대 녹음 시간: {MAX_RECORDING_DURATION // 60}분")
    logger.info(f"덴트웹 녹음 기능: {'활성화' if DENTWEB_RECORDING_ENABLED else '비활성화'}")
    logger.info(f"덴트웹 차트 업로드 기능: {'활성화' if DENTWEB_CHART_UPLOAD_ENABLED else '비활성화'}")
    logger.info(f"사용자 저장 경로: {SAVE_PATH if SAVE_PATH else '기본 경로 사용'}")
    logger.info(f"평가판 모드: {'활성화' if USE_TRIAL_MODE else '비활성화'}")
    logger.info("-" * 80)
    
    # 커서 체크 타이머 시작
    from cursor_utils import start_cursor_check_timer
    start_cursor_check_timer()
    
    # 사용자 정보를 Sentry 컨텍스트에 추가
    try:
        sentry_sdk.set_user({
            "id": USER_EMAIL if not USE_TRIAL_MODE else "trial-user",
            "username": USER_NAME,
            "license_type": MODEL_MODE
        })
        
        # 추가 컨텍스트 정보
        sentry_sdk.set_context("app_info", {
            "version": VERSION,
            "os_info": f"{os.name} {platform.platform()}",
            "trial_mode": USE_TRIAL_MODE,
            "model_mode": MODEL_MODE
        })
    except Exception as e:
        logger.error(f"Sentry 사용자 정보 설정 중 오류: {str(e)}")
    
    open_settings_window()

    try:
        create_recording_handle_overlay()
        logging.info("녹음 핸들바 오버레이 시작")
    except Exception as e:
        logging.error(f"녹음 핸들바 오버레이 생성 실패: {e}")

    # # Windows 버전을 확인하는 함수
    # def is_windows_10():
    #     version = platform.version()
    #     build_number = int(version.split('.')[2])  # 빌드 번호 추출
    #     return build_number < 22000  # 빌드 번호가 22000 미만이면 Windows 10

    # try:
    #     if not is_windows_10():
    #         create_dictation_handle_overlay()
    #         logging.info("받아쓰기 핸들바 오버레이 시작")
    # except Exception as e:
    #     logging.error(f"받아쓰기 핸들바 오버레이 생성 실패: {e}")

    # 파일 감시자 초기화 (STT 처리 콜백 설정) - 주석 처리 (하단에서 통합 처리)
    # async def auto_stt_processor(file_path: str):
    #     """자동 파일 감시에서 호출되는 STT 처리 함수"""
    #     try:
    #         # 기존 STT 처리 로직 재사용
    #         settings_app = DentalAssistApp.get_instance()
    #         if settings_app:
    #             await settings_app.process_stt_file_from_watcher(file_path)
    #     except Exception as e:
    #         logging.error(f"자동 STT 처리 실패: {e}")

    # 파일 감시자 초기화 - 주석 처리 (하단에서 통합 처리)
    # initialize_file_watcher(auto_stt_processor)

    try:
        # 녹음 또는 업로드 중인지 확인하는 함수
        def is_busy():
            global recording, uploading
            return recording or uploading
        
        # 업데이트 매니저 초기화 및 인터넷 연결 체크 시작
        update_manager = UpdateManager(
            parent=root,
            app_version=VERSION,
            app_name=APP_NAME,
            github_owner=GITHUB_OWNER,
            github_repo=GITHUB_REPO,
            is_busy_callback=is_busy
        )
        update_manager.start_internet_check()
        
        # 여기서 다른 초기화 로직이 필요하다면 작성
        root.mainloop()  # 마우스 이벤트 대기
    except KeyboardInterrupt:
        if driver is not None:
            driver.quit()
        if listener is not None:
            listener.stop()
        close_overlay()
    except Exception as e:
        # 기타 예외 처리 및 로깅
        logger.error(f"메인 애플리케이션 실행 중 오류: {str(e)}")
        # Sentry에 추가 컨텍스트 정보와 함께 오류 보고
        sentry_sdk.capture_exception(e)

# 업데이트 관련 함수
def cleanup_update_temp_folder():
    """이전 업데이트에서 남은 임시 폴더와 파일들을 정리합니다."""
    try:
        # 현재 실행 파일 경로에서 실행 중인 프로그램 디렉토리 확인
        current_dir = os.path.dirname(os.path.abspath(sys.executable))
        main_exe = os.path.basename(sys.executable)
        
        # 기존 임시 폴더 경로
        temp_dir = os.path.join(current_dir, "Temp_dNote_updates")
        
        # 개별 정리 대상 파일 목록
        individual_files = [
            "dNote_Updater.exe",
            "updater_log.txt",
            "*.bak"
        ]
        
        # 현재 폴더에 있는 이전 버전 실행 파일 패턴
        version_pattern = "dNote_*.exe"  # 버전 번호가 포함된 실행 파일 패턴
        
        # 먼저 폴더 외부의 파일들 정리
        for pattern in individual_files + [version_pattern]:
            try:
                files = glob.glob(os.path.join(current_dir, pattern))
                for file_path in files:
                    # 현재 실행 중인 메인 프로그램은 건너뜁니다
                    if os.path.basename(file_path) == main_exe:
                        continue
                        
                    # 특별히 로그 파일은 다른 프로세스가 사용 중일 수 있으므로 추가 처리
                    if os.path.basename(file_path) == "updater_log.txt":
                        try:
                            # 로그 파일의 내용을 읽은 후 비우기 시도
                            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                                log_content = f.read()
                            
                            # 로그 파일을 비웁니다
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write("이전 로그 파일이 정리되었습니다.\n")
                                
                            # 이후 삭제 시도
                            try:
                                os.remove(file_path)
                                logging.info(f"업데이터 로그 파일 삭제 완료: {file_path}")
                            except Exception as e:
                                logging.warning(f"업데이터 로그 파일 삭제 실패 (사용 중): {str(e)}")
                                # 삭제 실패 시 나중에 배치 스크립트로 처리
                        except Exception as e:
                            logging.warning(f"로그 파일 처리 실패: {str(e)}")
                    else:
                        # 다른 파일들은 바로 삭제 시도
                        try:
                            os.remove(file_path)
                            logging.info(f"이전 파일 삭제 완료: {file_path}")
                        except Exception as e:
                            logging.warning(f"파일 삭제 실패 (사용 중일 수 있음): {str(e)}")
            except Exception as e:
                logging.warning(f"패턴 '{pattern}' 처리 중 오류: {str(e)}")
        
        # 폴더가 존재하는지 확인
        if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
            logging.info(f"이전 업데이트에서 남은 임시 폴더({temp_dir})를 정리합니다.")
            
            # 폴더 내 로그 파일 처리 (인코딩 문제 해결)
            log_file = os.path.join(temp_dir, "updater_log.txt")
            if os.path.exists(log_file):
                try:
                    # 여러 인코딩 시도
                    encodings_to_try = ['cp949', 'utf-8', 'euc-kr']
                    log_content = None
                    
                    for encoding in encodings_to_try:
                        try:
                            with open(log_file, 'r', encoding=encoding) as f:
                                log_content = f.read()
                                logging.info(f"임시 폴더의 로그 파일 읽기 성공: 인코딩 {encoding}")
                                break
                        except UnicodeDecodeError:
                            continue
                    
                    # 모든 인코딩이 실패하면 대체 문자 사용
                    if log_content is None:
                        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                            log_content = f.read()
                        logging.info("임시 폴더의 로그 파일 읽기: 인코딩 오류는 대체 문자로 처리됨")
                    
                    # 로그 내용은 읽기만 했지만 파일을 직접 삭제하지는 않음
                    # 폴더 전체를 삭제하는 과정에서 함께 삭제됨
                except Exception as e:
                    logging.warning(f"임시 폴더의 로그 파일 처리 중 오류: {str(e)}")
            
            try:
                # 폴더와 내용 모두 삭제
                shutil.rmtree(temp_dir, ignore_errors=True)
                logging.info("업데이트 임시 폴더 삭제 완료")
            except Exception as e:
                logging.warning(f"임시 폴더 삭제 실패: {str(e)}")
                
                # 삭제 실패 시 지연 삭제를 위한 배치 파일 생성
                try:
                    import subprocess
                    batch_path = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'cleanup_dnote_temp.bat')
                    with open(batch_path, 'w', encoding='utf-8') as f:
                        f.write('@echo off\n')
                        f.write('timeout /t 5 /nobreak > nul\n')  # 5초 대기
                        f.write(f'rmdir /s /q "{temp_dir}"\n')
                        
                        # 추가: 개별 파일도 다시 삭제 시도
                        for pattern in individual_files:
                            pattern_path = os.path.join(current_dir, pattern)
                            f.write(f'del /f /q "{pattern_path}" 2>nul\n')
                        
                        # 버전 패턴 실행 파일 삭제 시도
                        f.write(f'del /f /q "{os.path.join(current_dir, "dNote_*.exe")}" 2>nul\n')
                        
                        f.write('del "%~f0"\n')  # 배치 파일 자체 삭제
                    
                    # 배치 파일 실행 (숨겨진 창으로)
                    startupinfo = None
                    if os.name == 'nt':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = 0  # SW_HIDE
                    
                    subprocess.Popen(['cmd', '/c', batch_path], startupinfo=startupinfo)
                    logging.info("지연된 임시 폴더 및 파일 삭제를 위한 배치 스크립트 생성 및 실행")
                except Exception as batch_error:
                    logging.warning(f"배치 파일 생성 실패: {str(batch_error)}")
                    
        # 모든 정리 작업이 완료되었는지 확인하고 남은 파일 로깅
        remaining_updater = glob.glob(os.path.join(current_dir, "dNote_Updater.exe"))
        remaining_logs = glob.glob(os.path.join(current_dir, "updater_log.txt"))
        
        if remaining_updater or remaining_logs:
            logging.info(f"정리 후 남은 파일: 업데이터({len(remaining_updater)}개), 로그({len(remaining_logs)}개)")
    except Exception as e:
        logging.error(f"업데이트 임시 폴더 정리 중 오류 발생: {str(e)}")

# Windows 바탕화면 경로를 찾는 함수 추가
def get_desktop_path():
    """
    Windows에서 실제 사용자의 바탕화면 경로를 찾아 반환합니다.
    여러 방법을 시도하여 신뢰성을 높입니다.
    """
    try:
        # 방법 1: 레지스트리를 통해 바탕화면 경로 확인
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                          r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
            if os.path.exists(desktop_path):
                logging.info(f"레지스트리에서 바탕화면 경로 찾음: {desktop_path}")
                return Path(desktop_path)
    except Exception as e:
        logging.warning(f"레지스트리에서 바탕화면 경로 찾기 실패: {e}")

    try:
        # 방법 2: USERPROFILE 환경 변수 + Desktop
        user_profile = os.environ.get('USERPROFILE')
        if user_profile:
            desktop_path = os.path.join(user_profile, 'Desktop')
            if os.path.exists(desktop_path):
                logging.info(f"USERPROFILE 환경변수로 바탕화면 경로 찾음: {desktop_path}")
                return Path(desktop_path)
    except Exception as e:
        logging.warning(f"USERPROFILE에서 바탕화면 경로 찾기 실패: {e}")

    try:
        # 방법 3: SHGetFolderPath API를 사용하여 바탕화면 경로 가져오기
        from ctypes import windll, wintypes, create_unicode_buffer
        CSIDL_DESKTOP = 0x0000
        buf = create_unicode_buffer(wintypes.MAX_PATH)
        windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOP, None, 0, buf)
        desktop_path = buf.value
        if desktop_path and os.path.exists(desktop_path):
            logging.info(f"SHGetFolderPath API로 바탕화면 경로 찾음: {desktop_path}")
            return Path(desktop_path)
    except Exception as e:
        logging.warning(f"SHGetFolderPath API로 바탕화면 경로 찾기 실패: {e}")

    # 방법 4: 마지막 수단으로 Path.home() + Desktop 사용
    desktop_path = Path.home() / 'Desktop'
    logging.info(f"기본 방법으로 바탕화면 경로 설정: {desktop_path}")
    
    # 해당 경로가 없으면 생성 시도
    if not os.path.exists(desktop_path):
        try:
            os.makedirs(desktop_path)
            logging.info(f"바탕화면 디렉토리 생성됨: {desktop_path}")
        except Exception as e:
            logging.error(f"바탕화면 디렉토리 생성 실패: {e}")
    
    return desktop_path

def create_desktop_shortcut():
    """
    바탕화면에 dNote.exe 바로가기를 생성합니다.
    PowerShell을 사용하여 간단하고 확실하게 구현합니다.
    
    Returns:
        bool: 바로가기 생성 성공 여부
    """
    global SHORTCUT_CREATED
    
    try:
        # 현재 실행 파일 경로 가져오기
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller로 패키징된 경우
            exe_path = sys.executable
        else:
            # 개발 환경에서는 Python 스크립트 경로
            exe_path = os.path.abspath(__file__)
        
        # 바탕화면 경로 가져오기
        desktop_path = get_desktop_path()
        
        # 바로가기 파일 경로
        shortcut_path = os.path.join(desktop_path, "dNote.lnk")
        
        # 이미 바로가기가 존재하는지 확인
        if os.path.exists(shortcut_path):
            logging.info("바탕화면에 dNote 바로가기가 이미 존재합니다.")
            return True
        
        # PowerShell 스크립트로 바로가기 생성
        # 경로에 공백이나 특수문자가 있을 수 있으므로 따옴표로 감싸기
        powershell_script = f"""
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{exe_path}'
$Shortcut.WorkingDirectory = '{os.path.dirname(exe_path)}'
$Shortcut.Description = 'dNote - AI 음성 인식 솔루션'
$Shortcut.Save()
"""
        
        # PowerShell 명령 실행
        result = subprocess.run([
            'powershell', '-Command', powershell_script
        ], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        if result.returncode == 0 and os.path.exists(shortcut_path):
            logging.info(f"바탕화면에 dNote 바로가기가 성공적으로 생성되었습니다: {shortcut_path}")
            SHORTCUT_CREATED = True
            return True
        else:
            logging.error(f"바로가기 생성 실패. PowerShell 오류: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"바탕화면 바로가기 생성 중 오류 발생: {e}")
        return False

# 환자 이름을 처리하는 함수 추가
def get_best_patient_name(names_list, default_name="무제"):
    """
    환자 이름 목록에서 가장 적합한 환자 이름을 반환하는 함수
    - "무제"가 아닌 실제 환자 이름이 있으면 가장 많이 등장한 환자 이름 반환
    - 모두 "무제"이면 기본값 반환
    
    우선순위:
    1. "무제"가 아닌 실제 환자 이름이 있으면, 가장 많이 등장한 실제 환자 이름 선택
    2. 실제 환자 이름이 없으면 default_name(일반적으로 최초 환자 이름) 사용
    """
    if not names_list:
        return default_name
    
    # "무제"가 아닌 이름만 필터링
    real_names = [name for name in names_list if name != "무제" and name is not None]
    
    # 실제 환자 이름이 없는 경우 기본값 반환
    if not real_names:
        return default_name
    
    # 가장 많이 등장한 환자 이름 찾기
    name_counts = {}
    for name in real_names:
        name_counts[name] = name_counts.get(name, 0) + 1
    
    # 가장 많이 등장한 이름 및 횟수
    best_name, max_count = max(name_counts.items(), key=lambda x: x[1])
    
    # 로깅
    logging.info(f"환자 이름 통계: {name_counts}")
    logging.info(f"선택된 최적 환자 이름: {best_name} (등장 횟수: {max_count})")
    
    return best_name

# 환자 이름을 모니터링하는 코루틴 함수 추가
async def monitor_patient_name():
    """
    녹음 중 주기적으로 환자 이름을 확인하는 코루틴
    - patient_name_update_interval 간격으로 환자 이름 확인
    - 감지된 이름을 patient_names_list에 추가
    - 환자 이름이 변경되면 알림 표시
    """
    global patient_names_list, original_patient_name
    
    try:
        last_detected_name = original_patient_name
        monitoring_count = 0
        
        while recording:
            monitoring_count += 1
            
            # # 환자 이름 가져오기
            # current_patient = get_patient_name()

            patient_info = get_patient_info()
            current_patient = patient_info.display_name
            
            # 환자 이름 목록에 추가
            if current_patient is not None:
                patient_names_list.append(current_patient)
                logging.info(f"환자 이름 감지됨 [{monitoring_count}]: {current_patient}")
                
                # 환자 이름이 변경된 경우
                if last_detected_name != current_patient:
                    logging.warning(f"환자 이름 변경 감지: {last_detected_name} -> {current_patient}")
                    
                    # 특정 조건에서만 알림 표시
                    if last_detected_name == "무제" and current_patient != "무제":
                        # 처음에 "무제"였다가 실제 환자가 감지된 경우
                        asyncio.create_task(show_notification_overlay(f"환자 '{current_patient}' 감지됨", duration=2))
                    elif last_detected_name != "무제" and current_patient != "무제" and last_detected_name != current_patient:
                        # 다른 환자로 변경된 경우 (둘 다 "무제"가 아닌 경우)
                        asyncio.create_task(show_notification_overlay(f"환자가 '{last_detected_name}'에서 '{current_patient}'로 변경됨", duration=3))
                        # 녹음한 원래 환자 이름과 다르게 변경된 경우 경고 알림
                        if original_patient_name != "무제" and original_patient_name != current_patient:
                            asyncio.create_task(show_notification_overlay(f"주의: 작업 시작 환자와 다른 환자입니다!", duration=3))
                    
                    # 마지막 감지 이름 업데이트
                    last_detected_name = current_patient
            
            # 지정된 간격만큼 대기
            await asyncio.sleep(patient_name_update_interval)
            
            # 녹음이 종료된 경우 루프 종료
            if not recording:
                break
                
    except Exception as e:
        logging.error(f"환자 이름 모니터링 중 오류 발생: {e}")
        # 오류가 발생해도 녹음은 계속 진행

# 디스크 용량 확인 함수 추가
def check_disk_space(path, required_space_mb=500):
    """
    지정된 경로의 디스크 용량을 확인하는 함수.
    
    Args:
        path (str): 확인할 디스크 경로
        required_space_mb (int): 필요한 최소 용량 (MB 단위)
        
    Returns:
        tuple: (충분한 공간이 있는지 여부, 남은 용량 MB)
    """
    try:
        # 경로가 존재하지 않으면 상위 경로 사용
        check_path = path
        while not os.path.exists(check_path) and check_path:
            check_path = os.path.dirname(check_path)
        
        if not check_path:
            # 드라이브 루트로 폴백
            check_path = os.path.splitdrive(path)[0] + os.sep
            if not os.path.exists(check_path):
                check_path = os.path.dirname(os.path.abspath(__file__))
        
        # 디스크 사용량 확인 (psutil은 이미 import되어 있음)
        disk_usage = psutil.disk_usage(check_path)
        free_space_mb = disk_usage.free / (1024 * 1024)  # MB 단위로 변환
        
        logging.info(f"디스크 공간 확인: 남은 공간 {free_space_mb:.2f}MB (필요: {required_space_mb}MB)")
        
        # 필요한 공간보다 남은 공간이 적은지 확인
        return free_space_mb >= required_space_mb, free_space_mb
    except Exception as e:
        logging.error(f"디스크 공간 확인 중 오류 발생: {e}")
        # 오류 발생 시 True 반환하여 녹음 진행 허용 (오류가 계속 발생하는 것보다 낫음)
        return True, 0

# 일정 시간 후 붙여넣기 팁 자동 숨김
async def auto_hide_paste_tip(delay=24):
    """
    일정 시간 후 붙여넣기 팁을 자동으로 숨깁니다.
    
    Args:
        delay (int): 숨기기 전 대기 시간(초)
    """
    try:
        # 활성화 상태 초기화
        if not hasattr(auto_hide_paste_tip, 'active'):
            auto_hide_paste_tip.active = False
            
        # 짧은 간격으로 여러 번 확인하여 팁이 이미 숨겨졌는지 체크
        for i in range(delay * 2):  # 0.5초 간격으로 체크
            await asyncio.sleep(0.5)
            
            # 활성화 상태가 비활성화되었거나, 아직 설정되지 않았다면 종료
            if not hasattr(auto_hide_paste_tip, 'active') or not auto_hide_paste_tip.active:
                logging.info(f"붙여넣기 팁이 이미 다른 곳에서 숨겨짐 ({i * 0.5:.1f}초 후)")
                return
        
        # 시간이 지나면 팁 숨기기
        from cursor_utils import hide_paste_tip
        hide_paste_tip()
        auto_hide_paste_tip.active = False
        logging.info(f"{delay}초 후 붙여넣기 팁 자동 숨김")
    except Exception as e:
        logging.error(f"붙여넣기 팁 자동 숨김 오류: {e}")
        # 오류 발생 시에도 확실히 숨기기
        try:
            from cursor_utils import hide_paste_tip
            hide_paste_tip()
        except:
            pass
        auto_hide_paste_tip.active = False

def on_file_watch_change(enabled, path=None):
    """파일 감시 설정 변경 콜백"""
    global WATCH_FOLDER_ENABLED, WATCH_FOLDER_PATH
    
    WATCH_FOLDER_ENABLED = enabled
    if path is not None:
        WATCH_FOLDER_PATH = path
    
    logging.info(f"파일 감시 설정 변경: 활성화={enabled}, 경로={WATCH_FOLDER_PATH}")
    save_settings()  # 설정 저장

async def pause_recording():
    """
    녹음을 일시정지하는 함수
    """
    global recording_paused, pause_start_time, stream, paused_audio_data, recording_data
    
    if not recording or recording_paused:
        logging.warning("일시정지할 녹음이 없거나 이미 일시정지 상태입니다.")
        return False
    
    try:
        # 오디오 스트림 일시정지
        if stream and stream.active:
            # 현재까지의 녹음 데이터를 임시 저장
            paused_audio_data = recording_data.copy()
            stream.stop()
            logging.info(f"오디오 스트림 일시정지 - 저장된 데이터 청크: {len(paused_audio_data)}개")
            
        recording_paused = True
        pause_start_time = time.time()
        
        logging.info("녹음이 일시정지되었습니다.")
        asyncio.create_task(show_notification_overlay("작업이 일시정지 되었습니다.", duration=2))
        
        return True
        
    except Exception as e:
        logging.error(f"녹음 일시정지 중 오류 발생: {e}")
        return False

async def resume_recording():
    """
    일시정지된 녹음을 재개하는 함수
    """
    global recording_paused, pause_start_time, total_paused_time, stream, recording_data, paused_audio_data
    
    if not recording or not recording_paused:
        logging.warning("재개할 일시정지된 녹음이 없습니다.")
        return False
    
    try:
        # 일시정지 시간 계산 및 누적
        if pause_start_time:
            paused_duration = time.time() - pause_start_time
            total_paused_time += paused_duration
            logging.info(f"일시정지 시간: {paused_duration:.2f}초, 총 일시정지 시간: {total_paused_time:.2f}초")
        
        # 이전 녹음 데이터 복원
        if paused_audio_data:
            recording_data[:] = paused_audio_data
            paused_audio_data = []
            logging.info(f"녹음 데이터 복원 완료 - 복원된 데이터 청크: {len(recording_data)}개")
        
        # 오디오 스트림 재시작
        if stream:
            stream.start()
            logging.info("오디오 스트림 재시작 완료")
        
        recording_paused = False
        pause_start_time = None
        
        logging.info("녹음이 재개되었습니다.")
        asyncio.create_task(show_notification_overlay("작업이 재개되었습니다.", duration=2))
        
        return True
        
    except Exception as e:
        logging.error(f"녹음 재개 중 오류 발생: {e}")
        return False

def toggle_recording_pause():
    """
    녹음 일시정지/재개를 토글하는 함수 (동기 버전)
    """
    if recording_paused:
        asyncio.run_coroutine_threadsafe(resume_recording(), loop)
    else:
        asyncio.run_coroutine_threadsafe(pause_recording(), loop)

if __name__ == "__main__":
    try:
        # 로그 시스템 초기화 (가장 먼저 수행)
        logger = setup_logging()
        logger.info(f"{APP_NAME} v{VERSION} 시작")
        
        # 전역 예외 처리기 설정
        setup_global_exception_handler()
        
        # Sentry 초기화 (main 함수 전에도 수행)
        initialize_sentry()
        
        # 업데이트 임시 폴더 정리
        cleanup_update_temp_folder()
        
        register_startup_task()
        
        # 전역 아이콘 설정 (Windows 환경)
        if os.name == 'nt':
            try:
                # Windows 작업 표시줄 아이콘 설정
                icon_path = resource_path("src\\img\\app\\icon.ico")
                app_id = "IMM.dNote.Main"  # 고유한 앱 ID 설정
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                
                # 메인 창 아이콘 설정
                root.iconbitmap(icon_path)
            except Exception as e:
                logger.error(f"전역 아이콘 설정 중 오류: {e}")
        
        # 약관 동의 확인을 가장 먼저 수행
        if not TERMS_ACCEPTED:
            # 사용자에게 약관 동의 창 표시
            if show_terms_agreement():
                TERMS_ACCEPTED = True
                save_settings()  # 동의 여부 저장
                logger.info("약관에 동의하셨습니다.")
                
                # # 약관 동의 후 바탕화면 바로가기 생성
                # try:
                #     if create_desktop_shortcut():
                #         # 바로가기 생성 성공 시 알림 표시
                #         asyncio.run_coroutine_threadsafe(
                #             show_notification_overlay("바탕화면에 바로가기가 생성되었어요!", duration=4),
                #             loop if 'loop' in globals() else asyncio.new_event_loop()
                #         )
                #         logger.info("바탕화면 바로가기 생성 완료")
                #     else:
                #         logger.warning("바탕화면 바로가기 생성 실패")
                # except Exception as e:
                #     logger.error(f"바탕화면 바로가기 생성 중 오류: {e}")
            else:
                logger.info("약관에 동의하지 않아 프로그램을 종료합니다.")
                messagebox.showinfo("프로그램 종료", "dNote를 사용하기 위해서는 약관에 동의해야 합니다.\n프로그램을 종료합니다.")
                os._exit(0)  # 약관에 동의하지 않으면 즉시 종료

        # 파일 감시자 초기화 (STT 처리 콜백을 포함하여)
        async def stt_processor_callback(file_path: str):
            """파일 감시자에서 호출되는 STT 처리 콜백"""
            try:
                settings_app = DentalAssistApp.get_instance()
                if settings_app:
                    await settings_app.process_stt_file_from_watcher(file_path)
            except Exception as e:
                logging.error(f"STT 처리 콜백 오류: {e}")

        # 파일 감시자 초기화 및 메인 루프 설정
        initialize_file_watcher(stt_processor_callback, loop)
        set_main_event_loop(loop)
        
        threading.Thread(target=run_tray, daemon=True).start()
        main()
    except Exception as e:
        # 시작 단계에서의 예외 처리
        try:
            # logger가 초기화되지 않았을 수 있으므로 예외 처리
            logger.error(f"프로그램 시작 중 오류 발생: {str(e)}", exc_info=True)
        except:
            print(f"로깅 실패: 프로그램 시작 중 오류 발생: {str(e)}")
            
        # Sentry에 추가 컨텍스트 정보와 함께 오류 보고
        try:
            sentry_sdk.capture_exception(e)
        except:
            pass
        
        # 사용자에게 오류 알림
        messagebox.showerror("오류 발생", f"프로그램 시작 중 오류가 발생했습니다:\n{str(e)}\n\n이 오류는 자동으로 보고되었습니다.")
        os._exit(1)