import os
import sys
import time
import subprocess
import requests
import logging
import ctypes
import threading
import datetime
import socket
import random
import customtkinter as ctk
from packaging import version
import json

class UpdateManager:
    def __init__(self, parent=None, app_version=None, app_name="dNote", github_owner="I-MM", github_repo="dNote", is_busy_callback=None):
        self.parent = parent
        self.update_window = None
        self.internet_check_attempts = 0
        self.max_internet_check_attempts = 6  # 60초 (10초 * 6)
        self.check_update_scheduled = False
        # 업데이트 시간 목록 [(시간, 분)] 형태로 저장
        self.update_times = [(9, 20), (12, 30)]  # 오전 9시 20분, 오후 12시 30분
        self.is_busy_callback = is_busy_callback  # 녹음 또는 업로딩 중인지 확인하는 콜백
        
        # 애플리케이션 정보
        self.APP_NAME = app_name
        self.VERSION = app_version or "0.0.75"  # 외부에서 전달받은 버전 사용
        self.GITHUB_OWNER = github_owner
        self.GITHUB_REPO = github_repo
        
        # 업데이트 이력 추적 관련 속성 추가
        self.update_history_file = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'dNote_update', 'update_history.json')
        self.update_cooldown_hours = 24  # 업데이트 후 최소 대기 시간 (시간)
        self.update_cooldown_minutes = 10  # 업데이트 후 최소 대기 시간 (분) - 새로 추가
        self.max_updates_per_day = 4     # 하루 최대 업데이트 횟수 (2에서 4로 변경)
        
        # 프로그레스 바 UI 요소
        self.progress_status = None
        self.progress_bar = None
        self.download_info = None
        self.status_label = None
        
        # 자동 업데이트 카운트다운 타이머
        self.countdown_timer = None
        self.countdown_value = 10  # 10초 카운트다운
        self.countdown_label = None
        
        # 창 관리 속성
        self.window_displayed = False  # 창이 표시되었는지 여부
        self.dialog_active = False     # 다이얼로그가 활성화되었는지 여부
        
        # 아이콘 경로
        self.icon_path = self.resource_path("src\\img\\app\\icon.ico")
        
        # 디버깅 로깅
        logging.info(f"UpdateManager 초기화: 버전 {self.VERSION}, 앱 이름 {self.APP_NAME}")
        
        # 업데이트 이력 디렉토리 확인 및 생성
        self._ensure_update_history_dir()
        
    def check_internet_connection(self):
        """인터넷 연결 확인"""
        try:
            # 구글 DNS 서버로 연결 시도
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except OSError:
            return False
            
    def start_internet_check(self):
        """앱 시작시 인터넷 연결 확인 및 업데이트 체크 시작"""
        self.internet_check_attempts += 1
        
        if self.check_internet_connection():
            logging.info("인터넷 연결 확인됨")
            # 인터넷 연결 확인된 경우 3초 후 업데이트 체크
            if not self.check_update_scheduled:
                self.check_update_scheduled = True
                threading.Timer(3, self.check_for_updates).start()
                # 매일 오후 12시 30분 업데이트 체크 스케줄링
                self.schedule_daily_update_check()
            return
            
        if self.internet_check_attempts >= self.max_internet_check_attempts:
            # 60초 동안 인터넷 연결 실패
            logging.warning("인터넷 연결 실패. 애플리케이션을 종료합니다.")
            self.show_connection_error()
            return
            
        # 10초 후 다시 체크
        logging.info(f"인터넷 연결 시도 중... ({self.internet_check_attempts}/{self.max_internet_check_attempts})")
        threading.Timer(10, self.start_internet_check).start()
    
    def show_connection_error(self):
        """인터넷 연결 오류 메시지 표시"""
        # 기존 창이 있다면 제거
        if self.update_window and self.update_window.winfo_exists():
            self.update_window.destroy()
            
        # 오류 창 생성
        self.update_window = ctk.CTkToplevel(self.parent)
        self.update_window.title("연결 오류")
        self.update_window.geometry("400x200")
        self.update_window.resizable(False, False)
        self.update_window.attributes("-topmost", True)
        
        # 아이콘 설정
        self.set_window_icon(self.update_window)
        
        # 화면 중앙에 표시
        if self.update_window.winfo_exists():
            self.update_window.update_idletasks()
            width = self.update_window.winfo_width()
            height = self.update_window.winfo_height()
            x = (self.update_window.winfo_screenwidth() // 2) - (width // 2)
            y = (self.update_window.winfo_screenheight() // 2) - (height // 2)
            self.update_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 오류 메시지
        ctk.CTkLabel(
            self.update_window,
            text="인터넷 연결이 되지 않아 앱이 종료됩니다.",
            font=("Malgun Gothic", 14, "bold")
        ).pack(pady=(40, 20))
        
        # 앱 종료 카운트다운
        self.countdown_value = 6
        self.countdown_label = ctk.CTkLabel(
            self.update_window,
            text=f"{self.countdown_value}초 후 종료됩니다...",
            font=("Malgun Gothic", 12)
        )
        self.countdown_label.pack(pady=20)
        
        self.update_countdown()
    
    def update_countdown(self):
        """종료 카운트다운 업데이트"""
        if not self.update_window or not self.update_window.winfo_exists():
            return
            
        self.countdown_value -= 1
        self.countdown_label.configure(text=f"{self.countdown_value}초 후 종료됩니다...")
        
        if self.countdown_value <= 0:
            self.update_window.destroy()
            os._exit(0)  # 강제 종료
        else:
            self.update_window.after(1000, self.update_countdown)
    
    def schedule_daily_update_check(self):
        """지정된 시간에 업데이트 체크 스케줄링"""
        now = datetime.datetime.now()
        
        # 다음 실행 시간 찾기
        next_update_time = None
        min_delay = float('inf')
        
        for hour, minute in self.update_times:
            # 각 업데이트 시간 계산
            check_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # API 호출 분산을 위한 랜덤 지연 추가 (±5초)
            random_offset = random.randint(-5, 5)
            check_time = check_time + datetime.timedelta(seconds=random_offset)
            
            # 이미 지난 시간이면 다음 날로 설정
            if now > check_time:
                check_time = check_time + datetime.timedelta(days=1)
            
            # 현재부터 이 시간까지의 지연 계산
            delay = (check_time - now).total_seconds()
            
            # 가장 가까운 다음 업데이트 시간 선택
            if delay < min_delay:
                next_update_time = check_time
                min_delay = delay
        
        # 다음 체크까지 남은 시간 (초)
        delay_seconds = min_delay
        
        logging.info(f"다음 자동 업데이트 체크 예정: {next_update_time.strftime('%Y-%m-%d %H:%M:%S')} (약 {delay_seconds/3600:.1f}시간 후)")
        
        # 타이머 설정
        threading.Timer(delay_seconds, self.check_for_updates_auto).start()
    
    def check_for_updates(self, auto_update=True):
        """업데이트 체크 (수동 또는 자동)"""
        try:
            # 로컬 캐시 디렉토리
            cache_dir = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'dNote_update')
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, 'github_release_cache.json')
            
            # 캐시 시간 (10분 = 600초)
            cache_timeout = 600
            
            # 캐시된 응답이 있는지 확인
            use_cached = False
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    
                    cache_time = cached_data.get('timestamp', 0)
                    current_time = time.time()
                    
                    if current_time - cache_time < cache_timeout:
                        use_cached = True
                        response_data = cached_data['data']
                        logging.info("캐시된 업데이트 정보 사용")
                except (FileNotFoundError, PermissionError, json.JSONDecodeError) as cache_error:
                    logging.warning(f"캐시 파일 읽기 오류 (무시하고 계속): {str(cache_error)}")
                    use_cached = False
                except Exception as cache_error:
                    logging.warning(f"캐시 처리 중 예상치 못한 오류 (무시하고 계속): {str(cache_error)}")
                    use_cached = False
            
            if not use_cached:
                # GitHub API를 통해 최신 릴리스 정보 가져오기
                logging.info("GitHub에서 최신 릴리스 정보 조회 중...")
                api_url = f"https://api.github.com/repos/{self.GITHUB_OWNER}/{self.GITHUB_REPO}/releases/latest"
                
                try:
                    response = requests.get(api_url, timeout=10)
                    response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
                    
                    try:
                        response_data = response.json()
                    except json.JSONDecodeError as json_error:
                        logging.error(f"GitHub API 응답 JSON 파싱 오류: {str(json_error)}")
                        logging.error(f"응답 내용: {response.text[:500]}...")
                        return False
                    
                    # 응답 캐시 저장
                    try:
                        cache_data = {
                            'timestamp': time.time(),
                            'data': response_data
                        }
                        
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(cache_data, f, ensure_ascii=False, indent=2)
                        
                        logging.info("업데이트 정보 캐시 저장 완료")
                    except (PermissionError, OSError) as cache_save_error:
                        logging.warning(f"캐시 저장 실패 (업데이트는 계속): {str(cache_save_error)}")
                    
                except requests.exceptions.Timeout:
                    logging.error("GitHub API 요청 타임아웃 (10초)")
                    return False
                except requests.exceptions.ConnectionError as conn_error:
                    logging.error(f"GitHub API 연결 오류: {str(conn_error)}")
                    return False
                except requests.exceptions.HTTPError as http_error:
                    logging.error(f"GitHub API HTTP 오류: {str(http_error)}")
                    logging.error(f"응답 상태 코드: {response.status_code}")
                    return False
                except requests.exceptions.RequestException as req_error:
                    logging.error(f"GitHub API 요청 오류: {str(req_error)}")
                    return False
            
            latest_version = response_data["tag_name"].lstrip('v')
            
            logging.info(f"최신 버전: {latest_version}")
            
            if version.parse(latest_version) > version.parse(self.VERSION):
                logging.info(f"새 버전 발견: {latest_version}")
                
                # 업데이트 건너뛰기 확인
                should_skip, skip_reason = self._should_skip_update(latest_version)
                if should_skip:
                    logging.warning(f"업데이트 건너뛰기: {skip_reason}")
                    if not auto_update:
                        # 수동 업데이트인 경우 사용자에게 알림
                        self.show_update_skip_notice(skip_reason)
                    return False
                
                # 자동 업데이트 모드와 상관없이 항상 카운트다운 UI 표시
                self.show_update_dialog(response_data, auto_mode=auto_update)
                return True
            else:
                logging.info("이미 최신 버전을 사용 중입니다.")
                return False
                
        except Exception as e:
            logging.error(f"업데이트 확인 실패: {str(e)}")
            return False
    
    def check_for_updates_auto(self):
        """자동 업데이트 체크"""
        # 녹음 또는 업로드 중인지 확인
        if self.is_busy_callback and self.is_busy_callback():
            logging.info("녹음 또는 업로드 중이므로 자동 업데이트를 연기합니다.")
            # 30분 후에 다시 시도
            threading.Timer(1800, self.check_for_updates_auto).start()
            return False
            
        # 자동 업데이트 모드로 체크
        result = self.check_for_updates(auto_update=True)
        
        # 다음 날 같은 시간에 다시 체크하도록 스케줄링
        self.schedule_daily_update_check()
        
        return result
    
    def show_update_dialog(self, release_data, auto_mode=False):
        """업데이트 알림 대화상자 표시 (수동 또는 자동)"""
        try:
            # 이미 대화상자가 표시 중인 경우 중복 방지
            if self.dialog_active:
                logging.warning("업데이트 대화상자가 이미 활성화되어 있습니다. 중복 표시를 방지합니다.")
                return
            
            self.dialog_active = True
            
            if self.update_window and self.update_window.winfo_exists():
                try:
                    self.update_window.destroy()
                except Exception as e:
                    logging.error(f"기존 업데이트 창 제거 중 오류: {str(e)}")
                
            latest_version = release_data["tag_name"].lstrip('v')
            release_notes = release_data.get("body", "릴리스 노트 없음")
            
            logging.info(f"업데이트 대화상자 표시: auto_mode={auto_mode}, 버전 {self.VERSION} -> {latest_version}")
            
            # 업데이트 대화 상자 생성
            self.update_window = ctk.CTkToplevel(self.parent)
            # 타이틀바 표시 (최소화 버튼 활성화를 위해 overrideredirect 제거)
            if auto_mode:
                self.update_window.title("자동 업데이트 가능")
            else:
                self.update_window.title("수동 업데이트 가능")
            self.update_window.geometry("500x480")
            self.update_window.resizable(False, False)
            
            # 아이콘 설정
            try:
                self.set_window_icon(self.update_window)
            except Exception as e:
                logging.error(f"아이콘 설정 중 오류: {str(e)}")
            
            # 항상 최상위에 표시되도록 설정
            self.update_window.attributes("-topmost", True)
            
            # 모달 상태 설정을 위한 새로운 접근법
            # 업데이트 창이 닫힐 때까지 다른 창들의 상호작용을 막기 위한 전역 grab 설정
            try:
                # 현재 grab 상태를 확인
                current_grab = self.update_window.grab_current()
                # 다른 창이 grab을 가지고 있다면 일시적으로 해제
                if current_grab and current_grab != self.update_window:
                    current_grab.grab_release()
                # 업데이트 창에 grab 설정
                self.update_window.grab_set()
            except Exception as e:
                logging.error(f"모달 상태 설정 중 오류: {str(e)}")
            
            # 먼저 창 표시
            try:
                self.update_window.update()
            except Exception as e:
                logging.error(f"창 업데이트 중 오류: {str(e)}")
            
            # 화면 중앙에 표시
            try:
                screen_width = self.update_window.winfo_screenwidth()
                screen_height = self.update_window.winfo_screenheight()
                x = (screen_width // 2) - (500 // 2)
                y = (screen_height // 2) - (480 // 2)
                self.update_window.geometry(f"500x480+{x}+{y}")
            except Exception as e:
                logging.error(f"창 위치 설정 중 오류: {str(e)}")
            
            # 타이틀
            ctk.CTkLabel(
                self.update_window, 
                text=f"새 버전 {latest_version}이(가) 있습니다!", 
                font=("Malgun Gothic", 18, "bold")
            ).pack(pady=(20, 5))
            
            # 현재 버전
            ctk.CTkLabel(
                self.update_window, 
                text=f"현재 버전: {self.VERSION}",
                text_color="gray75"
            ).pack(pady=(0, 10))
            
            # auto_mode에 따른 카운트다운 표시 (자동 모드에서만 카운트다운)
            if auto_mode:
                self.countdown_value = 5
                self.countdown_label = ctk.CTkLabel(
                    self.update_window,
                    text=f"{self.countdown_value}초 후 자동으로 업데이트합니다...",
                    font=("Malgun Gothic", 13),
                    text_color="#FF5555"
                )
                self.countdown_label.pack(pady=10)
            else:
                # 수동 모드에서는 카운트다운 없이 안내 메시지만 표시
                notice_label = ctk.CTkLabel(
                    self.update_window,
                    text="수동 업데이트 확인 - 업데이트를 진행하거나 취소하세요.",
                    font=("Malgun Gothic", 11),
                    text_color="#2196F3"
                )
                notice_label.pack(pady=10)
            
            # 구분선
            separator = ctk.CTkFrame(self.update_window, height=1, width=450)
            separator.pack(pady=5)
            
            # 릴리스 노트 프레임
            notes_frame = ctk.CTkFrame(self.update_window, corner_radius=10)
            notes_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            ctk.CTkLabel(
                notes_frame,
                text="변경 사항:",
                font=("Malgun Gothic", 12, "bold"),
                anchor="w"
            ).pack(anchor="w", padx=10, pady=(10, 0))
            
            # 스크롤 가능한 텍스트 영역
            notes_text = ctk.CTkTextbox(notes_frame, width=450, height=150)
            notes_text.pack(padx=10, pady=10, fill="both", expand=True)
            notes_text.insert("1.0", release_notes)
            notes_text.configure(state="disabled")  # 읽기 전용
            
            # 버튼 프레임
            button_frame = ctk.CTkFrame(self.update_window, fg_color="transparent")
            button_frame.pack(fill="x", padx=20, pady=(0, 15))
            
            # 업데이트 진행 버튼 (항상 표시)
            update_button = ctk.CTkButton(
                button_frame, 
                text="업데이트 진행", 
                font=("Malgun Gothic", 12),
                fg_color="#2196F3", 
                hover_color="#1976D2",
                command=lambda: self.start_auto_update(release_data)
            )
            update_button.pack(side="left", padx=20)
            
            # 취소 버튼 - 자동/수동 모드에 따라 다른 텍스트와 동작
            if auto_mode:
                # 자동 업데이트 모드에서는 "취소 및 앱 종료" 버튼
                cancel_button = ctk.CTkButton(
                    button_frame, 
                    text="취소 및 앱 종료", 
                    font=("Malgun Gothic", 12),
                    fg_color="#555555", 
                    hover_color="#333333",
                    command=lambda: self.cancel_update()
                )
            else:
                # 수동 업데이트 모드에서는 "업데이트 건너뛰기" 버튼
                cancel_button = ctk.CTkButton(
                    button_frame, 
                    text="업데이트 건너뛰기", 
                    font=("Malgun Gothic", 12),
                    fg_color="#555555", 
                    hover_color="#333333",
                    command=lambda: self.skip_update()
                )
            cancel_button.pack(side="right", padx=20)
            
            # 모든 UI 요소가 생성된 후 다시 한 번 화면 최상위 및 포커스 설정
            self.update_window.attributes("-topmost", True)
            self.update_window.lift()
            self.update_window.focus_force()
            
            # 창이 표시되었음을 표시
            self.window_displayed = True
            
            # auto_mode에서만 카운트다운 시작
            if auto_mode:
                # 일단 창이 모두 표시된 후 약간의 지연 후 카운트다운 시작
                self.update_window.after(500, lambda: self.start_update_countdown(release_data))
            
            # 창 닫기 이벤트 처리 - 자동/수동 모드에 따라 다르게 처리
            if auto_mode:
                self.update_window.protocol("WM_DELETE_WINDOW", lambda: self.cancel_update())
            else:
                self.update_window.protocol("WM_DELETE_WINDOW", lambda: self.skip_update())
        
        except Exception as e:
            logging.error(f"업데이트 대화상자 표시 중 오류 발생: {str(e)}")
            self.dialog_active = False
    
    def start_update_countdown(self, release_data):
        """자동 업데이트 카운트다운 시작"""
        try:
            if not self.update_window or not self.update_window.winfo_exists():
                logging.error("카운트다운을 시작할 창이 존재하지 않습니다.")
                return
            
            # 창이 여전히 최상위에 있는지 확인하고 포커스 강제
            try:
                self.update_window.lift()
                self.update_window.attributes("-topmost", True)
                self.update_window.focus_force()
            except Exception as ui_error:
                logging.error(f"창 포커스 설정 중 오류: {str(ui_error)}")
            
            # 카운트다운 값 감소
            self.countdown_value -= 1
            
            # 카운트다운 텍스트 업데이트
            try:
                if hasattr(self, 'countdown_label') and self.countdown_label and self.countdown_label.winfo_exists():
                    self.countdown_label.configure(text=f"{self.countdown_value}초 후 자동으로 업데이트합니다...")
                    # 텍스트 변경이 즉시 적용되도록 업데이트
                    self.countdown_label.update()
            except Exception as label_error:
                logging.error(f"카운트다운 라벨 업데이트 중 오류: {str(label_error)}")
            
            # 카운트다운 상태 로깅
            logging.info(f"업데이트 카운트다운: {self.countdown_value}초 남음")
            
            if self.countdown_value <= 0:
                # 카운트다운 완료, 업데이트 시작
                logging.info("카운트다운 완료, 자동 업데이트 시작")
                try:
                    if self.update_window and self.update_window.winfo_exists():
                        # 카운트다운 완료 시 바로 자동 업데이트 실행
                        self.start_auto_update(release_data)
                        return  # 더 이상 카운트다운 필요 없음
                except Exception as update_error:
                    logging.error(f"자동 업데이트 시작 중 오류: {str(update_error)}")
                    # 오류 발생 시 사용자가 수동으로 선택할 수 있도록 계속 진행
                    return
            else:
                # 1초 후 다시 호출 (창이 여전히 존재하는지 확인)
                try:
                    if self.update_window and self.update_window.winfo_exists():
                        self.countdown_timer = self.update_window.after(1000, lambda: self.start_update_countdown(release_data))
                except Exception as timer_error:
                    logging.error(f"카운트다운 타이머 설정 중 오류: {str(timer_error)}")
        
        except Exception as e:
            # 예외 발생 시 로깅
            logging.error(f"카운트다운 중 숈상치 못한 오류 발생: {str(e)}")
            # 안전하게 계속 진행
            try:
                if self.update_window and self.update_window.winfo_exists() and self.countdown_value > 0:
                    self.countdown_timer = self.update_window.after(1000, lambda: self.start_update_countdown(release_data))
            except Exception as fallback_error:
                logging.error(f"카운트다운 복구 시도 중 오류: {str(fallback_error)}")
                # 더 이상 진행할 수 없는 경우 사용자가 수동으로 선택하도록 유도
                logging.warning("카운트다운을 중단합니다. 사용자의 수동 선택을 기다립니다.")
    
    def skip_update(self):
        """업데이트 건너뛰기 (자동 모드에서만 호출)"""
        try:
            logging.info("사용자가 자동 업데이트를 건너뛰었습니다.")
            
            # 카운트다운 타이머 취소
            if self.countdown_timer and self.update_window and self.update_window.winfo_exists():
                try:
                    self.update_window.after_cancel(self.countdown_timer)
                    self.countdown_timer = None
                except Exception as e:
                    logging.error(f"카운트다운 타이머 취소 중 오류: {str(e)}")
                
            # grab 상태 해제
            if self.update_window and self.update_window.winfo_exists():
                try:
                    self.update_window.grab_release()
                except Exception as e:
                    logging.error(f"grab 해제 중 오류: {str(e)}")
            
            # 업데이트 창 닫기
            if self.update_window and self.update_window.winfo_exists():
                try:
                    self.update_window.destroy()
                except Exception as e:
                    logging.error(f"업데이트 창 닫기 중 오류: {str(e)}")
                
            # 상태 변수 리셋
            self.dialog_active = False
            self.window_displayed = False
            self.update_window = None
            
            # 앱은 계속 실행됨
            
        except Exception as e:
            logging.error(f"업데이트 건너뛰기 중 오류 발생: {str(e)}")
            # 상태 변수 강제 리셋
            self.dialog_active = False
            self.window_displayed = False
            self.update_window = None

    def cancel_update(self):
        """업데이트 취소 및 앱 종료"""
        try:
            logging.info("사용자가 업데이트를 취소하고 앱 종료를 선택했습니다.")
            
            # 카운트다운 타이머 취소
            if self.countdown_timer and self.update_window and self.update_window.winfo_exists():
                try:
                    self.update_window.after_cancel(self.countdown_timer)
                    self.countdown_timer = None
                except Exception as e:
                    logging.error(f"카운트다운 타이머 취소 중 오류: {str(e)}")
                
            # grab 상태 해제
            if self.update_window and self.update_window.winfo_exists():
                try:
                    self.update_window.grab_release()
                except Exception as e:
                    logging.error(f"grab 해제 중 오류: {str(e)}")
            
            # 업데이트 창 닫기
            if self.update_window and self.update_window.winfo_exists():
                try:
                    self.update_window.destroy()
                except Exception as e:
                    logging.error(f"업데이트 창 닫기 중 오류: {str(e)}")
                
            # 상태 변수 리셋
            self.dialog_active = False
            self.window_displayed = False
            self.update_window = None
            
            # 앱 종료
            os._exit(0)  # 앱 강제 종료
            
        except Exception as e:
            logging.error(f"업데이트 취소 중 오류 발생: {str(e)}")
            # 오류 발생 시에도 앱 종료
            os._exit(0)
    
    def start_auto_update(self, release_data):
        """자동 업데이트 시작"""
        # grab 상태 해제
        if self.update_window and self.update_window.winfo_exists():
            try:
                self.update_window.grab_release()
            except Exception as e:
                logging.error(f"grab 해제 중 오류: {str(e)}")
            
        if self.update_window and self.update_window.winfo_exists():
            self.update_window.destroy()
        
        # EXE 자산 찾기
        assets = release_data.get("assets", [])
        installer_asset = next((asset for asset in assets if 
                               asset["name"].lower() == "dnote_installer.exe"), None)
        
        if not installer_asset:
            self.show_update_error("다운로드할 Installer 파일을 찾을 수 없습니다.")
            return
        
        download_url = installer_asset["browser_download_url"]
        latest_version = release_data["tag_name"].lstrip('v')
        release_notes = release_data.get("body", "릴리스 노트 없음")
        
        # 업데이트 진행에서 사용할 수 있도록 release_data와 installer_asset 저장
        self.current_release_data = release_data
        self.current_installer_asset = installer_asset
        
        # 업데이트 시도 기록
        self._record_update_attempt(self.VERSION, latest_version, success=False)  # 초기에는 실패로 기록하고 성공 시 업데이트
        
        # 업데이트 진행 창 표시
        self.show_update_progress(download_url, latest_version, release_notes)
    
    def show_update_progress(self, download_url, latest_version, release_notes):
        """업데이트 진행 상황 UI 표시"""
        # 기존 창의 grab 상태 해제
        if self.update_window and self.update_window.winfo_exists():
            try:
                self.update_window.grab_release()
            except Exception as e:
                logging.error(f"grab 해제 중 오류: {str(e)}")
        
        # 기존 창이 있다면 제거
        if self.update_window and self.update_window.winfo_exists():
            self.update_window.destroy()
        
        # 업데이트 진행 창 생성
        self.update_window = ctk.CTkToplevel(self.parent)
        # 타이틀바 표시 (최소화 버튼 활성화를 위해 overrideredirect 제거)
        self.update_window.title("업데이트 진행 중")
        self.update_window.geometry("500x400")
        self.update_window.resizable(False, False)
        
        # 아이콘 설정
        self.set_window_icon(self.update_window)
        
        self.update_window.attributes("-topmost", True)
        
        # 화면 중앙에 표시
        if self.update_window.winfo_exists():
            self.update_window.update_idletasks()
            width = self.update_window.winfo_width()
            height = self.update_window.winfo_height()
            x = (self.update_window.winfo_screenwidth() // 2) - (width // 2)
            y = (self.update_window.winfo_screenheight() // 2) - (height // 2)
            self.update_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 업데이트 정보
        ctk.CTkLabel(
            self.update_window, 
            text=f"{self.APP_NAME} 업데이트", 
            font=("Malgun Gothic", 18, "bold")
        ).pack(pady=(20, 5))
        
        ctk.CTkLabel(
            self.update_window, 
            text=f"버전 {self.VERSION} → {latest_version}",
            font=("Malgun Gothic", 12)
        ).pack(pady=(0, 10))
        
        # 프로그레스 바 및 상태 표시
        self.progress_frame = ctk.CTkFrame(self.update_window)
        self.progress_frame.pack(fill="x", padx=25, pady=10)
        
        self.progress_status = ctk.CTkLabel(
            self.progress_frame,
            text="다운로드 준비 중...",
            font=("Malgun Gothic", 11),
            anchor="w"
        )
        self.progress_status.pack(anchor="w", pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", padx=0, pady=0)
        self.progress_bar.set(0)
        
        self.download_info = ctk.CTkLabel(
            self.progress_frame,
            text="0 MB / 0 MB",
            font=("Malgun Gothic", 10),
            text_color="gray70",
            anchor="e"
        )
        self.download_info.pack(anchor="e", pady=(5, 0))
        
        # 릴리스 노트 표시
        notes_frame = ctk.CTkFrame(self.update_window, corner_radius=10)
        notes_frame.pack(fill="both", expand=True, padx=25, pady=10)
        
        ctk.CTkLabel(
            notes_frame,
            text="변경 사항:",
            font=("Malgun Gothic", 12, "bold"),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(10, 0))
        
        notes_text = ctk.CTkTextbox(notes_frame, width=450, height=120)
        notes_text.pack(padx=10, pady=10, fill="both", expand=True)
        notes_text.insert("1.0", release_notes)
        notes_text.configure(state="disabled")
        
        # 진행 상태 표시
        status_frame = ctk.CTkFrame(self.update_window, fg_color="transparent")
        status_frame.pack(fill="x", padx=25, pady=(0, 20))
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="업데이트가 완료되면 프로그램이 자동으로 재시작됩니다.",
            font=("Malgun Gothic", 11),
            text_color="gray70"
        )
        self.status_label.pack(pady=10)
        
        # 별도 스레드에서 다운로드 시작
        threading.Thread(target=self.download_and_update, args=(download_url,), daemon=True).start()
    
    def download_and_update(self, download_url):
        """
        파일 다운로드 및 업데이트 수행
        액세스 거부 오류 발생 시 최대 3회까지 재시도
        """
        max_attempts = 3
        
        # 다운로드 URL 검증
        if not download_url or not isinstance(download_url, str):
            logging.error("잘못된 다운로드 URL입니다.")
            self.update_progress("오류", "다운로드 URL이 올바르지 않습니다.", 0)
            threading.Timer(2, self.show_update_error, args=["업데이트 실패: 다운로드 URL이 올바르지 않습니다."]).start()
            return
        
        # URL 형식 기본 검증
        if not download_url.startswith(('http://', 'https://')):
            logging.error(f"지원하지 않는 URL 프로토콜입니다: {download_url}")
            self.update_progress("오류", "지원하지 않는 다운로드 링크입니다.", 0)
            threading.Timer(2, self.show_update_error, args=["업데이트 실패: 지원하지 않는 다운로드 링크입니다."]).start()
            return
        
        for attempt in range(max_attempts):
            try:
                # Installer 방식에서는 별도 업데이터 다운로드 불필요
                self.update_progress("업데이트 준비 중...", "업데이트 준비를 진행합니다.", 0.05)
                
                # 다운로드 시작
                self.update_progress("다운로드 중...", "서버에서 파일을 받고 있습니다.", 0.1)
                
                # 네트워크 연결성 재확인
                if not self.check_internet_connection():
                    logging.error("네트워크 연결이 끊어졌습니다.")
                    self.update_progress("오류", "네트워크 연결을 확인할 수 없습니다.", 0)
                    threading.Timer(2, self.show_update_error, args=["업데이트 실패: 네트워크 연결을 확인해주세요."]).start()
                    return
                
                # 요청 보내기 - 타임아웃과 연결 재시도 설정
                try:
                    response = requests.get(
                        download_url, 
                        stream=True, 
                        timeout=(10, 60),  # (연결 타임아웃, 읽기 타임아웃)
                        headers={
                            'User-Agent': f'{self.APP_NAME}/{self.VERSION} UpdateManager'
                        }
                    )
                    response.raise_for_status()
                except requests.exceptions.Timeout:
                    if attempt < max_attempts - 1:
                        logging.warning(f"다운로드 타임아웃 발생. 재시도 중... ({attempt+1}/{max_attempts})")
                        self.update_progress("재시도 중...", f"다운로드 타임아웃이 발생했습니다. 재시도 중... ({attempt+1}/{max_attempts})", 0.05)
                        time.sleep(2)
                        continue
                    else:
                        raise
                except requests.exceptions.ConnectionError as conn_error:
                    if attempt < max_attempts - 1:
                        logging.warning(f"연결 오류 발생. 재시도 중... ({attempt+1}/{max_attempts}): {str(conn_error)}")
                        self.update_progress("재시도 중...", f"연결 오류가 발생했습니다. 재시도 중... ({attempt+1}/{max_attempts})", 0.05)
                        time.sleep(3)
                        continue
                    else:
                        raise
                
                # 파일 이름 및 임시 저장 경로 설정
                try:
                    file_name = os.path.basename(download_url)
                    # 파일명에 특수문자가 있는 경우 처리
                    if not file_name or '?' in file_name:
                        file_name = f"dnote_installer_{int(time.time())}.exe"
                    
                    # 안전한 파일명으로 정제
                    import re
                    file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
                    
                    if not file_name.endswith('.exe'):
                        file_name += '.exe'
                        
                except Exception as name_error:
                    logging.error(f"파일명 처리 오류: {str(name_error)}")
                    file_name = f"dnote_installer_{int(time.time())}.exe"
                
                temp_dir = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'dNote_update')
                
                # 임시 디렉토리 생성 및 권한 확인
                try:
                    os.makedirs(temp_dir, exist_ok=True)
                except OSError as dir_error:
                    logging.error(f"임시 디렉토리 생성 실패: {str(dir_error)}")
                    # 홈 디렉토리로 폴백
                    temp_dir = os.path.join(os.path.expanduser('~'), 'dNote_update')
                    try:
                        os.makedirs(temp_dir, exist_ok=True)
                    except OSError:
                        # 마지막 수단으로 현재 디렉토리 사용
                        temp_dir = os.getcwd()
                
                temp_file = os.path.join(temp_dir, file_name)
                
                # 임시 디렉토리 쓰기 권한 확인
                try:
                    # 테스트 파일 생성 시도
                    test_file = os.path.join(temp_dir, f'test_write_{int(time.time())}.tmp')
                    with open(test_file, 'w', encoding='utf-8') as f:
                        f.write('test')
                    # 테스트 성공 시 파일 삭제
                    if os.path.exists(test_file):
                        os.remove(test_file)
                except PermissionError:
                    # 권한이 없을 경우 사용자 홈 디렉토리로 변경
                    logging.warning(f"임시 디렉토리 {temp_dir}에 쓰기 권한이 없습니다. 홈 디렉토리 사용")
                    temp_dir = os.path.join(os.path.expanduser('~'), 'dNote_update')
                    try:
                        os.makedirs(temp_dir, exist_ok=True)
                        temp_file = os.path.join(temp_dir, file_name)
                    except OSError:
                        # 최후의 수단
                        temp_dir = os.getcwd()
                        temp_file = os.path.join(temp_dir, file_name)
                
                # 진행 상황 표시 초기화
                total_size = int(response.headers.get('content-length', 0))
                
                # Content-Length가 없거나 이상한 경우 처리
                if total_size <= 0:
                    logging.warning("서버에서 파일 크기 정보를 제공하지 않습니다. 예상 크기로 진행합니다.")
                    total_size = 50 * 1024 * 1024  # 50MB로 가정
                
                total_size_mb = total_size / (1024 * 1024)
                downloaded = 0
                
                # 업데이트 간격 설정 (0.5MB 단위)
                update_interval = 512 * 1024  # 0.5MB
                last_update_size = 0
                
                # 파일 다운로드
                try:
                    with open(temp_file, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                file.write(chunk)
                                downloaded += len(chunk)
                                
                                # 0.5MB 단위로만 프로그레스 업데이트
                                if downloaded - last_update_size >= update_interval or downloaded >= total_size:
                                    percent = min(downloaded / total_size, 1.0) if total_size > 0 else 0
                                    downloaded_mb = downloaded / (1024 * 1024)
                                    
                                    # 진행 상황 업데이트
                                    self.update_progress(
                                        "다운로드 중...", 
                                        f"서버에서 파일을 받고 있습니다. ({percent:.0%})", 
                                        0.1 + (percent * 0.6),  # 10% ~ 70% 구간
                                        f"{downloaded_mb:.1f} MB / {total_size_mb:.1f} MB"
                                    )
                                    
                                    last_update_size = downloaded
                                    
                                    # 다운로드가 예상보다 훨씬 큰 경우 중단 (보안상)
                                    if downloaded > 200 * 1024 * 1024:  # 200MB 초과
                                        logging.error("다운로드 크기가 예상보다 너무 큽니다. 보안상 중단합니다.")
                                        raise ValueError("파일 크기가 너무 큽니다.")
                                        
                except PermissionError:
                    self.update_progress("오류", "파일을 저장할 권한이 없습니다.", 0)
                    threading.Timer(2, self.show_update_error, args=["파일 저장 실패: 권한이 거부되었습니다. 관리자 권한으로 실행해보세요."]).start()
                    return
                except OSError as disk_error:
                    error_msg = str(disk_error).lower()
                    if "no space" in error_msg or "disk full" in error_msg or "디스크" in error_msg:
                        self.update_progress("오류", "디스크 공간이 부족합니다.", 0)
                        threading.Timer(2, self.show_update_error, args=["업데이트 실패: 디스크 공간이 부족합니다."]).start()
                    else:
                        self.update_progress("오류", "파일 저장 중 오류가 발생했습니다.", 0)
                        threading.Timer(2, self.show_update_error, args=[f"파일 저장 실패: {str(disk_error)}"]).start()
                    return
                
                # 다운로드 완료 후 파일 검증
                if not os.path.exists(temp_file):
                    logging.error("다운로드된 파일을 찾을 수 없습니다.")
                    self.update_progress("오류", "다운로드된 파일을 찾을 수 없습니다.", 0)
                    threading.Timer(2, self.show_update_error, args=["업데이트 실패: 다운로드된 파일을 확인할 수 없습니다."]).start()
                    return
                
                # 파일 크기 검증
                actual_size = os.path.getsize(temp_file)
                if actual_size < 1024 * 1024:  # 1MB 미만인 경우 의심
                    logging.warning(f"다운로드된 파일 크기가 의외로 작습니다: {actual_size} bytes")
                
                # 다운로드 완료, 설치 준비
                self.update_progress("설치 준비 중...", "업데이트를 적용합니다.", 0.7)
                time.sleep(0.5)  # UI 업데이트를 위한 약간의 지연
                
                # 업데이트 적용
                self.update_progress("업데이트 적용 중...", "Installer를 실행합니다.", 0.85)
                
                # 업데이트 완료 메시지
                self.update_progress("완료", "업데이트가 준비되었습니다. Installer를 실행합니다.", 1.0)
                time.sleep(1)
                
                # Installer 실행 명령 (Inno Setup 표준 파라미터)
                cmd = [
                    temp_file,
                    "/SILENT",              # 사용자 인터페이스 없이 설치
                    "/SUPPRESSMSGBOXES",    # 모든 메시지 박스 억제
                    "/CLOSEAPPLICATIONS",   # 실행 중인 앱 자동 종료
                    "/RESTARTAPPLICATIONS", # 설치 후 앱 자동 재시작
                    "/NOCANCEL"             # 설치 취소 불가
                ]
                
                # 현재 관리자 권한 상태 확인
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() if sys.platform == 'win32' else False
                
                # Installer 실행
                try:
                    if sys.platform == 'win32':
                        if not is_admin:
                            # 관리자 권한으로 실행 (Inno Setup installer는 관리자 권한 필요)
                            logging.info("관리자 권한으로 Installer를 실행합니다.")
                            ctypes.windll.shell32.ShellExecuteW(
                                None, 
                                "runas",  # 관리자 권한으로 실행 
                                temp_file, 
                                ' '.join(cmd[1:]),  # 첫 번째 인자(파일명) 제외
                                None, 
                                1  # SW_SHOWNORMAL
                            )
                        else:
                            # 이미 관리자 권한이 있는 경우 권한 상속으로 실행
                            logging.info("기존 관리자 권한으로 Installer를 실행합니다.")
                            subprocess.Popen(cmd)
                    else:
                        # 다른 플랫폼의 경우 일반 실행
                        subprocess.Popen(cmd, start_new_session=True)
                        
                except Exception as e:
                    logging.error(f"Installer 실행 실패: {str(e)}")
                    # 실패 시 일반 모드로 다시 시도
                    try:
                        subprocess.Popen([temp_file])
                        logging.info("일반 모드로 Installer 실행 재시도")
                    except Exception as e2:
                        logging.error(f"Installer 재시도 실패: {str(e2)}")
                        self.update_progress("오류", "Installer 실행에 실패했습니다.", 0)
                        threading.Timer(2, self.show_update_error, args=[f"Installer 실행 실패: {str(e2)}"]).start()
                        return
                
                # 업데이트 성공 기록 (Installer 실행 성공)
                try:
                    # GitHub release tag에서 버전 추출
                    latest_version = "unknown"
                    if hasattr(self, 'current_release_data') and self.current_release_data:
                        latest_version = self.current_release_data.get("tag_name", "").lstrip('v')
                    
                    # 업데이트 성공 기록
                    self._record_update_attempt(self.VERSION, latest_version, success=True)
                    logging.info(f"업데이트 성공 기록됨: {self.VERSION} -> {latest_version}")
                except Exception as record_error:
                    logging.error(f"업데이트 성공 기록 실패: {str(record_error)}")
                
                logging.info("업데이트가 시작되었습니다. 애플리케이션을 종료합니다.")
                
                # 프로그램 종료
                os._exit(0)
                
                # 성공적으로 완료되면 루프 종료
                return
                
            except PermissionError as e:
                if "액세스가 거부되었습니다" in str(e) and attempt < max_attempts - 1:
                    # 액세스 거부 오류가 발생하고 시도 횟수가 남아있으면 재시도
                    logging.warning(f"액세스 거부 오류 발생. 재시도 중... ({attempt+1}/{max_attempts}): {str(e)}")
                    self.update_progress("재시도 중...", f"액세스 거부 오류가 발생했습니다. 재시도 중... ({attempt+1}/{max_attempts})", 0.05)
                    time.sleep(1.5)  # 1.5초 대기 후 재시도
                    continue
                else:
                    # 최대 시도 횟수에 도달하면 오류 표시
                    logging.error(f"권한 오류 (최대 시도 횟수 초과): {str(e)}")
                    self.update_progress("오류", "파일 액세스 권한이 없습니다. 관리자 권한으로 실행해보세요.", 0)
                    threading.Timer(2, self.show_update_error, args=[f"업데이트 실패: 액세스가 거부되었습니다. 관리자 권한으로 프로그램을 실행하세요."]).start()
                    return
            except OSError as e:
                if "액세스가 거부되었습니다" in str(e) and attempt < max_attempts - 1:
                    # OS 오류지만 액세스 거부 문자열이 포함된 경우 재시도
                    logging.warning(f"OS 오류 (액세스 거부 관련) 발생. 재시도 중... ({attempt+1}/{max_attempts}): {str(e)}")
                    self.update_progress("재시도 중...", f"파일 시스템 오류가 발생했습니다. 재시도 중... ({attempt+1}/{max_attempts})", 0.05)
                    time.sleep(1.5)
                    continue
                else:
                    logging.error(f"OS 오류: {str(e)}")
                    self.update_progress("오류", f"파일 시스템 오류가 발생했습니다.", 0)
                    threading.Timer(2, self.show_update_error, args=[f"업데이트 실패: OS 오류 - {str(e)}"]).start()
                    return
            except Exception as e:
                error_msg = str(e).lower()
                if ("액세스가 거부되었습니다" in error_msg or "access is denied" in error_msg) and attempt < max_attempts - 1:
                    # 다른 예외지만 액세스 거부 문자열이 포함된 경우 재시도
                    logging.warning(f"액세스 거부 관련 오류 발생. 재시도 중... ({attempt+1}/{max_attempts}): {str(e)}")
                    self.update_progress("재시도 중...", f"액세스 거부 오류가 발생했습니다. 재시도 중... ({attempt+1}/{max_attempts})", 0.05)
                    time.sleep(1.5)  # 1.5초 대기 후 재시도
                    continue
                else:
                    # 그 외 다른 오류는 즉시 보고
                    logging.error(f"업데이트 실패: {str(e)}")
                    self.update_progress("오류", f"업데이트 중 오류가 발생했습니다.", 0)
                    threading.Timer(2, self.show_update_error, args=[f"업데이트 실패: {str(e)}"]).start()
                    return
    
    def download_updater_if_needed(self):
        """
        Installer 방식에서는 별도 업데이터가 필요하지 않음
        하위 호환성을 위해 메서드는 유지하되 None 반환
        """
        logging.info("Installer 방식으로 변경되어 별도 업데이터가 필요하지 않습니다.")
        return None
    
    def update_progress(self, status_text, detail_text, progress_value, download_info=None):
        """UI 진행 상황 업데이트"""
        # 창이 존재하고 표시되어 있는지 먼저 확인
        if self.update_window and self.update_window.winfo_exists() and self.update_window.winfo_viewable():
            try:
                # 메인 스레드에서 UI 업데이트
                self.update_window.after(0, lambda: self._update_progress_ui(
                    status_text, detail_text, progress_value, download_info
                ))
            except Exception as e:
                logging.error(f"진행 상황 업데이트 실패: {str(e)}")
    
    def _update_progress_ui(self, status_text, detail_text, progress_value, download_info):
        """UI 요소 실제 업데이트 (메인 스레드에서 호출)"""
        try:
            # 모든 UI 요소가 존재하는지 먼저 확인
            if (not self.update_window or 
                not self.update_window.winfo_exists() or
                not self.update_window.winfo_viewable()):
                return
                
            # 각 UI 요소가 존재하는지 확인 후 업데이트
            if self.progress_status and self.progress_status.winfo_exists():
                self.progress_status.configure(text=detail_text)
            
            if self.progress_bar and self.progress_bar.winfo_exists():
                self.progress_bar.set(progress_value)
            
            if self.download_info and self.download_info.winfo_exists() and download_info:
                self.download_info.configure(text=download_info)
            
            if self.status_label and self.status_label.winfo_exists():
                if status_text == "오류":
                    self.status_label.configure(
                        text="업데이트에 실패했습니다. 나중에 다시 시도하세요.",
                        text_color="#FF5555"
                    )
                else:
                    self.status_label.configure(
                        text="업데이트가 완료되면 프로그램이 자동으로 재시작됩니다.",
                        text_color="gray70"
                    )
        except Exception as e:
            logging.error(f"UI 업데이트 실패: {str(e)}")
    
    def show_update_error(self, error_message):
        """업데이트 오류 메시지 표시"""
        if self.update_window and self.update_window.winfo_exists():
            self.update_window.destroy()
            
        self.update_window = ctk.CTkToplevel(self.parent)
        self.update_window.title("업데이트 오류")
        self.update_window.geometry("400x240")  # 높이 증가
        self.update_window.resizable(False, False)
        
        # 아이콘 설정
        self.set_window_icon(self.update_window)
        
        # 화면 중앙에 표시
        if self.update_window.winfo_exists():
            self.update_window.update_idletasks()
            width = self.update_window.winfo_width()
            height = self.update_window.winfo_height()
            x = (self.update_window.winfo_screenwidth() // 2) - (width // 2)
            y = (self.update_window.winfo_screenheight() // 2) - (height // 2)
            self.update_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 오류 메시지
        ctk.CTkLabel(
            self.update_window,
            text="업데이트 오류",
            font=("Malgun Gothic", 16, "bold")
        ).pack(pady=(30, 5))
        
        ctk.CTkLabel(
            self.update_window,
            text=error_message,
            font=("Malgun Gothic", 12),
            wraplength=350
        ).pack(pady=(10, 20))
        
        # 자동 닫힘 카운트다운 라벨
        self.countdown_value = 10
        self.countdown_label = ctk.CTkLabel(
            self.update_window,
            text=f"{self.countdown_value}초 후 자동으로 닫힙니다...",
            font=("Malgun Gothic", 11),
            text_color="#888888"
        )
        self.countdown_label.pack(pady=(0, 15))
        
        # 카운트다운 시작
        self.start_countdown_timer()
        
        # 확인 버튼
        ctk.CTkButton(
            self.update_window,
            text="확인",
            font=("Malgun Gothic", 12),
            fg_color="#555555", 
            hover_color="#333333",
            command=self.update_window.destroy
        ).pack(pady=(0, 20))
        
        # 창 닫힘 이벤트 처리
        self.update_window.protocol("WM_DELETE_WINDOW", self.update_window.destroy)
    
    def get_updater_path(self):
        """업데이터 프로그램 경로 반환 (Installer 방식에서는 사용되지 않음)"""
        # 하위 호환성을 위해 메서드는 유지하되 None 반환
        logging.warning("get_updater_path 호출됨. Installer 방식에서는 별도 업데이터가 필요하지 않습니다.")
        return None
    
    def get_main_exe_path(self):
        """메인 실행 파일 경로 반환 (onedir 구조 고려)"""
        if getattr(sys, 'frozen', False):
            # onedir 구조에서는 sys.executable이 메인 실행 파일
            return sys.executable
        else:
            # 개발 환경인 경우 현재 스크립트 경로
            return os.path.abspath(__file__)
    
    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(base_path, relative_path)
        except Exception:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
    
    def set_window_icon(self, window):
        """창 아이콘 설정"""
        if sys.platform.startswith('win') and os.path.exists(self.icon_path):
            try:
                window.iconbitmap(self.icon_path)
                # 260ms 후 다시 시도 (tkinter가 때때로 첫 시도에 아이콘을 설정하지 못하는 문제 해결)
                window.after(260, lambda: self.try_set_icon_again(window))
            except Exception as e:
                logging.error(f"아이콘 설정 실패: {str(e)}")
                # 오류 발생 시 520ms 후 다시 시도
                window.after(520, lambda: self.try_set_icon_again(window))
                
    def try_set_icon_again(self, window):
        """지연 후 아이콘 설정 다시 시도"""
        if sys.platform.startswith('win'):
            try:
                window.iconbitmap(self.icon_path)
                
                # 작업 표시줄 아이콘 설정을 위한 추가 코드
                try:
                    import ctypes
                    
                    # 현재 창의 핸들 가져오기
                    hwnd = window.winfo_id()
                    
                    # 작업 표시줄 그룹화 식별자(AppUserModelID) 설정
                    app_id = "IMM.dNote.UpdateManager.Window"
                    try:
                        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                    except Exception as e:
                        logging.error(f"AppUserModelID 설정 오류: {e}")
                    
                    # 윈도우 스타일 수정 - 작업 표시줄에 표시되도록 (ctypes 사용)
                    GWL_EXSTYLE = -20
                    WS_EX_APPWINDOW = 0x00040000
                    WS_EX_TOOLWINDOW = 0x00000080
                    
                    # 현재 창 스타일 가져오기
                    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    # 툴 윈도우 스타일 제거, 앱 윈도우 스타일 추가
                    new_style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
                    # 스타일 적용
                    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
                    
                    # 작업 표시줄 업데이트 강제
                    WM_ACTIVATE = 0x0006
                    WA_ACTIVE = 1
                    ctypes.windll.user32.SendMessageW(hwnd, WM_ACTIVATE, WA_ACTIVE, 0)
                    
                except Exception as e:
                    logging.error(f"작업 표시줄 설정 오류: {e}")
                    
            except Exception as e:
                logging.error(f"두 번째 아이콘 설정 시도 실패: {e}")

    def _ensure_update_history_dir(self):
        """업데이트 이력 디렉토리 확인 및 생성"""
        history_dir = os.path.dirname(self.update_history_file)
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)
            
    def _load_update_history(self):
        """업데이트 이력 로드"""
        default_history = {
            "last_update_time": 0,
            "last_update_version": "",
            "last_update_date": "",
            "update_attempts": 0,
            "updates": []
        }
        
        try:
            if not os.path.exists(self.update_history_file):
                logging.info("업데이트 이력 파일이 없습니다. 기본값으로 초기화합니다.")
                return default_history
            
            # 파일 크기 확인 (0바이트 파일 처리)
            if os.path.getsize(self.update_history_file) == 0:
                logging.warning("업데이트 이력 파일이 비어있습니다. 기본값으로 초기화합니다.")
                return default_history
            
            with open(self.update_history_file, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError as json_error:
                    logging.error(f"업데이트 이력 파일 JSON 파싱 오류: {str(json_error)}")
                    # 백업 파일 생성
                    try:
                        backup_file = self.update_history_file + f".backup_{int(time.time())}"
                        with open(backup_file, 'w', encoding='utf-8') as backup:
                            with open(self.update_history_file, 'r', encoding='utf-8') as orig:
                                backup.write(orig.read())
                        logging.info(f"손상된 파일을 백업했습니다: {backup_file}")
                    except Exception as backup_error:
                        logging.error(f"백업 생성 실패: {str(backup_error)}")
                    return default_history
                
                # 필수 키들이 있는지 확인하고 없으면 기본값으로 설정
                for key, default_value in default_history.items():
                    if key not in history:
                        logging.warning(f"업데이트 이력에서 누락된 키 '{key}' 발견. 기본값으로 설정합니다.")
                        history[key] = default_value
                
                # 데이터 타입 검증
                if not isinstance(history.get("updates", []), list):
                    logging.warning("업데이트 목록이 리스트가 아닙니다. 빈 리스트로 초기화합니다.")
                    history["updates"] = []
                
                if not isinstance(history.get("last_update_time", 0), (int, float)):
                    logging.warning("마지막 업데이트 시간이 올바르지 않습니다. 0으로 초기화합니다.")
                    history["last_update_time"] = 0
                
                if not isinstance(history.get("update_attempts", 0), int):
                    logging.warning("업데이트 시도 횟수가 올바르지 않습니다. 0으로 초기화합니다.")
                    history["update_attempts"] = 0
                
                logging.debug("업데이트 이력 로드 완료")
                return history
                
        except FileNotFoundError:
            logging.info("업데이트 이력 파일을 찾을 수 없습니다. 기본값으로 초기화합니다.")
            return default_history
        except PermissionError:
            logging.error(f"업데이트 이력 파일 읽기 권한이 없습니다: {self.update_history_file}")
            return default_history
        except OSError as os_error:
            logging.error(f"업데이트 이력 파일 읽기 중 OS 오류: {str(os_error)}")
            return default_history
        except Exception as e:
            logging.error(f"업데이트 이력 로드 중 예상치 못한 오류: {str(e)}")
            return default_history
    
    def _save_update_history(self, history):
        """업데이트 이력 파일 저장"""
        try:
            # 디렉토리가 존재하는지 확인
            history_dir = os.path.dirname(self.update_history_file)
            if not os.path.exists(history_dir):
                os.makedirs(history_dir, exist_ok=True)
                logging.info(f"업데이트 이력 디렉토리 생성: {history_dir}")
                
            # 임시 파일에 먼저 쓰고 나중에 이동 (원자적 쓰기)
            temp_file = self.update_history_file + ".tmp"
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
            # 임시 파일을 실제 파일로 이동
            os.replace(temp_file, self.update_history_file)
            logging.debug("업데이트 이력 저장 완료")
            return True
            
        except PermissionError:
            logging.error(f"업데이트 이력 파일 쓰기 권한이 없습니다: {self.update_history_file}")
            return False
        except OSError as e:
            logging.error(f"업데이트 이력 파일 저장 중 OS 오류: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"업데이트 이력 파일 저장 중 예상치 못한 오류: {str(e)}")
            # 임시 파일 정리
            try:
                temp_file = self.update_history_file + ".tmp"
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as cleanup_error:
                logging.error(f"임시 파일 정리 실패: {str(cleanup_error)}")
            return False
    
    def _record_update_attempt(self, from_version, to_version, success=True):
        """업데이트 시도 기록"""
        history = self._load_update_history()
        
        # 현재 날짜 포맷 (YYYY-MM-DD)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 오늘 날짜의 업데이트 횟수 계산
        today_updates = [u for u in history["updates"] if u.get("date") == today]
        
        # 신규 업데이트 정보
        update_record = {
            "from_version": from_version,
            "to_version": to_version,
            "timestamp": time.time(),
            "date": today,
            "success": success
        }
        
        # 업데이트 목록에 추가
        history["updates"].append(update_record)
        
        # 100개만 유지 (오래된 것 삭제)
        if len(history["updates"]) > 100:
            history["updates"] = history["updates"][-100:]
            
        # 마지막 업데이트 시간 기록
        if success:
            history["last_update_time"] = time.time()
            history["last_update_version"] = to_version
            
        # 오늘 시도한 횟수 기록
        history["update_attempts"] = len(today_updates) + (1 if success else 0)
        history["last_update_date"] = today
        
        # 저장
        return self._save_update_history(history)
        
    def _should_skip_update(self, to_version):
        """
        업데이트를 건너뛸지 결정하는 로직
        - 10분 이내에 이미 업데이트한 경우
        - 24시간 이내에 동일한 버전으로 업데이트한 경우  
        - 하루 최대 업데이트 횟수를 초과한 경우
        - 동일한 버전으로 반복 업데이트를 시도하는 경우
        """
        try:
            history = self._load_update_history()
            current_time = time.time()
            
            # 잘못된 데이터 검증
            if not isinstance(history, dict):
                logging.error("업데이트 이력 데이터가 올바르지 않습니다. 업데이트를 진행합니다.")
                return False, ""
            
            # 1. 10분 이내 업데이트 확인 (최우선 체크)
            last_update_time = history.get("last_update_time", 0)
            if isinstance(last_update_time, (int, float)) and last_update_time > 0:
                try:
                    minutes_since_last_update = (current_time - last_update_time) / 60
                    
                    # 시간 계산이 음수가 나오는 경우 (시스템 시간 변경 등)
                    if minutes_since_last_update < 0:
                        logging.warning("시스템 시간이 이전으로 변경된 것 같습니다. 업데이트 진행을 허용합니다.")
                        return False, ""
                    
                    if minutes_since_last_update < self.update_cooldown_minutes:
                        remaining_minutes = self.update_cooldown_minutes - minutes_since_last_update
                        logging.warning(f"10분 쿨다운 적용: 최근 {minutes_since_last_update:.1f}분 전에 업데이트했습니다.")
                        return True, f"최근 {int(minutes_since_last_update)}분 전에 업데이트했습니다. {int(remaining_minutes) + 1}분 후에 다시 시도하세요."
                        
                except (ValueError, TypeError, OverflowError) as time_error:
                    logging.error(f"시간 계산 오류: {str(time_error)}. 안전하게 업데이트를 허용합니다.")
                    return False, ""
            
            # 2. 24시간 이내 동일 버전으로의 업데이트 확인
            if isinstance(last_update_time, (int, float)) and last_update_time > 0:
                try:
                    hours_since_last_update = (current_time - last_update_time) / 3600
                    last_version = history.get("last_update_version", "")
                    
                    # 시간 계산이 음수가 나오는 경우
                    if hours_since_last_update < 0:
                        logging.warning("시스템 시간 변경 감지. 24시간 체크를 건너뜁니다.")
                    elif (hours_since_last_update < self.update_cooldown_hours and 
                          isinstance(last_version, str) and 
                          last_version == to_version and 
                          last_version.strip() != ""):
                        logging.warning(f"24시간 쿨다운 적용: 최근 {hours_since_last_update:.1f}시간 전에 같은 버전({to_version})으로 업데이트했습니다.")
                        return True, f"최근 {int(hours_since_last_update)}시간 전에 같은 버전으로 업데이트했습니다."
                        
                except (ValueError, TypeError, OverflowError) as time_error:
                    logging.error(f"24시간 체크 중 시간 계산 오류: {str(time_error)}")
            
            # 3. 오늘 시도한 업데이트 횟수 확인
            try:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                last_update_date = history.get("last_update_date", "")
                update_attempts = history.get("update_attempts", 0)
                
                if (isinstance(last_update_date, str) and 
                    last_update_date == today and 
                    isinstance(update_attempts, int) and 
                    update_attempts >= self.max_updates_per_day):
                    logging.warning(f"일일 업데이트 한도 초과: 오늘({today}) 이미 {update_attempts}번 시도했습니다.")
                    return True, f"오늘 이미 {update_attempts}번 업데이트를 시도했습니다. 내일 다시 시도하세요."
                    
            except (ValueError, TypeError) as date_error:
                logging.error(f"날짜 처리 오류: {str(date_error)}")
            
            # 4. 최근 실패한 업데이트 확인 (같은 버전으로 여러번 실패한 경우)
            try:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                updates_list = history.get("updates", [])
                
                if isinstance(updates_list, list):
                    today_updates = [u for u in updates_list if isinstance(u, dict) and u.get("date") == today]
                    failed_attempts = [
                        u for u in today_updates 
                        if (isinstance(u.get("to_version"), str) and 
                            u.get("to_version") == to_version and 
                            not u.get("success", True))
                    ]
                    
                    if len(failed_attempts) >= 2:  # 같은 버전으로 2회 이상 실패한 경우
                        logging.warning(f"반복 실패 감지: 오늘 같은 버전({to_version})으로 이미 {len(failed_attempts)}번 실패했습니다.")
                        return True, f"같은 버전으로 여러 번 업데이트에 실패했습니다. 내일 다시 시도하세요."
                        
            except (ValueError, TypeError) as list_error:
                logging.error(f"실패 이력 체크 중 오류: {str(list_error)}")
            
            # 업데이트 진행 가능
            logging.info(f"업데이트 스킵 검사 통과: 버전 {to_version} 업데이트 진행")
            return False, ""
        
        except Exception as e:
            logging.error(f"업데이트 스킵 검사 중 예상치 못한 오류 발생: {str(e)}")
            # 오류 발생 시 안전하게 업데이트 진행 (기본 정책)
            logging.info("오류 발생으로 인해 업데이트를 허용합니다.")
            return False, ""

    def show_update_skip_notice(self, reason):
        """업데이트 건너뛰기 알림 표시"""
        if self.update_window and self.update_window.winfo_exists():
            self.update_window.destroy()
            
        self.update_window = ctk.CTkToplevel(self.parent)
        self.update_window.title("업데이트 건너뛰기")
        self.update_window.geometry("400x240")  # 높이 증가
        self.update_window.resizable(False, False)
        
        # 아이콘 설정
        self.set_window_icon(self.update_window)
        
        # 화면 중앙에 표시
        if self.update_window.winfo_exists():
            self.update_window.update_idletasks()
            width = self.update_window.winfo_width()
            height = self.update_window.winfo_height()
            x = (self.update_window.winfo_screenwidth() // 2) - (width // 2)
            y = (self.update_window.winfo_screenheight() // 2) - (height // 2)
            self.update_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 알림 메시지
        ctk.CTkLabel(
            self.update_window,
            text="업데이트 건너뛰기",
            font=("Malgun Gothic", 16, "bold")
        ).pack(pady=(30, 5))
        
        ctk.CTkLabel(
            self.update_window,
            text=reason,
            font=("Malgun Gothic", 12),
            wraplength=350
        ).pack(pady=(10, 20))
        
        # 자동 닫힘 카운트다운 라벨
        self.countdown_value = 10
        self.countdown_label = ctk.CTkLabel(
            self.update_window,
            text=f"{self.countdown_value}초 후 자동으로 닫힙니다...",
            font=("Malgun Gothic", 11),
            text_color="#888888"
        )
        self.countdown_label.pack(pady=(0, 15))
        
        # 카운트다운 시작
        self.start_countdown_timer()
        
        # 확인 버튼
        ctk.CTkButton(
            self.update_window,
            text="확인",
            font=("Malgun Gothic", 12),
            fg_color="#555555", 
            hover_color="#333333",
            command=self.update_window.destroy
        ).pack(pady=(0, 20))
        
        # 창 닫힘 이벤트 처리
        self.update_window.protocol("WM_DELETE_WINDOW", self.update_window.destroy)

    def start_countdown_timer(self):
        """창 자동 닫힘을 위한 카운트다운 타이머 시작"""
        if not self.update_window or not self.update_window.winfo_exists() or not hasattr(self, 'countdown_label'):
            return
            
        # 카운트다운 값 감소
        self.countdown_value -= 1
        
        if self.countdown_value <= 0:
            # 카운트다운 종료, 창 닫기
            if self.update_window and self.update_window.winfo_exists():
                self.update_window.destroy()
            return
            
        # 카운트다운 텍스트 업데이트
        if self.countdown_label and self.countdown_label.winfo_exists():
            self.countdown_label.configure(text=f"{self.countdown_value}초 후 자동으로 닫힙니다...")
            
        # 1초 후 다시 호출
        if self.update_window and self.update_window.winfo_exists():
            self.update_window.after(1000, self.start_countdown_timer)