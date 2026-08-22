"""
KIS Open API Automated Stock Trading System - Version 1.0
Production-grade Windows desktop application using PySide6
Korean Stock Market (KOSPI/KOSDAQ) automated trading
"""

import sys
import os
import json
import time
import logging
import sqlite3
import threading
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
import queue

import requests
import websocket

# ─────────────────────────────────────────────────────────────────────────────
# BILINGUAL STRINGS  (ko = Korean, en = English)
# Toggle at runtime via the 🌐 button — no restart needed.
# ─────────────────────────────────────────────────────────────────────────────

_LANG: str = "ko"   # default: Korean

STRINGS: Dict[str, Dict[str, str]] = {
    # ── top bar ──────────────────────────────────────────────────────────────
    "symbol_code":          {"ko": "종목코드",         "en": "Symbol"},
    "stock_name":           {"ko": "종목명",           "en": "Stock Name"},
    "current_price":        {"ko": "현재가",           "en": "Price"},
    "volume_lbl":           {"ko": "거래량: --",       "en": "Volume: --"},
    "start_lbl":            {"ko": "시작",             "en": "Start"},
    "end_lbl":              {"ko": "종료",             "en": "End"},
    "btn_start":            {"ko": "START\n자동매매",  "en": "START\nAuto Trade"},
    "btn_stop":             {"ko": "STOP\n자동매매",   "en": "STOP\nAuto Trade"},
    # ── chart area ───────────────────────────────────────────────────────────
    "select_stock":         {"ko": "종목선택",         "en": "Select Stock"},
    "chart_note":           {"ko": "* 차트 데이터는 실제와 다를 수 있습니다.",
                             "en": "* Chart data may differ from actual values."},
    "realtime_tick":        {"ko": "실시간 틱",        "en": "Real-time Tick"},
    # ── trade history ────────────────────────────────────────────────────────
    "trade_history":        {"ko": "TRADE HISTORY (오늘)", "en": "TRADE HISTORY (Today)"},
    "col_time":             {"ko": "시간",             "en": "Time"},
    "col_type":             {"ko": "구분",             "en": "Type"},
    "col_price":            {"ko": "가격(KRW)",        "en": "Price(KRW)"},
    "col_qty":              {"ko": "수량",             "en": "Qty"},
    "col_reason":           {"ko": "사유",             "en": "Reason"},
    "col_ticks":            {"ko": "변화(틱)",         "en": "Chg(Ticks)"},
    "col_high":             {"ko": "고가(KRW)",        "en": "High(KRW)"},
    "col_pnl":              {"ko": "P/L(KRW)",        "en": "P/L(KRW)"},
    # ── bottom status bar ────────────────────────────────────────────────────
    "order_status_ok":      {"ko": "주문상태: 정상",   "en": "Order: Normal"},
    "position_lbl":         {"ko": "포지션: 0주",      "en": "Position: 0 shs"},
    "avg_price_lbl":        {"ko": "평균가: --",       "en": "Avg: --"},
    "cur_price_lbl":        {"ko": "현재가: --",       "en": "Price: --"},
    # ── statusbar (bottom of window) ─────────────────────────────────────────
    "not_connected":        {"ko": "● 연결 안됨",      "en": "● Not Connected"},
    "ws_disconnected":      {"ko": "● WebSocket 끊김", "en": "● WebSocket Off"},
    # ── right panel ──────────────────────────────────────────────────────────
    "unrealized_pnl":       {"ko": "미실현손익",       "en": "Unrealized P/L"},
    "realized_pnl":         {"ko": "실현손익",         "en": "Realized P/L"},
    "total_pnl":            {"ko": "총손익(오늘)",     "en": "Total P/L(Today)"},
    "total_trades":         {"ko": "총거래",           "en": "Total Trades"},
    "win_loss":             {"ko": "익/손",            "en": "Win/Loss"},
    "win_rate":             {"ko": "승률",             "en": "Win Rate"},
    "idle_status":          {"ko": "대기 중",          "en": "Idle"},
    "basic_stop_lbl":       {"ko": "기본 손절",        "en": "Basic Stop"},
    "trailing_lbl":         {"ko": "추격 익절 (상승 후)", "en": "Trailing TP"},
    "stagnation_sell_lbl":  {"ko": "정체 매도",        "en": "Stagnation Exit"},
    "order_qty_lbl":        {"ko": "주문 수량",        "en": "Order Qty"},
    "shares_unit":          {"ko": "주",               "en": "shs"},
    "avail_lbl":            {"ko": "가용: 100주",      "en": "Avail: 100 shs"},
    "pos_box":              {"ko": "현재 포지션",      "en": "Current Position"},
    "pos_qty":              {"ko": "보유 수량",        "en": "Holding Qty"},
    "pos_avg":              {"ko": "평균 매수가",      "en": "Avg Buy Price"},
    "pos_high":             {"ko": "매수 후 최고가",   "en": "High After Buy"},
    "pos_trigger":          {"ko": "현재 매도 기준",   "en": "Sell Trigger"},
    "emergency_btn":        {"ko": "⛔ EMERGENCY STOP\n(전체 주문 취소)",
                             "en": "⛔ EMERGENCY STOP\n(Cancel All Orders)"},
    "btn_export":           {"ko": "💾 거래내역 저장", "en": "💾 Export Trades"},
    "btn_exit":             {"ko": "❌ 종료",          "en": "❌ Exit"},
    # ── settings dialog ──────────────────────────────────────────────────────
    "settings_title":       {"ko": "설정",             "en": "Settings"},
    "tab_api":              {"ko": "API 설정",         "en": "API Settings"},
    "tab_buy":              {"ko": "매수 조건",        "en": "Buy Conditions"},
    "tab_sell":             {"ko": "매도 조건",        "en": "Sell Conditions"},
    "tab_risk":             {"ko": "리스크 관리",      "en": "Risk Management"},
    "tab_time":             {"ko": "시간 설정",        "en": "Time Settings"},
    "env_lbl":              {"ko": "환경:",            "en": "Environment:"},
    "paper_check":          {"ko": "모의 투자 (Paper Trading)", "en": "Paper Trading"},
    "account_no":           {"ko": "계좌번호:",        "en": "Account No:"},
    "account_sfx":          {"ko": "계좌 상품코드:",   "en": "Account Suffix:"},
    "buy_cond1":            {"ko": "매수조건 1 - 20MA 눌림", "en": "Buy Cond 1 – 20MA Pullback"},
    "buy_cond2":            {"ko": "매수조건 2 - 급등",     "en": "Buy Cond 2 – Rapid Rise"},
    "buy_cond3":            {"ko": "매수조건 3 - 급락 후 반등", "en": "Buy Cond 3 – Rebound After Drop"},
    "enable":               {"ko": "활성화:",          "en": "Enable:"},
    "proximity_ticks":      {"ko": "근접 틱:",         "en": "Proximity Ticks:"},
    "recovery_ticks":       {"ko": "회복 틱:",         "en": "Recovery Ticks:"},
    "rise_ticks":           {"ko": "상승 틱:",         "en": "Rise Ticks:"},
    "drop_ticks":           {"ko": "하락 틱:",         "en": "Drop Ticks:"},
    "rebound_ticks":        {"ko": "반등 틱:",         "en": "Rebound Ticks:"},
    "seconds":              {"ko": "초:",              "en": "Seconds:"},
    "basic_stop_box":       {"ko": "기본 손절",        "en": "Basic Stop-Loss"},
    "stop_ticks":           {"ko": "손절 틱:",         "en": "Stop Ticks:"},
    "stag_sell_box":        {"ko": "정체 매도",        "en": "Stagnation Exit"},
    "stag_secs":            {"ko": "정체 초:",         "en": "Stagnation Secs:"},
    "max_daily_loss":       {"ko": "최대 일일 손실 (KRW):", "en": "Max Daily Loss (KRW):"},
    "max_trades":           {"ko": "최대 일일 거래 횟수:", "en": "Max Trades/Day:"},
    "order_qty_form":       {"ko": "주문 수량:",       "en": "Order Qty:"},
    "reentry_wait":         {"ko": "재진입 대기 (초):", "en": "Re-entry Wait (s):"},
    "trade_start":          {"ko": "매매 시작:",       "en": "Trade Start:"},
    "trade_end":            {"ko": "매매 종료:",       "en": "Trade End:"},
    "block_first":          {"ko": "장 시작 후 매수 차단 (분):", "en": "Block Buy First (min):"},
    "stag_buy_cancel":      {"ko": "매수 정체 취소 (초):", "en": "Buy Stagnation Cancel (s):"},
    "stag_reentry":         {"ko": "정체 후 재진입 대기 (초):", "en": "Re-entry After Stagnation (s):"},
    # ── dialogs / messages ───────────────────────────────────────────────────
    "warning":              {"ko": "경고",             "en": "Warning"},
    "error_title":          {"ko": "오류",             "en": "Error"},
    "enter_api_first":      {"ko": "먼저 설정에서 API 정보를 입력하세요.",
                             "en": "Please enter API credentials in Settings first."},
    "enter_api_warn":       {"ko": "설정에서 API 정보를 입력하세요.",
                             "en": "Enter API credentials in Settings."},
    "select_stock_warn":    {"ko": "종목을 먼저 선택하세요.",
                             "en": "Please select a stock first."},
    "stock_not_found":      {"ko": "종목을 찾을 수 없습니다: ",
                             "en": "Stock not found: "},
    "start_confirm_title":  {"ko": "자동매매 시작",    "en": "Start Auto-Trading"},
    "start_confirm_msg":    {"ko": "자동매매를 시작하시겠습니까?\n환경: {mode}\n종목: {stock}",
                             "en": "Start auto-trading?\nMode: {mode}\nStock: {stock}"},
    "paper_mode":           {"ko": "모의투자",         "en": "Paper"},
    "live_mode":            {"ko": "실거래",           "en": "Live"},
    "stop_confirm_title":   {"ko": "자동매매 중지",    "en": "Stop Auto-Trading"},
    "stop_confirm_msg":     {"ko": "자동매매를 중지하시겠습니까?",
                             "en": "Stop auto-trading?"},
    "emergency_title":      {"ko": "⛔ 긴급 정지",    "en": "⛔ Emergency Stop"},
    "emergency_msg":        {"ko": "긴급 정지를 실행하시겠습니까?\n\n모든 주문이 취소됩니다.",
                             "en": "Execute emergency stop?\n\nAll orders will be cancelled."},
    "liquidate_title":      {"ko": "포지션 처리",      "en": "Position Handling"},
    "liquidate_msg":        {"ko": "현재 보유 포지션을 청산하시겠습니까?",
                             "en": "Liquidate current position?"},
    "log_title":            {"ko": "시스템 로그",      "en": "System Log"},
    "log_no_file":          {"ko": "로그 파일 없음",   "en": "No log file found"},
    "export_title":         {"ko": "거래내역 저장",    "en": "Export Trades"},
    "export_done_title":    {"ko": "완료",             "en": "Done"},
    "export_done_msg":      {"ko": "저장 완료:\n",     "en": "Saved to:\n"},
    "exit_title":           {"ko": "종료",             "en": "Exit"},
    "exit_msg":             {"ko": "프로그램을 종료하시겠습니까?",
                             "en": "Exit the program?"},
    # ── log messages (engine) ────────────────────────────────────────────────
    "log_init":             {"ko": "시스템 초기화 완료. 설정에서 API 정보를 입력하세요.",
                             "en": "System ready. Enter API credentials in Settings."},
    "log_settings_saved":   {"ko": "설정 저장됨",      "en": "Settings saved"},
    "log_ws_connected":     {"ko": "연결",             "en": "connected"},
    "log_ws_disconnected":  {"ko": "끊김",             "en": "disconnected"},
    "log_stock_selected":   {"ko": "종목 선택: {name} ({sym}) @ {price:,}원",
                             "en": "Stock selected: {name} ({sym}) @ {price:,} KRW"},
    "log_auth_fail":        {"ko": "❌ API 인증 실패", "en": "❌ API auth failed"},
    "log_stock_fail":       {"ko": "❌ 종목 조회 실패: ", "en": "❌ Stock lookup failed: "},
    "log_start":            {"ko": "✅ 자동매매 시작 [{mode}]",
                             "en": "✅ Auto-trading started [{mode}]"},
    "log_stop":             {"ko": "⏹ 자동매매 중지", "en": "⏹ Auto-trading stopped"},
    "log_emergency":        {"ko": "⛔ 긴급 정지 실행 (청산={v})",
                             "en": "⛔ Emergency stop (liquidate={v})"},
    "log_export":           {"ko": "거래내역 저장: ",  "en": "Trades exported: "},
    "log_conn_warn":        {"ko": "⚠ 연결 상태 이상 감지 - 자동매매 일시 중단",
                             "en": "⚠ Connection issue detected – auto-trading paused"},
    "log_error_prefix":     {"ko": "⚠ 오류: ",        "en": "⚠ Error: "},
    "ws_connected_lbl":     {"ko": "● WebSocket 연결됨", "en": "● WebSocket On"},
    "kis_connected_lbl":    {"ko": "● KIS 연결됨",    "en": "● KIS Connected"},
    "order_lbl":            {"ko": "주문: ",           "en": "Order: "},
    "cur_price_fmt":        {"ko": "현재가: {p:,}",    "en": "Price: {p:,}"},
    "position_fmt":         {"ko": "포지션: {q}주",    "en": "Position: {q} shs"},
    "avg_fmt":              {"ko": "평균가: {p:,}",    "en": "Avg: {p:,}"},
    "avg_none":             {"ko": "평균가: --",       "en": "Avg: --"},
    "pos_qty_fmt":          {"ko": "{q}주",            "en": "{q} shs"},
    "pos_avg_fmt":          {"ko": "{p:,}원",          "en": "{p:,} KRW"},
    "trade_buy":            {"ko": "▲ 매수",           "en": "▲ Buy"},
    "trade_sell":           {"ko": "▼ 매도",           "en": "▼ Sell"},
    "yes":                  {"ko": "예",               "en": "Yes"},
    "no":                   {"ko": "아니오",           "en": "No"},
}


def tr(key: str, **kwargs) -> str:
    """Return translated string for current language, with optional format args."""
    text = STRINGS.get(key, {}).get(_LANG, STRINGS.get(key, {}).get("ko", key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QStatusBar, QSplitter, QFrame, QGroupBox, QDialog, QDialogButtonBox,
    QTabWidget, QTextEdit, QScrollArea, QMessageBox, QFileDialog,
    QHeaderView, QSizePolicy, QToolButton, QFormLayout
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QObject, QMutex, QMutexLocker,
    QDateTime, QSize, Slot
)
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QFontDatabase,
    QLinearGradient, QPolygonF, QPixmap, QIcon, QPalette, QAction
)
from PySide6.QtCharts import (
    QChart, QChartView, QCandlestickSeries, QCandlestickSet,
    QLineSeries, QValueAxis, QDateTimeAxis, QBarSeries, QBarSet,
    QBarCategoryAxis
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & ENUMS
# ─────────────────────────────────────────────────────────────────────────────

VERSION = "1.0"
APP_TITLE = f"AUTO TRADING SYSTEM v{VERSION}"

KIS_REAL_BASE = "https://openapi.koreainvestment.com:9443"
KIS_PAPER_BASE = "https://openapivts.koreainvestment.com:29443"
KIS_REAL_WS = "ws://ops.koreainvestment.com:21000"
KIS_PAPER_WS = "ws://ops.koreainvestment.com:31000"

DB_PATH = "trading_data.db"
CONFIG_PATH = "config.json"
LOG_PATH = "trading.log"

MARKET_OPEN = "09:00:00"
MARKET_CLOSE = "15:30:00"

# Korean tick size rules
TICK_RULES = [
    (2_000, 1),
    (5_000, 5),
    (20_000, 10),
    (50_000, 50),
    (200_000, 100),
    (500_000, 500),
    (float('inf'), 1000),
]


class SignalState(Enum):
    WATCHING = "Monitoring"
    SETUP_FORMING = "Buy Setup Forming"
    ARMED = "Armed"
    STAGNATION_CANCELLED = "Cancelled (Stagnation)"
    REENTRY_WAITING = "Re-Entry Waiting"
    PAUSED = "Paused"
    STOPPED = "Stopped"
    ERROR = "Error"


class OrderState(Enum):
    IDLE = "Idle"
    BUY_PENDING = "Buy Order Pending"
    BUY_PARTIAL = "Buy Partially Filled"
    HOLDING = "Holding"
    SELL_PENDING = "Sell Order Pending"
    SELL_PARTIAL = "Sell Partially Filled"
    CANCEL_PENDING = "Cancel Pending"
    RECONCILING = "Reconciling"
    FLAT = "Flat"
    PAUSED_ERROR = "Paused / Error"


class BuyReason(Enum):
    MA20_PULLBACK = "20MA Pullback Buy"
    RAPID_RISE = "Surge Buy"
    REBOUND = "Rebound Buy (After Drop)"


class SellReason(Enum):
    BASIC_STOP = "Basic Stop-Loss"
    TRAILING_TP = "Trailing TP"
    STAGNATION = "Stagnation Exit"
    RAPID_DROP = "Rapid Drop Sell"
    END_TIME = "End Time Liquidation"
    EMERGENCY = "Emergency Stop"


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging():
    logger = logging.getLogger("KISTrader")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


log = setup_logging()


# ─────────────────────────────────────────────────────────────────────────────
# TICK SIZE CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

def get_tick_size(price: int) -> int:
    """Return tick size for given price according to KRX rules."""
    for threshold, tick in TICK_RULES:
        if price < threshold:
            return tick
    return 1000


def price_to_ticks(price: int, ref_price: int) -> int:
    """Convert price difference to ticks (approximate, uses ref price tick)."""
    tick = get_tick_size(ref_price)
    if tick == 0:
        return 0
    return (price - ref_price) // tick


def ticks_to_price(ref_price: int, ticks: int) -> int:
    """Convert tick count to price from reference."""
    tick = get_tick_size(ref_price)
    return ref_price + ticks * tick


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._conn()
            c = conn.cursor()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS ticks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT, symbol TEXT, price INTEGER, volume INTEGER
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT, symbol TEXT, side TEXT,
                    broker_order_id TEXT, req_qty INTEGER,
                    filled_qty INTEGER, avg_price INTEGER,
                    status TEXT, reason TEXT
                );
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT, symbol TEXT, buy_time TEXT, sell_time TEXT,
                    buy_price INTEGER, sell_price INTEGER,
                    qty INTEGER, buy_reason TEXT, sell_reason TEXT,
                    high_after_buy INTEGER, pnl INTEGER, status TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT, event_type TEXT, detail TEXT
                );
            """)
            conn.commit()
            conn.close()

    def log_tick(self, symbol, price, volume):
        with self._lock:
            conn = self._conn()
            conn.execute(
                "INSERT INTO ticks (ts,symbol,price,volume) VALUES (?,?,?,?)",
                (datetime.now().isoformat(), symbol, price, volume)
            )
            conn.commit()
            conn.close()

    def save_order(self, symbol, side, broker_id, req_qty, filled_qty,
                   avg_price, status, reason=""):
        with self._lock:
            conn = self._conn()
            conn.execute(
                """INSERT INTO orders
                   (ts,symbol,side,broker_order_id,req_qty,filled_qty,
                    avg_price,status,reason)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (datetime.now().isoformat(), symbol, side, broker_id,
                 req_qty, filled_qty, avg_price, status, reason)
            )
            conn.commit()
            conn.close()

    def save_trade(self, symbol, buy_time, sell_time, buy_price, sell_price,
                   qty, buy_reason, sell_reason, high_after_buy, pnl):
        with self._lock:
            conn = self._conn()
            conn.execute(
                """INSERT INTO trades
                   (date,symbol,buy_time,sell_time,buy_price,sell_price,
                    qty,buy_reason,sell_reason,high_after_buy,pnl,status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,'COMPLETED')""",
                (datetime.now().date().isoformat(), symbol, buy_time,
                 sell_time, buy_price, sell_price, qty, buy_reason,
                 sell_reason, high_after_buy, pnl)
            )
            conn.commit()
            conn.close()

    def log_event(self, event_type, detail):
        # Sanitize sensitive info
        safe_detail = detail.replace("api_secret", "***").replace("token", "***")
        with self._lock:
            conn = self._conn()
            conn.execute(
                "INSERT INTO events (ts,event_type,detail) VALUES (?,?,?)",
                (datetime.now().isoformat(), event_type, safe_detail)
            )
            conn.commit()
            conn.close()

    def get_today_trades(self):
        with self._lock:
            conn = self._conn()
            today = datetime.now().date().isoformat()
            rows = conn.execute(
                "SELECT * FROM trades WHERE date=? ORDER BY id DESC", (today,)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def export_trades_csv(self, filepath):
        with self._lock:
            conn = self._conn()
            rows = conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
            conn.close()
        import csv
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if rows:
                writer.writerow(rows[0].keys())
                for r in rows:
                    writer.writerow(list(r))


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG MANAGER (secure local storage)
# ─────────────────────────────────────────────────────────────────────────────

class ConfigManager:
    DEFAULTS = {
        "is_paper": True,
        "app_key": "",
        "app_secret": "",
        "account_no": "",
        "account_suffix": "01",
        "order_qty": 10,
        "order_type": "MARKET",
        "start_time": "09:00:00",
        "end_time": "15:30:00",
        "block_buy_first_minutes": 0,
        "block_buy_before_close_minutes": 0,
        "end_time_action": "stop_buy",
        # Buy cond 1 - MA20
        "ma20_enabled": True,
        "ma20_proximity_ticks": 3,
        "ma20_recovery_ticks": 2,
        # Buy cond 2 - Rapid rise
        "rapid_rise_enabled": True,
        "rapid_rise_ticks": 5,
        "rapid_rise_seconds": 5,
        "rapid_rise_min_consecutive": 3,
        # Buy cond 3 - Rebound
        "rebound_enabled": True,
        "rebound_drop_ticks": 10,
        "rebound_up_ticks": 4,
        "rebound_seconds": 5,
        # Sideways filter
        "sideways_range_ticks": 3,
        "sideways_window_seconds": 30,
        # Stagnation
        "stagnation_buy_seconds": 2,
        "stagnation_reentry_seconds": 60,
        # Basic sell
        "basic_sell_enabled": True,
        "basic_sell_ticks": -2,
        # Trailing sell ranges
        "trailing_ranges": [
            {"min_ticks": 1, "max_ticks": 4, "pullback_ticks": 3},
            {"min_ticks": 5, "max_ticks": 9, "pullback_ticks": 4},
            {"min_ticks": 10, "max_ticks": 14, "pullback_ticks": 5},
        ],
        # Stagnation sell
        "stagnation_sell_enabled": True,
        "stagnation_sell_seconds": 2,
        # Limit order
        "limit_offset_ticks": 0,
        "limit_timeout_seconds": 10,
        # Risk limits
        "max_daily_loss": 500000,
        "max_trades_per_day": 50,
        "session_loss_limit": 300000,
        "reentry_wait_seconds": 3,
    }

    def __init__(self):
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.data.update(saved)
            except Exception as e:
                log.warning(f"Config load error: {e}")

    def save(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Config save error: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def set_many(self, d: dict):
        self.data.update(d)
        self.save()


# ─────────────────────────────────────────────────────────────────────────────
# KIS API CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class KISApiClient:
    def __init__(self, config: ConfigManager):
        self.config = config
        self._token = None
        self._token_expires = None
        self._lock = threading.Lock()

    @property
    def base_url(self):
        return KIS_PAPER_BASE if self.config.get("is_paper") else KIS_REAL_BASE

    def _headers(self, tr_id: str, extra: dict = None) -> dict:
        h = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._token}",
            "appkey": self.config.get("app_key"),
            "appsecret": self.config.get("app_secret"),
            "tr_id": tr_id,
            "custtype": "P",
        }
        if extra:
            h.update(extra)
        return h

    def get_token(self) -> bool:
        """Get access token. Returns True on success."""
        url = f"{self.base_url}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.config.get("app_key"),
            "appsecret": self.config.get("app_secret"),
        }
        try:
            r = requests.post(url, json=body, timeout=10)
            r.raise_for_status()
            d = r.json()
            self._token = d.get("access_token")
            expires_in = int(d.get("expires_in", 86400))
            self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
            log.info("KIS token obtained successfully")
            return True
        except Exception as e:
            log.error(f"Token error: {e}")
            return False

    def ensure_token(self):
        with self._lock:
            if not self._token or datetime.now() >= self._token_expires:
                self.get_token()

    def get_stock_info(self, symbol: str) -> dict:
        """Get current stock price and basic info."""
        self.ensure_token()
        tr_id = "FHKST01010100"  # paper uses same for inquiry
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
        }
        try:
            r = requests.get(url, headers=self._headers(tr_id), params=params, timeout=10)
            r.raise_for_status()
            d = r.json()
            if d.get("rt_cd") == "0":
                output = d.get("output", {})
                return {
                    "symbol": symbol,
                    "name": output.get("hts_kor_isnm", ""),
                    "price": int(output.get("stck_prpr", 0)),
                    "open": int(output.get("stck_oprc", 0)),
                    "high": int(output.get("stck_hgpr", 0)),
                    "low": int(output.get("stck_lwpr", 0)),
                    "volume": int(output.get("acml_vol", 0)),
                    "change": int(output.get("prdy_vrss", 0)),
                    "change_rate": float(output.get("prdy_ctrt", 0)),
                    "market": output.get("rprs_mrkt_kor_name", ""),
                }
        except Exception as e:
            log.error(f"Stock info error for {symbol}: {e}")
        return {}

    def get_account_balance(self) -> dict:
        """Get account holdings and balance."""
        self.ensure_token()
        tr_id = "VTTC8434R" if self.config.get("is_paper") else "TTTC8434R"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        params = {
            "CANO": self.config.get("account_no"),
            "ACNT_PRDT_CD": self.config.get("account_suffix", "01"),
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        try:
            r = requests.get(url, headers=self._headers(tr_id), params=params, timeout=10)
            r.raise_for_status()
            d = r.json()
            if d.get("rt_cd") == "0":
                output1 = d.get("output1", [])
                output2 = d.get("output2", [{}])
                holdings = {}
                for item in output1:
                    sym = item.get("pdno", "")
                    if sym:
                        holdings[sym] = {
                            "qty": int(item.get("hldg_qty", 0)),
                            "avg_price": int(float(item.get("pchs_avg_pric", 0))),
                            "current_price": int(item.get("prpr", 0)),
                            "pnl": int(item.get("evlu_pfls_amt", 0)),
                        }
                cash = int(float(output2[0].get("dnca_tot_amt", 0))) if output2 else 0
                return {"holdings": holdings, "cash": cash}
        except Exception as e:
            log.error(f"Balance error: {e}")
        return {"holdings": {}, "cash": 0}

    def get_outstanding_orders(self) -> list:
        """Get unfilled/pending orders."""
        self.ensure_token()
        tr_id = "VTTC8036R" if self.config.get("is_paper") else "TTTC8036R"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
        params = {
            "CANO": self.config.get("account_no"),
            "ACNT_PRDT_CD": self.config.get("account_suffix", "01"),
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
            "INQR_DVSN_1": "0",
            "INQR_DVSN_2": "0",
        }
        try:
            r = requests.get(url, headers=self._headers(tr_id), params=params, timeout=10)
            r.raise_for_status()
            d = r.json()
            if d.get("rt_cd") == "0":
                return d.get("output", [])
        except Exception as e:
            log.error(f"Outstanding orders error: {e}")
        return []

    def place_order(self, symbol: str, side: str, qty: int,
                    price: int = 0, order_type: str = "MARKET") -> dict:
        """Place buy or sell order. Returns order info dict."""
        self.ensure_token()
        is_paper = self.config.get("is_paper")
        if side == "BUY":
            tr_id = "VTTC0802U" if is_paper else "TTTC0802U"
        else:
            tr_id = "VTTC0801U" if is_paper else "TTTC0801U"

        # ord_dvsn: 00=limit, 01=market
        if order_type == "MARKET":
            ord_dvsn = "01"
            ord_unpr = "0"
        else:
            ord_dvsn = "00"
            ord_unpr = str(price)

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        body = {
            "CANO": self.config.get("account_no"),
            "ACNT_PRDT_CD": self.config.get("account_suffix", "01"),
            "PDNO": symbol,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(qty),
            "ORD_UNPR": ord_unpr,
        }
        try:
            r = requests.post(url, headers=self._headers(tr_id), json=body, timeout=10)
            r.raise_for_status()
            d = r.json()
            if d.get("rt_cd") == "0":
                output = d.get("output", {})
                order_id = output.get("ODNO", "")
                log.info(f"Order placed: {side} {qty}x{symbol} @ {price} → {order_id}")
                return {"success": True, "order_id": order_id, "raw": output}
            else:
                msg = d.get("msg1", "Unknown error")
                log.error(f"Order rejected: {msg}")
                return {"success": False, "error": msg}
        except requests.Timeout:
            log.error("Order request timed out - checking status before retry")
            return {"success": False, "error": "TIMEOUT", "check_required": True}
        except Exception as e:
            log.error(f"Order error: {e}")
            return {"success": False, "error": str(e)}

    def cancel_order(self, order_id: str, symbol: str, qty: int) -> dict:
        """Cancel an outstanding order."""
        self.ensure_token()
        is_paper = self.config.get("is_paper")
        tr_id = "VTTC0803U" if is_paper else "TTTC0803U"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-rvsecncl"
        body = {
            "CANO": self.config.get("account_no"),
            "ACNT_PRDT_CD": self.config.get("account_suffix", "01"),
            "KRX_FWDG_ORD_ORGNO": "",
            "ORGN_ODNO": order_id,
            "ORD_DVSN": "00",
            "RVSE_CNCL_DVSN_CD": "02",  # 02=cancel
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0",
            "QTY_ALL_ORD_YN": "Y",
        }
        try:
            r = requests.post(url, headers=self._headers(tr_id), json=body, timeout=10)
            r.raise_for_status()
            d = r.json()
            return {"success": d.get("rt_cd") == "0", "raw": d}
        except Exception as e:
            log.error(f"Cancel order error: {e}")
            return {"success": False, "error": str(e)}

    def get_order_status(self, order_id: str) -> dict:
        """Query single order status."""
        self.ensure_token()
        is_paper = self.config.get("is_paper")
        tr_id = "VTTC8001R" if is_paper else "TTTC8001R"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        params = {
            "CANO": self.config.get("account_no"),
            "ACNT_PRDT_CD": self.config.get("account_suffix", "01"),
            "INQR_STRT_DT": datetime.now().strftime("%Y%m%d"),
            "INQR_END_DT": datetime.now().strftime("%Y%m%d"),
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "00",
            "PDNO": "",
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": order_id,
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        try:
            r = requests.get(url, headers=self._headers(tr_id), params=params, timeout=10)
            r.raise_for_status()
            d = r.json()
            if d.get("rt_cd") == "0":
                output1 = d.get("output1", [])
                if output1:
                    item = output1[0]
                    return {
                        "order_id": order_id,
                        "filled_qty": int(item.get("tot_ccld_qty", 0)),
                        "remaining_qty": int(item.get("rmn_qty", 0)),
                        "avg_price": int(float(item.get("avg_prvs", 0))),
                        "status": item.get("ord_stts_name", ""),
                    }
        except Exception as e:
            log.error(f"Order status error: {e}")
        return {}

    def get_websocket_approval_key(self) -> str:
        """Get WebSocket approval key."""
        url = f"{self.base_url}/oauth2/Approval"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.config.get("app_key"),
            "secretkey": self.config.get("app_secret"),
        }
        try:
            r = requests.post(url, json=body, timeout=10)
            r.raise_for_status()
            return r.json().get("approval_key", "")
        except Exception as e:
            log.error(f"WS approval key error: {e}")
            return ""


# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKET MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class WebSocketManager(QObject):
    tick_received = Signal(str, int, int)       # symbol, price, volume
    order_filled = Signal(str, int, int)        # order_id, filled_qty, avg_price
    connection_changed = Signal(bool, str)       # connected, reason

    def __init__(self, api: KISApiClient, config: ConfigManager):
        super().__init__()
        self.api = api
        self.config = config
        self._ws = None
        self._approval_key = ""
        self._symbol = ""
        self._running = False
        self._thread = None
        self._reconnect_delay = 3
        self._max_reconnect = 10
        self._reconnect_count = 0
        self._last_heartbeat = time.time()
        self._heartbeat_interval = 30
        self._mutex = QMutex()

    @property
    def ws_url(self):
        return KIS_PAPER_WS if self.config.get("is_paper") else KIS_REAL_WS

    def start(self, symbol: str):
        self._symbol = symbol
        self._running = True
        self._reconnect_count = 0
        self._approval_key = self.api.get_websocket_approval_key()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

    def _run_loop(self):
        while self._running and self._reconnect_count < self._max_reconnect:
            try:
                self._connect()
                self._reconnect_count = 0  # reset on successful connect
            except Exception as e:
                log.error(f"WebSocket error: {e}")
            if self._running:
                delay = min(self._reconnect_delay * (2 ** self._reconnect_count), 60)
                self._reconnect_count += 1
                log.info(f"WebSocket reconnecting in {delay}s (attempt {self._reconnect_count})")
                self.connection_changed.emit(False, f"Reconnecting in {delay}s")
                time.sleep(delay)

        if self._reconnect_count >= self._max_reconnect:
            self.connection_changed.emit(False, "Connection Error")
            log.error("Max WebSocket reconnection attempts reached")

    def _connect(self):
        ws_url = self.ws_url
        log.info(f"Connecting WebSocket to {ws_url}")

        def on_open(ws):
            self.connection_changed.emit(True, "WebSocket Connected")
            self._subscribe(ws)

        def on_message(ws, message):
            self._last_heartbeat = time.time()
            self._process_message(message)

        def on_error(ws, error):
            log.error(f"WebSocket error: {error}")
            self.connection_changed.emit(False, f"WS Error: {error}")

        def on_close(ws, code, msg):
            log.info(f"WebSocket closed: {code} {msg}")
            if self._running:
                self.connection_changed.emit(False, "Disconnected")

        wsa = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        self._ws = wsa
        wsa.run_forever(ping_interval=self._heartbeat_interval, ping_timeout=10)

    def _subscribe(self, ws):
        """Subscribe to real-time data streams."""
        subs = [
            ("H0STCNT0", self._symbol),   # real-time tick
            ("H0STASP0", self._symbol),   # order book
        ]
        for tr_id, tr_key in subs:
            msg = json.dumps({
                "header": {
                    "approval_key": self._approval_key,
                    "custtype": "P",
                    "tr_type": "1",
                    "content-type": "utf-8",
                },
                "body": {
                    "input": {
                        "tr_id": tr_id,
                        "tr_key": tr_key,
                    }
                }
            })
            try:
                ws.send(msg)
                log.debug(f"Subscribed: {tr_id} {tr_key}")
            except Exception as e:
                log.error(f"Subscribe error: {e}")

    def _process_message(self, message: str):
        """Parse and emit WebSocket messages."""
        try:
            if message.startswith("{"):
                # JSON response (connect ack etc.)
                d = json.loads(message)
                header = d.get("header", {})
                tr_id = header.get("tr_id", "")
                body = d.get("body", {})
                rt_cd = body.get("rt_cd", "")
                if rt_cd == "1":
                    log.debug(f"WS msg {tr_id}: {body.get('msg1','')}")
                return

            # Pipe-delimited real-time data
            parts = message.split("|")
            if len(parts) < 4:
                return

            tr_id = parts[1]
            data_str = parts[3]
            fields = data_str.split("^")

            if tr_id == "H0STCNT0" and len(fields) >= 3:
                # Real-time tick: stck_shrn_iscd^stck_cntg_hour^stck_prpr^cntg_vol...
                symbol = fields[0]
                price = int(fields[2]) if fields[2] else 0
                volume = int(fields[9]) if len(fields) > 9 and fields[9] else 0
                if price > 0:
                    self.tick_received.emit(symbol, price, volume)

        except Exception as e:
            log.debug(f"WS parse error: {e} | msg: {message[:100]}")

    def resubscribe(self, new_symbol: str):
        self._symbol = new_symbol
        if self._ws and self._running:
            self._subscribe(self._ws)

    @property
    def is_connected(self) -> bool:
        return (self._ws is not None and
                self._running and
                (time.time() - self._last_heartbeat) < 60)


# ─────────────────────────────────────────────────────────────────────────────
# TICK DATA BUFFER
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TickData:
    price: int
    volume: int
    ts: float = field(default_factory=time.time)


class TickBuffer:
    """Thread-safe circular buffer for real-time tick data."""

    def __init__(self, maxlen: int = 5000):
        self._buf: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._last_price: int = 0
        self._prev_price: int = 0

    def add(self, price: int, volume: int):
        with self._lock:
            self._prev_price = self._last_price
            self._last_price = price
            self._buf.append(TickData(price, volume))

    def get_recent(self, seconds: float) -> List[TickData]:
        cutoff = time.time() - seconds
        with self._lock:
            return [t for t in self._buf if t.ts >= cutoff]

    def current_price(self) -> int:
        with self._lock:
            return self._last_price

    def prev_price(self) -> int:
        with self._lock:
            return self._prev_price

    def clear(self):
        with self._lock:
            self._buf.clear()
            self._last_price = 0
            self._prev_price = 0


# ─────────────────────────────────────────────────────────────────────────────
# 1-MINUTE CANDLE AGGREGATOR
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Candle:
    ts: datetime
    open: int
    high: int
    low: int
    close: int
    volume: int


class CandleAggregator:
    def __init__(self, period_minutes: int = 1):
        self.period = period_minutes
        self._candles: List[Candle] = []
        self._current: Optional[Candle] = None
        self._lock = threading.Lock()

    def add_tick(self, price: int, volume: int, ts: datetime = None):
        if ts is None:
            ts = datetime.now()
        minute_ts = ts.replace(second=0, microsecond=0)

        with self._lock:
            if self._current is None or self._current.ts != minute_ts:
                if self._current:
                    self._candles.append(self._current)
                    if len(self._candles) > 500:
                        self._candles = self._candles[-500:]
                self._current = Candle(minute_ts, price, price, price, price, volume)
            else:
                c = self._current
                c.high = max(c.high, price)
                c.low = min(c.low, price)
                c.close = price
                c.volume += volume

    def get_candles(self, n: int = None) -> List[Candle]:
        with self._lock:
            all_c = self._candles[:]
            if self._current:
                all_c = all_c + [self._current]
            if n:
                return all_c[-n:]
            return all_c

    def get_ma20(self) -> Optional[float]:
        candles = self.get_candles(21)
        if len(candles) < 20:
            return None
        closes = [c.close for c in candles[-20:]]
        return sum(closes) / 20

    def get_ma20_trend(self) -> int:
        """Return 1 if rising, -1 if falling, 0 if flat."""
        candles = self.get_candles(22)
        if len(candles) < 21:
            return 0
        closes = [c.close for c in candles]
        ma_now = sum(closes[-20:]) / 20
        ma_prev = sum(closes[-21:-1]) / 20
        if ma_now > ma_prev:
            return 1
        elif ma_now < ma_prev:
            return -1
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# POSITION TRACKER
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Position:
    symbol: str = ""
    qty: int = 0
    avg_price: int = 0
    buy_time: Optional[datetime] = None
    buy_reason: str = ""
    high_after_buy: int = 0

    def update_high(self, price: int):
        if price > self.high_after_buy:
            self.high_after_buy = price

    @property
    def is_open(self) -> bool:
        return self.qty > 0

    def unrealized_pnl(self, current_price: int) -> int:
        return (current_price - self.avg_price) * self.qty

    def ticks_from_buy(self, current_price: int) -> int:
        if self.avg_price == 0:
            return 0
        return price_to_ticks(current_price, self.avg_price)

    def ticks_from_high(self, current_price: int) -> int:
        if self.high_after_buy == 0:
            return 0
        return price_to_ticks(current_price, self.high_after_buy)


# ─────────────────────────────────────────────────────────────────────────────
# TRADING ENGINE (runs in separate thread)
# ─────────────────────────────────────────────────────────────────────────────

class TradingEngine(QObject):
    # Signals to update UI
    status_changed = Signal(str, str)          # signal_state, order_state
    position_updated = Signal(dict)            # position info
    pnl_updated = Signal(dict)                 # pnl info
    trade_completed = Signal(dict)             # trade record
    error_occurred = Signal(str)               # error message
    log_message = Signal(str)                  # log line for UI

    def __init__(self, api: KISApiClient, ws: WebSocketManager,
                 config: ConfigManager, db: DatabaseManager):
        super().__init__()
        self.api = api
        self.ws = ws
        self.config = config
        self.db = db

        self.tick_buf = TickBuffer()
        self.candles = CandleAggregator()
        self.position = Position()

        self._sig_state = SignalState.STOPPED
        self._ord_state = OrderState.IDLE
        self._mutex = QMutex()

        self._running = False
        self._auto_trading = False
        self._symbol = ""

        # Order tracking
        self._pending_order_id: Optional[str] = None
        self._pending_order_side: str = ""
        self._pending_order_qty: int = 0
        self._order_submit_time: Optional[float] = None
        self._cancel_in_progress = False
        self._sell_reason: SellReason = SellReason.BASIC_STOP  # always initialized

        # Session stats
        self.session_realized_pnl = 0
        self.session_trades = 0
        self.session_wins = 0
        self.session_losses = 0

        # Stagnation tracking
        self._last_price_change_time = time.time()
        self._stagnation_start: Optional[float] = None
        self._stagnation_cancelled_time: Optional[float] = None

        # Rapid rise tracking
        self._rapid_rise_start_price: int = 0
        self._rapid_rise_start_time: float = 0

        # Rebound tracking
        self._drop_start_price: int = 0
        self._drop_low: int = 0
        self._rebound_start_price: int = 0
        self._rebound_start_time: float = 0
        self._in_drop_phase = False

        # Tick at which setup started
        self._setup_start_price: int = 0
        self._setup_start_time: float = 0

        # Timer for engine loop
        self._engine_timer = QTimer()
        self._engine_timer.timeout.connect(self._engine_tick)
        self._engine_timer.setInterval(200)  # 200ms loop

    def set_symbol(self, symbol: str):
        with QMutexLocker(self._mutex):
            self._symbol = symbol
            self.tick_buf.clear()
            self.candles = CandleAggregator()

    def start_trading(self):
        with QMutexLocker(self._mutex):
            if not self._symbol:
                self.error_occurred.emit(tr("select_stock_warn"))
                return
            self._auto_trading = True
            self._running = True
            self._sig_state = SignalState.WATCHING
            self._ord_state = OrderState.IDLE
        self._engine_timer.start()
        self._emit_status()
        self.log_message.emit(f"Auto-trading started: {self._symbol}")

    def stop_trading(self, reconcile: bool = True):
        self._auto_trading = False
        self._engine_timer.stop()
        with QMutexLocker(self._mutex):
            self._sig_state = SignalState.STOPPED
            self._ord_state = OrderState.IDLE
        self._emit_status()
        if reconcile:
            self._reconcile_with_broker()
        self.log_message.emit("Auto-trading stopped")

    def emergency_stop(self, liquidate: bool = True):
        """Emergency stop - cancel all orders, optionally liquidate."""
        self._auto_trading = False
        self._engine_timer.stop()
        self.log_message.emit("⚠ Emergency stop executed")
        self.db.log_event("EMERGENCY_STOP", f"liquidate={liquidate}")

        # Cancel pending orders
        if self._pending_order_id:
            self.api.cancel_order(self._pending_order_id, self._symbol,
                                  self._pending_order_qty)

        # Liquidate if requested
        if liquidate and self.position.is_open:
            result = self.api.place_order(
                self._symbol, "SELL", self.position.qty,
                order_type="MARKET"
            )
            if result.get("success"):
                self.log_message.emit(f"Emergency liquidation order: {self.position.qty} shs")
            else:
                self.log_message.emit(f"Emergency liquidation failed: {result.get('error')}")

        with QMutexLocker(self._mutex):
            self._sig_state = SignalState.PAUSED
            self._ord_state = OrderState.PAUSED_ERROR
        self._emit_status()

    def on_tick(self, symbol: str, price: int, volume: int):
        """Called from WebSocket thread via signal."""
        if symbol != self._symbol:
            return
        self.tick_buf.add(price, volume)
        self.candles.add_tick(price, volume)
        self.db.log_tick(symbol, price, volume)

        # Update position high
        if self.position.is_open:
            self.position.update_high(price)

        # Update stagnation tracking
        prev = self.tick_buf.prev_price()
        if prev and price != prev:
            self._last_price_change_time = time.time()

    @Slot()
    def _engine_tick(self):
        """Main engine loop - called every 200ms."""
        if not self._auto_trading:
            return

        price = self.tick_buf.current_price()
        if price == 0:
            return

        now = datetime.now()

        # Check trading time
        if not self._is_trading_time(now):
            self._handle_end_time()
            return

        # Check risk limits
        if self._check_risk_limits():
            return

        # Handle based on order state
        if self._ord_state == OrderState.IDLE:
            self._handle_idle(price, now)
        elif self._ord_state in (OrderState.BUY_PENDING, OrderState.BUY_PARTIAL):
            self._handle_buy_pending(price)
        elif self._ord_state == OrderState.HOLDING:
            self._handle_holding(price, now)
        elif self._ord_state in (OrderState.SELL_PENDING, OrderState.SELL_PARTIAL):
            self._handle_sell_pending(price)
        elif self._ord_state == OrderState.CANCEL_PENDING:
            self._handle_cancel_pending()
        elif self._ord_state == OrderState.RECONCILING:
            self._handle_reconciling()

        self._emit_position(price)

    def _is_trading_time(self, now: datetime) -> bool:
        start_str = self.config.get("start_time", MARKET_OPEN)
        end_str = self.config.get("end_time", MARKET_CLOSE)
        try:
            start = datetime.strptime(start_str, "%H:%M:%S").time()
            end = datetime.strptime(end_str, "%H:%M:%S").time()
        except ValueError:
            return False

        # Block first N minutes
        block_first = self.config.get("block_buy_first_minutes", 0)
        market_open = datetime.strptime(MARKET_OPEN, "%H:%M:%S").time()
        block_until = (datetime.combine(now.date(), market_open) +
                       timedelta(minutes=block_first)).time()

        return start <= now.time() <= end and now.time() >= block_until

    def _check_risk_limits(self) -> bool:
        """Returns True if trading should pause."""
        max_loss = self.config.get("max_daily_loss", 500000)
        max_trades = self.config.get("max_trades_per_day", 50)
        session_limit = self.config.get("session_loss_limit", 300000)

        if -self.session_realized_pnl >= max_loss:
            self.log_message.emit("Max daily loss limit reached – trading stopped")
            self.stop_trading(reconcile=False)
            return True
        if self.session_trades >= max_trades:
            self.log_message.emit("Max trade count reached – trading stopped")
            self.stop_trading(reconcile=False)
            return True
        return False

    def _handle_end_time(self):
        """Handle end of trading time."""
        action = self.config.get("end_time_action", "stop_buy")
        if not self.position.is_open:
            self.stop_trading(reconcile=False)
            return
        if action == "liquidate" and self.position.is_open:
            price = self.tick_buf.current_price()
            self._execute_sell(price, SellReason.END_TIME)

    def _handle_idle(self, price: int, now: datetime):
        """Check buy conditions when not in position."""
        if self._sig_state == SignalState.REENTRY_WAITING:
            wait = self.config.get("reentry_wait_seconds", 3)
            if self._stagnation_cancelled_time:
                elapsed = time.time() - self._stagnation_cancelled_time
                if elapsed < wait:
                    return
            self._sig_state = SignalState.WATCHING

        if self._sig_state == SignalState.STAGNATION_CANCELLED:
            norm_time = self.config.get("stagnation_reentry_seconds", 60)
            if self._stagnation_cancelled_time:
                elapsed = time.time() - self._stagnation_cancelled_time
                if elapsed >= norm_time:
                    self._sig_state = SignalState.WATCHING
                    self._setup_start_price = 0
            return

        if self._sig_state == SignalState.WATCHING:
            buy_reason = self._check_buy_conditions(price)
            if buy_reason:
                self._execute_buy(price, buy_reason)

    def _check_buy_conditions(self, price: int) -> Optional[BuyReason]:
        """Check all buy conditions. Returns reason if buy signal, else None."""
        # Sideways filter first
        if self._is_sideways(price):
            return None

        # Stagnation buy cancel check
        stag_secs = self.config.get("stagnation_buy_seconds", 2)
        elapsed_no_move = time.time() - self._last_price_change_time
        if elapsed_no_move >= stag_secs and self._sig_state == SignalState.SETUP_FORMING:
            self._sig_state = SignalState.STAGNATION_CANCELLED
            self._stagnation_cancelled_time = time.time()
            self.log_message.emit("Buy setup cancelled: price stagnation")
            return None

        # Condition 1: 20MA Pullback
        if self.config.get("ma20_enabled", True):
            if self._check_ma20_pullback(price):
                return BuyReason.MA20_PULLBACK

        # Condition 2: Rapid Rise
        if self.config.get("rapid_rise_enabled", True):
            if self._check_rapid_rise(price):
                return BuyReason.RAPID_RISE

        # Condition 3: Rebound after drop
        if self.config.get("rebound_enabled", True):
            if self._check_rebound(price):
                return BuyReason.REBOUND

        return None

    def _is_sideways(self, price: int) -> bool:
        """Check if price is in sideways range."""
        range_ticks = self.config.get("sideways_range_ticks", 3)
        window_secs = self.config.get("sideways_window_seconds", 30)
        recent = self.tick_buf.get_recent(window_secs)
        if len(recent) < 5:
            return False
        prices = [t.price for t in recent]
        tick_size = get_tick_size(price)
        price_range = (max(prices) - min(prices))
        range_in_ticks = price_range / tick_size if tick_size > 0 else 0
        return range_in_ticks <= range_ticks

    def _check_ma20_pullback(self, price: int) -> bool:
        """Check 20MA pullback and recovery condition."""
        ma20 = self.candles.get_ma20()
        if ma20 is None:
            return False
        ma20_trend = self.candles.get_ma20_trend()
        if ma20_trend != 1:
            return False
        if price <= ma20:
            return False

        proximity = self.config.get("ma20_proximity_ticks", 3)
        recovery = self.config.get("ma20_recovery_ticks", 2)
        tick_size = get_tick_size(price)
        proximity_price = proximity * tick_size

        # Price must be close to MA
        if price - ma20 > proximity_price * 2:
            return False

        # Check recent recovery: recent low near MA, now recovering
        recent = self.tick_buf.get_recent(30)
        if len(recent) < 5:
            return False
        prices = [t.price for t in recent]
        recent_low = min(prices)
        recovery_ticks = price_to_ticks(price, recent_low)
        near_ma = abs(recent_low - ma20) <= proximity_price

        return near_ma and recovery_ticks >= recovery

    def _check_rapid_rise(self, price: int) -> bool:
        """Check rapid rise condition."""
        ticks_needed = self.config.get("rapid_rise_ticks", 5)
        seconds = self.config.get("rapid_rise_seconds", 5)
        min_consec = self.config.get("rapid_rise_min_consecutive", 3)

        recent = self.tick_buf.get_recent(seconds)
        if len(recent) < 3:
            return False

        prices = [t.price for t in recent]

        # Check total tick movement
        start_p = prices[0]
        total_ticks = price_to_ticks(price, start_p)
        if total_ticks < ticks_needed:
            return False

        # Check consecutive upward ticks
        consec = 0
        max_consec = 0
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                consec += 1
                max_consec = max(max_consec, consec)
            elif prices[i] < prices[i-1] - get_tick_size(prices[i]) * 2:
                # significant pullback - reset
                consec = 0
            # small pullback: don't reset
        if max_consec < min_consec:
            return False

        return True

    def _check_rebound(self, price: int) -> bool:
        """Check rebound after rapid drop condition."""
        drop_ticks = self.config.get("rebound_drop_ticks", 10)
        up_ticks = self.config.get("rebound_up_ticks", 4)
        seconds = self.config.get("rebound_seconds", 5)

        recent = self.tick_buf.get_recent(30)
        if len(recent) < 5:
            return False

        prices = [t.price for t in recent]
        high = max(prices[:-1])
        low = min(prices)
        low_idx = prices.index(low)
        current = prices[-1]

        # Was there a significant drop?
        drop = price_to_ticks(low, high)
        if drop > -drop_ticks:
            return False

        # Is price now rebounding?
        rebound = price_to_ticks(current, low)
        if rebound < up_ticks:
            return False

        # Ensure rebound is recent
        if low_idx < len(recent) * 0.5:
            return False

        return True

    def _execute_buy(self, price: int, reason: BuyReason):
        """Submit buy order."""
        if self._ord_state != OrderState.IDLE:
            log.warning("Buy attempt while order pending - skipped")
            return

        qty = self.config.get("order_qty", 10)
        order_type = self.config.get("order_type", "MARKET")

        if order_type == "LIMIT":
            offset = self.config.get("limit_offset_ticks", 0)
            tick_size = get_tick_size(price)
            limit_price = price + offset * tick_size
        else:
            limit_price = price

        self._ord_state = OrderState.BUY_PENDING
        self._sig_state = SignalState.SETUP_FORMING
        self._emit_status()

        result = self.api.place_order(self._symbol, "BUY", qty, limit_price, order_type)

        if result.get("check_required"):
            # Timeout - must verify
            self._ord_state = OrderState.RECONCILING
            self._emit_status()
            self.log_message.emit("Buy order timeout – checking order status")
            return

        if result.get("success"):
            self._pending_order_id = result.get("order_id")
            self._pending_order_side = "BUY"
            self._pending_order_qty = qty
            self._order_submit_time = time.time()
            self.log_message.emit(f"Buy order: {qty} shs @ {price:,} KRW ({reason.value})")
            self.db.save_order(self._symbol, "BUY", self._pending_order_id,
                               qty, 0, limit_price, "PENDING", reason.value)
        else:
            self._ord_state = OrderState.IDLE
            self._sig_state = SignalState.WATCHING
            self.log_message.emit(f"Buy order failed: {result.get('error')}")
            self._emit_status()

    def _handle_buy_pending(self, price: int):
        """Poll buy order status."""
        if not self._pending_order_id:
            return

        timeout = self.config.get("limit_timeout_seconds", 10)
        elapsed = time.time() - (self._order_submit_time or time.time())

        status = self.api.get_order_status(self._pending_order_id)
        if not status:
            return

        filled = status.get("filled_qty", 0)
        remaining = status.get("remaining_qty", 0)
        avg_price = status.get("avg_price", 0)

        if remaining == 0 and filled > 0:
            # Fully filled
            self.position.symbol = self._symbol
            self.position.qty = filled
            self.position.avg_price = avg_price or price
            self.position.buy_time = datetime.now()
            self.position.buy_reason = ""
            self.position.high_after_buy = self.position.avg_price
            self._ord_state = OrderState.HOLDING
            self._sig_state = SignalState.WATCHING
            self.log_message.emit(
                f"Buy filled: {filled} shs @ avg {avg_price:,} KRW")
            self._pending_order_id = None
            self._emit_status()

        elif filled > 0 and remaining > 0:
            self._ord_state = OrderState.BUY_PARTIAL

        elif elapsed >= timeout and remaining > 0:
            # Cancel unfilled
            self._cancel_pending_order()

    def _cancel_pending_order(self):
        """Cancel current pending order."""
        if not self._pending_order_id or self._cancel_in_progress:
            return
        self._cancel_in_progress = True
        self._ord_state = OrderState.CANCEL_PENDING
        self._emit_status()
        result = self.api.cancel_order(
            self._pending_order_id, self._symbol, self._pending_order_qty)
        self.log_message.emit(
            f"Order cancel {'OK' if result.get('success') else 'FAILED'}: "
            f"{self._pending_order_id}")

    def _handle_cancel_pending(self):
        """Wait for cancellation confirmation."""
        if not self._pending_order_id:
            return
        status = self.api.get_order_status(self._pending_order_id)
        if not status:
            return

        filled = status.get("filled_qty", 0)
        remaining = status.get("remaining_qty", 0)

        if remaining == 0:
            # Cancellation confirmed
            self._cancel_in_progress = False
            if filled > 0:
                # Partial fill during cancel
                self.position.qty = filled
                self.position.avg_price = status.get("avg_price", 0)
                self.position.buy_time = datetime.now()
                self.position.high_after_buy = self.position.avg_price
                self._ord_state = OrderState.HOLDING
                self.log_message.emit(f"Partial fill then cancelled: {filled} shs")
            else:
                self._ord_state = OrderState.IDLE
                self._sig_state = SignalState.WATCHING
            self._pending_order_id = None
            self._emit_status()

    def _handle_holding(self, price: int, now: datetime):
        """Monitor sell conditions while holding position."""
        if not self.position.is_open:
            self._ord_state = OrderState.FLAT
            self._sig_state = SignalState.REENTRY_WAITING
            self._emit_status()
            return

        sell_reason = self._check_sell_conditions(price)
        if sell_reason:
            self._execute_sell(price, sell_reason)

    def _check_sell_conditions(self, price: int) -> Optional[SellReason]:
        """Check all sell conditions."""
        ticks_from_buy = self.position.ticks_from_buy(price)
        ticks_from_high = self.position.ticks_from_high(price)

        # Basic sell (stop loss)
        if self.config.get("basic_sell_enabled", True):
            basic_ticks = self.config.get("basic_sell_ticks", -2)
            if ticks_from_buy <= basic_ticks:
                return SellReason.BASIC_STOP

        # Trailing TP
        high_ticks = self.position.ticks_from_buy(self.position.high_after_buy)
        ranges = self.config.get("trailing_ranges", [])
        for r in ranges:
            if r["min_ticks"] <= high_ticks <= r["max_ticks"]:
                if ticks_from_high <= -r["pullback_ticks"]:
                    return SellReason.TRAILING_TP

        # Stagnation sell
        if self.config.get("stagnation_sell_enabled", True):
            stag_secs = self.config.get("stagnation_sell_seconds", 2)
            elapsed_no_move = time.time() - self._last_price_change_time
            if elapsed_no_move >= stag_secs and ticks_from_buy > 0:
                return SellReason.STAGNATION

        return None

    def _execute_sell(self, price: int, reason: SellReason):
        """Submit sell order."""
        if self._ord_state != OrderState.HOLDING:
            return
        if not self.position.is_open:
            return

        qty = self.position.qty
        order_type = self.config.get("order_type", "MARKET")

        if order_type == "LIMIT":
            offset = self.config.get("limit_offset_ticks", 0)
            tick_size = get_tick_size(price)
            limit_price = price - offset * tick_size
        else:
            limit_price = price

        self._ord_state = OrderState.SELL_PENDING
        self._emit_status()

        result = self.api.place_order(self._symbol, "SELL", qty, limit_price, order_type)

        if result.get("check_required"):
            self._ord_state = OrderState.RECONCILING
            self._emit_status()
            return

        if result.get("success"):
            self._pending_order_id = result.get("order_id")
            self._pending_order_side = "SELL"
            self._pending_order_qty = qty
            self._order_submit_time = time.time()
            self.log_message.emit(f"Sell order: {qty} shs @ {price:,} KRW ({reason.value})")
            self.db.save_order(self._symbol, "SELL", self._pending_order_id,
                               qty, 0, limit_price, "PENDING", reason.value)
            # Store sell reason for trade record
            self._sell_reason = reason
        else:
            self._ord_state = OrderState.HOLDING
            self.log_message.emit(f"Sell order failed: {result.get('error')}")
            self._emit_status()

    def _handle_sell_pending(self, price: int):
        """Poll sell order status."""
        if not self._pending_order_id:
            return

        timeout = self.config.get("limit_timeout_seconds", 10)
        elapsed = time.time() - (self._order_submit_time or time.time())

        status = self.api.get_order_status(self._pending_order_id)
        if not status:
            return

        filled = status.get("filled_qty", 0)
        remaining = status.get("remaining_qty", 0)
        avg_price = status.get("avg_price", 0)

        if remaining == 0 and filled > 0:
            # Fully sold
            sell_price = avg_price or price
            pnl = (sell_price - self.position.avg_price) * filled

            self.db.save_trade(
                self._symbol,
                self.position.buy_time.isoformat() if self.position.buy_time else "",
                datetime.now().isoformat(),
                self.position.avg_price, sell_price, filled,
                self.position.buy_reason,
                self._sell_reason.value,
                self.position.high_after_buy, pnl
            )

            self.session_realized_pnl += pnl
            self.session_trades += 1
            if pnl > 0:
                self.session_wins += 1
            else:
                self.session_losses += 1

            trade_info = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": "Sell",
                "price": sell_price,
                "qty": filled,
                "reason": self._sell_reason.value,
                "high": self.position.high_after_buy,
                "pnl": pnl,
                "ticks": price_to_ticks(sell_price, self.position.avg_price),
            }

            self.log_message.emit(
                f"Sell filled: {filled} shs @ {sell_price:,} KRW | P&L: {pnl:+,} KRW")
            self.trade_completed.emit(trade_info)

            # Reset position
            self.position = Position()
            self._pending_order_id = None
            self._ord_state = OrderState.FLAT
            self._sig_state = SignalState.REENTRY_WAITING
            self._stagnation_cancelled_time = time.time()
            self._emit_status()

            # Emit updated PnL
            self._emit_pnl()

        elif filled > 0 and remaining > 0:
            self._ord_state = OrderState.SELL_PARTIAL
            # Broker returns cumulative filled; set remaining qty directly
            # to avoid double-subtraction across repeated poll cycles
            self.position.qty = remaining

        elif elapsed >= timeout and remaining > 0:
            self._cancel_pending_order()

    def _handle_reconciling(self):
        """Reconcile state with broker after timeout/restart."""
        self.log_message.emit("Querying broker account status...")
        balance = self.api.get_account_balance()
        holdings = balance.get("holdings", {})

        if self._symbol in holdings:
            h = holdings[self._symbol]
            self.position.symbol = self._symbol
            self.position.qty = h["qty"]
            self.position.avg_price = h["avg_price"]
            if self.position.high_after_buy == 0:
                self.position.high_after_buy = h["current_price"]
            self._ord_state = OrderState.HOLDING
        else:
            self.position = Position()
            self._ord_state = OrderState.IDLE
            self._sig_state = SignalState.WATCHING

        self._pending_order_id = None
        self._cancel_in_progress = False
        self.log_message.emit("Account status confirmed")
        self._emit_status()

    def _reconcile_with_broker(self):
        """Full reconciliation on stop/restart."""
        balance = self.api.get_account_balance()
        holdings = balance.get("holdings", {})
        if self._symbol and self._symbol in holdings:
            h = holdings[self._symbol]
            self.position.qty = h["qty"]
            self.position.avg_price = h["avg_price"]
        outstanding = self.api.get_outstanding_orders()
        self.db.log_event("RECONCILE",
                          f"holdings={len(holdings)}, outstanding={len(outstanding)}")
        self._emit_status()

    def _emit_status(self):
        self.status_changed.emit(self._sig_state.value, self._ord_state.value)

    def _emit_position(self, price: int):
        if self.position.is_open:
            pnl = self.position.unrealized_pnl(price)
            ticks = self.position.ticks_from_buy(price)
            trigger = self._get_current_sell_trigger(price)
            self.position_updated.emit({
                "qty": self.position.qty,
                "avg_price": self.position.avg_price,
                "current_price": price,
                "high_after_buy": self.position.high_after_buy,
                "unrealized_pnl": pnl,
                "ticks": ticks,
                "sell_trigger": trigger,
            })
        else:
            self.position_updated.emit({
                "qty": 0,
                "avg_price": 0,
                "current_price": price,
                "high_after_buy": 0,
                "unrealized_pnl": 0,
                "ticks": 0,
                "sell_trigger": "--",
            })
        self._emit_pnl()

    def _emit_pnl(self):
        win_rate = (self.session_wins / max(self.session_trades, 1)) * 100
        self.pnl_updated.emit({
            "unrealized": self.position.unrealized_pnl(
                self.tick_buf.current_price()) if self.position.is_open else 0,
            "realized": self.session_realized_pnl,
            "total": self.session_realized_pnl + (
                self.position.unrealized_pnl(self.tick_buf.current_price())
                if self.position.is_open else 0),
            "trades": self.session_trades,
            "wins": self.session_wins,
            "losses": self.session_losses,
            "win_rate": win_rate,
        })

    def _get_current_sell_trigger(self, price: int) -> str:
        if not self.position.is_open:
            return "--"
        basic_ticks = self.config.get("basic_sell_ticks", -2)
        trigger = ticks_to_price(self.position.avg_price, basic_ticks)
        return f"{trigger:,}"


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS DIALOG
# ─────────────────────────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(tr("settings_title"))
        self.setMinimumWidth(500)
        self.setStyleSheet(DARK_STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._api_tab(), tr("tab_api"))
        tabs.addTab(self._buy_tab(), tr("tab_buy"))
        tabs.addTab(self._sell_tab(), tr("tab_sell"))
        tabs.addTab(self._risk_tab(), tr("tab_risk"))
        tabs.addTab(self._time_tab(), tr("tab_time"))

        layout.addWidget(tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _make_form(self, fields: list) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._widgets = getattr(self, "_widgets", {})
        for key, label, widget in fields:
            form.addRow(label, widget)
            self._widgets[key] = widget
        return w

    def _api_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self._widgets = {}

        self._paper_check = QCheckBox(tr("paper_check"))
        self._paper_check.setChecked(self.config.get("is_paper", True))
        layout.addRow(tr("env_lbl"), self._paper_check)

        self._app_key = QLineEdit(self.config.get("app_key", ""))
        layout.addRow("App Key:", self._app_key)

        self._app_secret = QLineEdit(self.config.get("app_secret", ""))
        self._app_secret.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("App Secret:", self._app_secret)

        self._account = QLineEdit(self.config.get("account_no", ""))
        layout.addRow(tr("account_no"), self._account)

        self._suffix = QLineEdit(self.config.get("account_suffix", "01"))
        layout.addRow(tr("account_sfx"), self._suffix)

        return w

    def _buy_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        g1 = QGroupBox(tr("buy_cond1"))
        f1 = QFormLayout(g1)
        self._ma20_en = QCheckBox()
        self._ma20_en.setChecked(self.config.get("ma20_enabled", True))
        self._ma20_prox = QSpinBox(); self._ma20_prox.setRange(1, 20)
        self._ma20_prox.setValue(self.config.get("ma20_proximity_ticks", 3))
        self._ma20_rec = QSpinBox(); self._ma20_rec.setRange(1, 20)
        self._ma20_rec.setValue(self.config.get("ma20_recovery_ticks", 2))
        f1.addRow(tr("enable"), self._ma20_en)
        f1.addRow(tr("proximity_ticks"), self._ma20_prox)
        f1.addRow(tr("recovery_ticks"), self._ma20_rec)
        layout.addWidget(g1)

        g2 = QGroupBox(tr("buy_cond2"))
        f2 = QFormLayout(g2)
        self._rr_en = QCheckBox()
        self._rr_en.setChecked(self.config.get("rapid_rise_enabled", True))
        self._rr_ticks = QSpinBox(); self._rr_ticks.setRange(1, 50)
        self._rr_ticks.setValue(self.config.get("rapid_rise_ticks", 5))
        self._rr_secs = QSpinBox(); self._rr_secs.setRange(1, 60)
        self._rr_secs.setValue(self.config.get("rapid_rise_seconds", 5))
        f2.addRow(tr("enable"), self._rr_en)
        f2.addRow(tr("rise_ticks"), self._rr_ticks)
        f2.addRow(tr("seconds"), self._rr_secs)
        layout.addWidget(g2)

        g3 = QGroupBox(tr("buy_cond3"))
        f3 = QFormLayout(g3)
        self._reb_en = QCheckBox()
        self._reb_en.setChecked(self.config.get("rebound_enabled", True))
        self._reb_drop = QSpinBox(); self._reb_drop.setRange(1, 50)
        self._reb_drop.setValue(self.config.get("rebound_drop_ticks", 10))
        self._reb_up = QSpinBox(); self._reb_up.setRange(1, 20)
        self._reb_up.setValue(self.config.get("rebound_up_ticks", 4))
        self._reb_secs = QSpinBox(); self._reb_secs.setRange(1, 30)
        self._reb_secs.setValue(self.config.get("rebound_seconds", 5))
        f3.addRow(tr("enable"), self._reb_en)
        f3.addRow(tr("drop_ticks"), self._reb_drop)
        f3.addRow(tr("rebound_ticks"), self._reb_up)
        f3.addRow(tr("seconds"), self._reb_secs)
        layout.addWidget(g3)

        layout.addStretch()
        return w

    def _sell_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        g1 = QGroupBox(tr("basic_stop_box"))
        f1 = QFormLayout(g1)
        self._bs_en = QCheckBox()
        self._bs_en.setChecked(self.config.get("basic_sell_enabled", True))
        self._bs_ticks = QSpinBox(); self._bs_ticks.setRange(-50, 0)
        self._bs_ticks.setValue(self.config.get("basic_sell_ticks", -2))
        f1.addRow(tr("enable"), self._bs_en)
        f1.addRow(tr("stop_ticks"), self._bs_ticks)
        layout.addWidget(g1)

        g2 = QGroupBox(tr("stag_sell_box"))
        f2 = QFormLayout(g2)
        self._ss_en = QCheckBox()
        self._ss_en.setChecked(self.config.get("stagnation_sell_enabled", True))
        self._ss_secs = QSpinBox(); self._ss_secs.setRange(1, 30)
        self._ss_secs.setValue(self.config.get("stagnation_sell_seconds", 2))
        f2.addRow(tr("enable"), self._ss_en)
        f2.addRow(tr("stag_secs"), self._ss_secs)
        layout.addWidget(g2)

        layout.addStretch()
        return w

    def _risk_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        self._max_loss = QSpinBox()
        self._max_loss.setRange(0, 10000000)
        self._max_loss.setValue(self.config.get("max_daily_loss", 500000))
        self._max_loss.setSingleStep(10000)
        f.addRow(tr("max_daily_loss"), self._max_loss)

        self._max_trades = QSpinBox()
        self._max_trades.setRange(1, 1000)
        self._max_trades.setValue(self.config.get("max_trades_per_day", 50))
        f.addRow(tr("max_trades"), self._max_trades)

        self._order_qty = QSpinBox()
        self._order_qty.setRange(1, 10000)
        self._order_qty.setValue(self.config.get("order_qty", 10))
        f.addRow(tr("order_qty_form"), self._order_qty)

        self._reentry_wait = QSpinBox()
        self._reentry_wait.setRange(0, 3600)
        self._reentry_wait.setValue(self.config.get("reentry_wait_seconds", 3))
        f.addRow(tr("reentry_wait"), self._reentry_wait)

        return w

    def _time_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)

        self._start_time = QLineEdit(self.config.get("start_time", "09:00:00"))
        f.addRow(tr("trade_start"), self._start_time)

        self._end_time = QLineEdit(self.config.get("end_time", "15:30:00"))
        f.addRow(tr("trade_end"), self._end_time)

        self._block_first = QSpinBox()
        self._block_first.setRange(0, 60)
        self._block_first.setValue(self.config.get("block_buy_first_minutes", 0))
        f.addRow(tr("block_first"), self._block_first)

        self._stag_buy_secs = QSpinBox()
        self._stag_buy_secs.setRange(1, 30)
        self._stag_buy_secs.setValue(self.config.get("stagnation_buy_seconds", 2))
        f.addRow(tr("stag_buy_cancel"), self._stag_buy_secs)

        self._stag_reentry = QSpinBox()
        self._stag_reentry.setRange(5, 300)
        self._stag_reentry.setValue(self.config.get("stagnation_reentry_seconds", 60))
        f.addRow(tr("stag_reentry"), self._stag_reentry)

        return w

    def _save(self):
        # API
        self.config.set("is_paper", self._paper_check.isChecked())
        self.config.set("app_key", self._app_key.text().strip())
        self.config.set("app_secret", self._app_secret.text().strip())
        self.config.set("account_no", self._account.text().strip())
        self.config.set("account_suffix", self._suffix.text().strip())
        # Buy
        self.config.set("ma20_enabled", self._ma20_en.isChecked())
        self.config.set("ma20_proximity_ticks", self._ma20_prox.value())
        self.config.set("ma20_recovery_ticks", self._ma20_rec.value())
        self.config.set("rapid_rise_enabled", self._rr_en.isChecked())
        self.config.set("rapid_rise_ticks", self._rr_ticks.value())
        self.config.set("rapid_rise_seconds", self._rr_secs.value())
        self.config.set("rebound_enabled", self._reb_en.isChecked())
        self.config.set("rebound_drop_ticks", self._reb_drop.value())
        self.config.set("rebound_up_ticks", self._reb_up.value())
        self.config.set("rebound_seconds", self._reb_secs.value())
        # Sell
        self.config.set("basic_sell_enabled", self._bs_en.isChecked())
        self.config.set("basic_sell_ticks", self._bs_ticks.value())
        self.config.set("stagnation_sell_enabled", self._ss_en.isChecked())
        self.config.set("stagnation_sell_seconds", self._ss_secs.value())
        # Risk
        self.config.set("max_daily_loss", self._max_loss.value())
        self.config.set("max_trades_per_day", self._max_trades.value())
        self.config.set("order_qty", self._order_qty.value())
        self.config.set("reentry_wait_seconds", self._reentry_wait.value())
        # Time
        self.config.set("start_time", self._start_time.text().strip())
        self.config.set("end_time", self._end_time.text().strip())
        self.config.set("block_buy_first_minutes", self._block_first.value())
        self.config.set("stagnation_buy_seconds", self._stag_buy_secs.value())
        self.config.set("stagnation_reentry_seconds", self._stag_reentry.value())

        self.config.save()
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# CHART WIDGET (Candlestick + MA20)
# ─────────────────────────────────────────────────────────────────────────────

class CandleChartWidget(QChartView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart = QChart()
        self._chart.setBackgroundBrush(QBrush(QColor("#1a1a2e")))
        self._chart.setTheme(QChart.ChartTheme.ChartThemeDark)
        self._chart.legend().hide()
        from PySide6.QtCore import QMargins
        self._chart.setMargins(QMargins(0, 0, 0, 0))

        self._candle_series = QCandlestickSeries()
        self._candle_series.setIncreasingColor(QColor("#e74c3c"))
        self._candle_series.setDecreasingColor(QColor("#3498db"))
        self._candle_series.setBodyWidth(0.8)

        self._ma_series = QLineSeries()
        pen = QPen(QColor("#f0c040"))
        pen.setWidth(2)
        self._ma_series.setPen(pen)

        self._buy_series = QLineSeries()
        buy_pen = QPen(QColor("#e74c3c"))
        buy_pen.setWidth(0)
        self._buy_series.setPen(buy_pen)

        self._chart.addSeries(self._candle_series)
        self._chart.addSeries(self._ma_series)

        # Axes created on first data update to avoid mismatched-axis crash
        self._axes_created = False
        self.setChart(self._chart)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setStyleSheet("background: #1a1a2e; border: none;")

        # Buy/sell markers stored as annotations
        self._markers: List[dict] = []

    def update_candles(self, candles: List[Candle], ma20_values: List[float]):
        """Update chart with latest candle data."""
        self._candle_series.clear()
        self._ma_series.clear()

        for c in candles[-60:]:  # show last 60 candles
            ts_ms = int(c.ts.timestamp() * 1000)
            cs = QCandlestickSet(c.open, c.high, c.low, c.close, ts_ms)
            self._candle_series.append(cs)

        # MA line
        for c, ma in zip(candles[-60:], ma20_values[-60:]):
            if ma > 0:
                ts_ms = int(c.ts.timestamp() * 1000)
                self._ma_series.append(ts_ms, ma)

        # Create axes once after series have data
        if not self._axes_created and self._candle_series.count() > 0:
            self._chart.createDefaultAxes()
            self._axes_created = True

    def add_trade_marker(self, price: int, is_buy: bool, ts: datetime):
        self._markers.append({"price": price, "is_buy": is_buy, "ts": ts})
        # Trigger repaint
        self.viewport().update()


# ─────────────────────────────────────────────────────────────────────────────
# TICK TAPE WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class TickTapeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ticks: deque = deque(maxlen=50)
        self._prev_price = 0
        self.setMinimumHeight(80)
        self.setStyleSheet("background: #0d0d1a; border: 1px solid #2a2a4a;")

    def add_tick(self, price: int, volume: int):
        direction = 0
        if self._prev_price:
            direction = 1 if price > self._prev_price else (-1 if price < self._prev_price else 0)
        self._ticks.append((price, volume, direction, time.time()))
        self._prev_price = price
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0d0d1a"))

        if not self._ticks:
            return

        x = self.width() - 10
        for price, vol, direction, ts in reversed(self._ticks):
            if direction > 0:
                color = QColor("#e74c3c")
                arrow = "▲"
            elif direction < 0:
                color = QColor("#3498db")
                arrow = "▼"
            else:
                color = QColor("#888888")
                arrow = "─"

            painter.setPen(QPen(color))
            painter.setFont(QFont("Consolas", 9))
            text = f"{arrow} {price:,}"
            fm = painter.fontMetrics()
            w = fm.horizontalAdvance(text)
            x -= w + 8
            if x < 0:
                break
            painter.drawText(x, self.height() // 2 + 5, text)

        painter.end()


# ─────────────────────────────────────────────────────────────────────────────
# DARK THEME STYLESHEET
# ─────────────────────────────────────────────────────────────────────────────

DARK_STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #0d0d1a;
    color: #e0e0e0;
    font-family: 'Malgun Gothic', 'Consolas', sans-serif;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    margin-top: 8px;
    padding: 8px;
    color: #a0a0c0;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    color: #7878aa;
}
QLabel { color: #c0c0d8; }
QLabel#price_label { color: #ff6060; font-size: 24px; font-weight: bold; }
QLabel#pnl_positive { color: #ff4444; font-size: 14px; font-weight: bold; }
QLabel#pnl_negative { color: #4488ff; font-size: 14px; font-weight: bold; }
QLabel#status_label { color: #ffdd00; font-size: 13px; font-weight: bold; }
QPushButton {
    background-color: #1e1e3a;
    border: 1px solid #3a3a6a;
    border-radius: 4px;
    padding: 6px 14px;
    color: #d0d0f0;
}
QPushButton:hover { background-color: #2a2a5a; }
QPushButton:pressed { background-color: #151530; }
QPushButton#btn_start {
    background-color: #1a5c1a;
    border: 1px solid #2a8c2a;
    color: white;
    font-weight: bold;
    font-size: 13px;
}
QPushButton#btn_start:hover { background-color: #227722; }
QPushButton#btn_stop {
    background-color: #5c1a1a;
    border: 1px solid #8c2a2a;
    color: white;
    font-weight: bold;
    font-size: 13px;
}
QPushButton#btn_stop:hover { background-color: #772222; }
QPushButton#btn_emergency {
    background-color: #8b0000;
    border: 2px solid #ff0000;
    color: white;
    font-weight: bold;
    font-size: 14px;
    border-radius: 6px;
    padding: 10px;
}
QPushButton#btn_emergency:hover { background-color: #cc0000; }
QPushButton#btn_market_active {
    background-color: #1a3a8c;
    border: 2px solid #3a5acc;
    color: white;
    font-weight: bold;
}
QPushButton#btn_limit_active {
    background-color: #1a3a8c;
    border: 2px solid #3a5acc;
    color: white;
    font-weight: bold;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1a1a2e;
    border: 1px solid #3a3a5a;
    border-radius: 3px;
    padding: 4px;
    color: #d0d0f0;
}
QTableWidget {
    background-color: #0d0d1a;
    alternate-background-color: #151530;
    border: 1px solid #2a2a4a;
    gridline-color: #1e1e3a;
    color: #c0c0d8;
}
QTableWidget::item:selected { background-color: #2a2a5a; }
QHeaderView::section {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    padding: 4px;
    color: #8888aa;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #2a2a4a;
    background-color: #0d0d1a;
}
QTabBar::tab {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    padding: 6px 14px;
    color: #8888aa;
}
QTabBar::tab:selected {
    background-color: #1e1e4a;
    color: #d0d0f0;
}
QScrollBar:vertical {
    background: #1a1a2e;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #3a3a6a;
    border-radius: 4px;
}
QStatusBar {
    background-color: #0a0a18;
    color: #8888aa;
    border-top: 1px solid #2a2a4a;
}
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #5a5a8a;
    background: #1a1a2e;
}
QCheckBox::indicator:checked {
    background: #3a6acc;
}
QTextEdit {
    background-color: #080810;
    color: #88cc88;
    font-family: Consolas, monospace;
    font-size: 11px;
    border: 1px solid #1a1a3a;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.api = KISApiClient(self.config)
        self.ws = WebSocketManager(self.api, self.config)
        self.engine = TradingEngine(self.api, self.ws, self.config, self.db)

        self._is_live = not self.config.get("is_paper", True)
        self._ws_connected = False
        self._api_connected = False
        self._trading_active = False

        self._current_symbol = ""
        self._current_stock_name = ""
        self._current_price = 0

        # MA20 history for chart
        self._ma20_history: List[float] = []

        self.setWindowTitle(f"{APP_TITLE}  {'🔴 LIVE' if self._is_live else '📄 PAPER'}")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(DARK_STYLE)

        self._build_ui()
        self._connect_signals()

        # Chart update timer (separate from engine)
        self._chart_timer = QTimer()
        self._chart_timer.timeout.connect(self._update_chart)
        self._chart_timer.start(2000)  # every 2s

        # Clock timer
        self._clock_timer = QTimer()
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        # Connection status timer
        self._conn_timer = QTimer()
        self._conn_timer.timeout.connect(self._check_connection)
        self._conn_timer.start(5000)

        self._update_clock()
        self._log(tr("log_init"))

    # ── UI BUILD ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Left: chart area
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(4)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(self._build_top_bar())
        left_layout.addWidget(self._build_chart_area(), stretch=3)
        left_layout.addWidget(self._build_tick_area())
        left_layout.addWidget(self._build_trade_history(), stretch=1)
        left_layout.addWidget(self._build_status_bar_widget())

        # Right: control panel
        right = self._build_right_panel()
        right.setFixedWidth(330)

        root.addWidget(left, stretch=1)
        root.addWidget(right)

        # System status bar
        self.statusBar().setStyleSheet(
            "QStatusBar { background: #0a0a18; color: #666688; }")
        self._status_conn = QLabel(tr("not_connected"))
        self._status_conn.setStyleSheet("color: #cc4444;")
        self._status_ws = QLabel(tr("ws_disconnected"))
        self._status_ws.setStyleSheet("color: #cc4444;")
        self._status_order = QLabel(tr("order_status_ok"))
        self._status_time = QLabel("")
        self.statusBar().addWidget(self._status_conn)
        self.statusBar().addWidget(QLabel("  "))
        self.statusBar().addWidget(self._status_ws)
        self.statusBar().addWidget(QLabel("  "))
        self.statusBar().addWidget(self._status_order)
        self.statusBar().addPermanentWidget(self._status_time)

    def _build_top_bar(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(58)
        w.setStyleSheet("background: #0a0a18; border-bottom: 1px solid #2a2a4a;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # ── Symbol search ──────────────────────────────────────────────────
        layout.addWidget(QLabel(tr("symbol_code")))
        self._sym_input = QLineEdit()
        self._sym_input.setFixedWidth(80)
        self._sym_input.setPlaceholderText("005930")
        self._sym_input.returnPressed.connect(self._search_stock)
        layout.addWidget(self._sym_input)
        btn_search = QPushButton("🔍")
        btn_search.setFixedSize(30, 30)
        btn_search.clicked.connect(self._search_stock)
        layout.addWidget(btn_search)

        self._stock_name_lbl = QLabel(tr("stock_name"))
        self._stock_name_lbl.setStyleSheet(
            "color:#a0a0cc; font-size:13px; font-weight:bold;")
        self._stock_name_lbl.setMinimumWidth(80)
        layout.addWidget(self._stock_name_lbl)

        # ── Price ──────────────────────────────────────────────────────────
        layout.addSpacing(8)
        lbl = QLabel(tr("current_price"))
        lbl.setStyleSheet("color:#888888; font-size:11px;")
        layout.addWidget(lbl)

        self._price_lbl = QLabel("--")
        self._price_lbl.setObjectName("price_label")
        self._price_lbl.setMinimumWidth(70)
        layout.addWidget(self._price_lbl)

        self._price_change_lbl = QLabel("")
        self._price_change_lbl.setStyleSheet("color:#e74c3c; font-size:12px;")
        self._price_change_lbl.setMinimumWidth(90)
        layout.addWidget(self._price_change_lbl)

        # ── Volume ─────────────────────────────────────────────────────────
        self._vol_lbl = QLabel(tr("volume_lbl"))
        self._vol_lbl.setStyleSheet("color:#888888; font-size:11px;")
        layout.addWidget(self._vol_lbl)

        layout.addStretch()

        # ── Time settings ──────────────────────────────────────────────────
        layout.addWidget(QLabel(tr("start_lbl")))
        self._start_time_edit = QLineEdit(self.config.get("start_time", "09:00:00"))
        self._start_time_edit.setFixedWidth(68)
        layout.addWidget(self._start_time_edit)
        layout.addWidget(QLabel(tr("end_lbl")))
        self._end_time_edit = QLineEdit(self.config.get("end_time", "15:30:00"))
        self._end_time_edit.setFixedWidth(68)
        layout.addWidget(self._end_time_edit)

        layout.addSpacing(8)

        # ── START / STOP / LANG ────────────────────────────────────────────
        self.btn_start = QPushButton(tr("btn_start"))
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFixedSize(88, 46)
        self.btn_start.clicked.connect(self._start_trading)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton(tr("btn_stop"))
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedSize(88, 46)
        self.btn_stop.clicked.connect(self._stop_trading)
        layout.addWidget(self.btn_stop)

        self.btn_lang = QPushButton("🌐 EN")
        self.btn_lang.setFixedSize(54, 46)
        self.btn_lang.setToolTip("Switch language / 언어 전환")
        self.btn_lang.setStyleSheet(
            "QPushButton{background:#1a1a2e;border:1px solid #3a3a6a;"
            "color:#a0a0d0;font-size:11px;border-radius:4px;}"
            "QPushButton:hover{background:#2a2a5a;}")
        self.btn_lang.clicked.connect(self._toggle_language)
        layout.addWidget(self.btn_lang)

        return w

    def _build_chart_area(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Chart tabs
        tab_bar = QWidget()
        tb_layout = QHBoxLayout(tab_bar)
        tb_layout.setContentsMargins(4, 2, 4, 2)
        tb_layout.setSpacing(4)
        lbl = QLabel(self._current_stock_name or tr("select_stock"))
        lbl.setStyleSheet("color: #a0a0cc; font-weight: bold;")
        self._chart_name_lbl = lbl
        tb_layout.addWidget(lbl)

        self._ma20_lbl = QLabel("SMA 20")
        self._ma20_lbl.setStyleSheet("color: #f0c040; font-size: 11px;")
        tb_layout.addWidget(self._ma20_lbl)
        tb_layout.addStretch()

        self._chart_view = CandleChartWidget()
        layout.addWidget(tab_bar)
        layout.addWidget(self._chart_view, stretch=1)

        # Volume bar placeholder
        self._vol_note = QLabel(tr("chart_note"))
        self._vol_note.setStyleSheet("color: #555566; font-size: 10px;")
        self._vol_note.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._vol_note)

        return w

    def _build_tick_area(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(60)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(4, 0, 4, 0)
        lbl = QLabel(tr("realtime_tick"))
        lbl.setStyleSheet("color: #666688; font-size: 10px;")
        lbl.setFixedWidth(48)
        layout.addWidget(lbl)
        self._tick_tape = TickTapeWidget()
        layout.addWidget(self._tick_tape)
        return w

    def _build_trade_history(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        hdr = QLabel(tr("trade_history"))
        hdr.setStyleSheet("color: #8888aa; font-size: 11px; padding: 4px 6px;")
        layout.addWidget(hdr)

        self._trade_table = QTableWidget()
        cols = [tr("col_time"), tr("col_type"), tr("col_price"), tr("col_qty"),
                tr("col_reason"), tr("col_ticks"), tr("col_high"), tr("col_pnl")]
        self._trade_table.setColumnCount(len(cols))
        self._trade_table.setHorizontalHeaderLabels(cols)
        self._trade_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._trade_table.setAlternatingRowColors(True)
        self._trade_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self._trade_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self._trade_table.verticalHeader().setVisible(False)
        self._trade_table.setMinimumHeight(100)
        # No fixed max — let the splitter/stretch allocate space naturally
        layout.addWidget(self._trade_table)

        return w

    def _build_status_bar_widget(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(32)
        w.setStyleSheet("background: #080810; border-top: 1px solid #2a2a4a;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(16)

        self._conn_dot = QLabel(tr("not_connected"))
        self._conn_dot.setStyleSheet("color: #cc4444;")
        layout.addWidget(self._conn_dot)

        self._order_status_lbl = QLabel(tr("order_status_ok"))
        self._order_status_lbl.setStyleSheet("color: #44cc44;")
        layout.addWidget(self._order_status_lbl)

        self._position_lbl = QLabel(tr("position_lbl"))
        self._position_lbl.setStyleSheet("color: #c0c0d8;")
        layout.addWidget(self._position_lbl)

        self._avg_price_lbl = QLabel(tr("avg_price_lbl"))
        self._avg_price_lbl.setStyleSheet("color: #c0c0d8;")
        layout.addWidget(self._avg_price_lbl)

        self._cur_price_lbl = QLabel(tr("cur_price_lbl"))
        self._cur_price_lbl.setStyleSheet("color: #c0c0d8;")
        layout.addWidget(self._cur_price_lbl)

        layout.addStretch()

        self._unrealized_inline = QLabel("+0 KRW")
        self._unrealized_inline.setStyleSheet("color: #ff4444; font-weight: bold;")
        layout.addWidget(self._unrealized_inline)

        return w

    def _build_right_panel(self) -> QWidget:
        # Outer container — fixed width, full height
        outer = QWidget()
        outer.setStyleSheet("background: #0a0a18; border-left: 1px solid #2a2a4a;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Scrollable inner area so content never overflows on small screens
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{border:none; background:#0a0a18;}"
            "QScrollBar:vertical{background:#1a1a2e; width:6px;}"
            "QScrollBar::handle:vertical{background:#3a3a6a; border-radius:3px;}")

        w = QWidget()
        w.setStyleSheet("background: #0a0a18;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Performance summary
        perf_box = QGroupBox("PERFORMANCE SUMMARY")
        perf_layout = QGridLayout(perf_box)
        perf_layout.setSpacing(4)

        def pnl_lbl(val="--"):
            l = QLabel(val)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold;")
            return l

        def info_hdr(text):
            l = QLabel(text)
            l.setStyleSheet("color: #888888; font-size: 10px;")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return l

        perf_layout.addWidget(info_hdr(tr("unrealized_pnl")), 0, 0)
        perf_layout.addWidget(info_hdr(tr("realized_pnl")), 0, 1)
        perf_layout.addWidget(info_hdr(tr("total_pnl")), 0, 2)
        self._unreal_lbl = pnl_lbl("+0 KRW")
        self._real_lbl = pnl_lbl("+0 KRW")
        self._total_lbl = pnl_lbl("+0 KRW")
        perf_layout.addWidget(self._unreal_lbl, 1, 0)
        perf_layout.addWidget(self._real_lbl, 1, 1)
        perf_layout.addWidget(self._total_lbl, 1, 2)

        perf_layout.addWidget(info_hdr(tr("total_trades")), 2, 0)
        perf_layout.addWidget(info_hdr(tr("win_loss")), 2, 1)
        perf_layout.addWidget(info_hdr(tr("win_rate")), 2, 2)
        self._trades_lbl = QLabel("0")
        self._trades_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._trades_lbl.setStyleSheet("color: #d0d0f0; font-size: 16px; font-weight:bold;")
        self._winloss_lbl = QLabel("0 / 0")
        self._winloss_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._winloss_lbl.setStyleSheet("color: #d0d0f0; font-size: 14px;")
        self._winrate_lbl = QLabel("0.0 %")
        self._winrate_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._winrate_lbl.setStyleSheet("color: #d0d0f0; font-size: 14px;")
        perf_layout.addWidget(self._trades_lbl, 3, 0)
        perf_layout.addWidget(self._winloss_lbl, 3, 1)
        perf_layout.addWidget(self._winrate_lbl, 3, 2)
        layout.addWidget(perf_box)

        # Current status
        status_box = QGroupBox("CURRENT STATUS")
        status_layout = QVBoxLayout(status_box)
        self._status_lbl = QLabel(tr("idle_status"))
        self._status_lbl.setObjectName("status_label")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setMinimumHeight(44)
        status_layout.addWidget(self._status_lbl)
        layout.addWidget(status_box)

        # Sell settings status
        sell_box = QGroupBox("TRADING SETTINGS STATUS")
        sell_grid = QGridLayout(sell_box)
        btn_settings = QPushButton("Settings")
        btn_settings.setFixedWidth(70)
        btn_settings.clicked.connect(self._open_settings)
        sell_grid.addWidget(btn_settings, 0, 2)

        def status_row(row, label_text):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #c0c0d8;")
            on_btn = QLabel("ON")
            on_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            on_btn.setFixedWidth(36)
            on_btn.setStyleSheet(
                "background:#1a5c1a; color:white; border-radius:3px; "
                "padding: 2px; font-weight:bold; font-size:10px;")
            cfg_lbl = QLabel("Configured")
            cfg_lbl.setStyleSheet("color: #888888; font-size:10px;")
            sell_grid.addWidget(lbl, row, 0)
            sell_grid.addWidget(on_btn, row, 1)
            sell_grid.addWidget(cfg_lbl, row, 2)
            return on_btn

        self._bs_on_lbl = status_row(1, tr("basic_stop_lbl"))
        self._ts_on_lbl = status_row(2, tr("trailing_lbl"))
        self._ss_on_lbl = status_row(3, tr("stagnation_sell_lbl"))
        layout.addWidget(sell_box)

        # Order type
        order_box = QGroupBox("ORDER TYPE")
        order_layout = QVBoxLayout(order_box)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        _active_style = ("background-color:#1a3a8c; border:2px solid #3a5acc;"
                         "color:white; font-weight:bold; border-radius:4px;")
        _inactive_style = ("background-color:#1e1e3a; border:1px solid #3a3a6a;"
                           "color:#a0a0c0; border-radius:4px;")

        self.btn_market = QPushButton("MARKET ORDER")
        self.btn_market.setCheckable(True)
        is_market = self.config.get("order_type", "MARKET") == "MARKET"
        self.btn_market.setChecked(is_market)
        self.btn_market.setStyleSheet(_active_style if is_market else _inactive_style)
        self.btn_market.clicked.connect(lambda: self._set_order_type("MARKET"))

        self.btn_limit = QPushButton("LIMIT ORDER")
        self.btn_limit.setCheckable(True)
        self.btn_limit.setChecked(not is_market)
        self.btn_limit.setStyleSheet(_inactive_style if is_market else _active_style)
        self.btn_limit.clicked.connect(lambda: self._set_order_type("LIMIT"))

        btn_row.addWidget(self.btn_market)
        btn_row.addWidget(self.btn_limit)
        order_layout.addLayout(btn_row)

        qty_row = QHBoxLayout()
        qty_row.addWidget(QLabel(tr("order_qty_lbl")))
        self.btn_qty_minus = QPushButton("−")
        self.btn_qty_minus.setFixedWidth(28)
        self.btn_qty_minus.clicked.connect(self._dec_qty)
        self._qty_lbl = QLabel(str(self.config.get("order_qty", 10)))
        self._qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qty_lbl.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self._qty_lbl.setFixedWidth(50)
        self.btn_qty_plus = QPushButton("+")
        self.btn_qty_plus.setFixedWidth(28)
        self.btn_qty_plus.clicked.connect(self._inc_qty)
        qty_row.addWidget(self.btn_qty_minus)
        qty_row.addWidget(self._qty_lbl)
        qty_row.addWidget(QLabel(tr("shares_unit")))
        qty_row.addWidget(self.btn_qty_plus)
        qty_row.addStretch()
        avail_lbl = QLabel(tr("avail_lbl"))
        avail_lbl.setStyleSheet("color: #666688;")
        self._avail_lbl = avail_lbl
        qty_row.addWidget(avail_lbl)
        order_layout.addLayout(qty_row)
        layout.addWidget(order_box)

        # Position info
        pos_box = QGroupBox(tr("pos_box"))
        pos_grid = QGridLayout(pos_box)

        def pos_row(r, lbl_text, val_text="--"):
            pos_grid.addWidget(QLabel(lbl_text), r, 0)
            lbl = QLabel(val_text)
            lbl.setStyleSheet("color: #d0d0f0; font-weight: bold;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            pos_grid.addWidget(lbl, r, 1)
            return lbl

        self._pos_qty_lbl     = pos_row(0, tr("pos_qty"),     "0")
        self._pos_avg_lbl     = pos_row(1, tr("pos_avg"),     "--")
        self._pos_high_lbl    = pos_row(2, tr("pos_high"),    "--")
        self._pos_trigger_lbl = pos_row(3, tr("pos_trigger"), "--")
        layout.addWidget(pos_box)

        # Emergency stop — constrained height, full width
        self.btn_emergency = QPushButton(tr("emergency_btn"))
        self.btn_emergency.setObjectName("btn_emergency")
        self.btn_emergency.setFixedHeight(52)
        self.btn_emergency.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_emergency.clicked.connect(self._emergency_stop)
        layout.addWidget(self.btn_emergency)

        # Log — flexible height
        log_box = QGroupBox("Log")
        log_layout = QVBoxLayout(log_box)
        log_layout.setContentsMargins(4, 4, 4, 4)
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMinimumHeight(80)
        self._log_view.setMaximumHeight(160)
        log_layout.addWidget(self._log_view)
        layout.addWidget(log_box)

        # Bottom buttons — 2×2 grid to avoid cramping
        from PySide6.QtWidgets import QGridLayout as _QGL
        btn_grid = _QGL()
        btn_grid.setSpacing(4)
        btn_settings2 = QPushButton("⚙ Settings")
        btn_settings2.clicked.connect(self._open_settings)
        btn_log = QPushButton("📋 Log")
        btn_log.clicked.connect(self._open_log)
        btn_export = QPushButton(tr("btn_export"))
        btn_export.clicked.connect(self._export_trades)
        btn_exit = QPushButton(tr("btn_exit"))
        btn_exit.clicked.connect(self.close)
        btn_grid.addWidget(btn_settings2, 0, 0)
        btn_grid.addWidget(btn_log,       0, 1)
        btn_grid.addWidget(btn_export,    1, 0)
        btn_grid.addWidget(btn_exit,      1, 1)
        layout.addLayout(btn_grid)

        layout.addStretch()

        # Wire scroll area
        scroll.setWidget(w)
        outer_layout.addWidget(scroll)
        return outer

    # ── LANGUAGE TOGGLE ───────────────────────────────────────────────────────

    def _toggle_language(self):
        global _LANG
        _LANG = "en" if _LANG == "ko" else "ko"
        self.btn_lang.setText("🌐 KO" if _LANG == "en" else "🌐 EN")
        self._apply_language()

    def _apply_language(self):
        """Refresh all translatable labels without rebuilding the whole UI."""
        # Top bar
        self._stock_name_lbl.setText(
            self._current_stock_name or tr("select_stock"))
        self._vol_lbl.setText(
            f"{'Volume' if _LANG == 'en' else '거래량'}: "
            f"{self._current_price:,}" if self._current_price else tr("volume_lbl"))
        self.btn_start.setText(tr("btn_start"))
        self.btn_stop.setText(tr("btn_stop"))
        # Status bar labels
        self._status_order.setText(tr("order_status_ok"))
        if not self._ws_connected:
            self._status_ws.setText(tr("ws_disconnected"))
            self._conn_dot.setText(tr("not_connected"))
        else:
            self._status_ws.setText(tr("ws_connected_lbl"))
            self._conn_dot.setText(tr("ws_connected_lbl"))
        if not self._api_connected:
            self._status_conn.setText(tr("not_connected"))
        else:
            self._status_conn.setText(tr("kis_connected_lbl"))
        # Bottom strip
        self._order_status_lbl.setText(tr("order_status_ok"))
        self._position_lbl.setText(tr("position_lbl"))
        self._avg_price_lbl.setText(tr("avg_price_lbl"))
        self._cur_price_lbl.setText(tr("cur_price_lbl"))
        # Chart area
        self._vol_note.setText(tr("chart_note"))
        # Trade history header
        cols = [tr("col_time"), tr("col_type"), tr("col_price"), tr("col_qty"),
                tr("col_reason"), tr("col_ticks"), tr("col_high"), tr("col_pnl")]
        for i, c in enumerate(cols):
            self._trade_table.horizontalHeaderItem(i).setText(c)
        # Right panel
        self._status_lbl.setText(
            self._status_lbl.text())  # status text is dynamic; leave as-is
        self.btn_emergency.setText(tr("emergency_btn"))
        # Pos box labels are dynamic; pos_box title
        # (GroupBox titles require finding the widget – update on next rebuild)

    # ── SIGNAL CONNECTIONS ────────────────────────────────────────────────────

    def _connect_signals(self):
        self.ws.tick_received.connect(self._on_tick)
        self.ws.connection_changed.connect(self._on_ws_connection)
        self.engine.status_changed.connect(self._on_status_changed)
        self.engine.position_updated.connect(self._on_position_updated)
        self.engine.pnl_updated.connect(self._on_pnl_updated)
        self.engine.trade_completed.connect(self._on_trade_completed)
        self.engine.error_occurred.connect(self._on_error)
        self.engine.log_message.connect(self._log)

    # ── SLOTS ─────────────────────────────────────────────────────────────────

    @Slot(str, int, int)
    @Slot(str, int, int)
    def _on_tick(self, symbol: str, price: int, volume: int):
        prev_price = self._current_price          # capture BEFORE updating
        self._current_price = price
        self._tick_tape.add_tick(price, volume)
        self.engine.on_tick(symbol, price, volume)

        color = "#e74c3c" if price >= (prev_price or price) else "#3498db"
        self._price_lbl.setText(f"{price:,}")
        self._price_lbl.setStyleSheet(
            f"color: {color}; font-size: 24px; font-weight: bold;")
        self._cur_price_lbl.setText(tr("cur_price_fmt", p=price))

    @Slot(bool, str)
    def _on_ws_connection(self, connected: bool, reason: str):
        self._ws_connected = connected
        if connected:
            self._status_ws.setText(tr("ws_connected_lbl"))
            self._status_ws.setStyleSheet("color: #44cc44;")
            self._conn_dot.setText(tr("ws_connected_lbl"))
            self._conn_dot.setStyleSheet("color: #44cc44;")
        else:
            self._status_ws.setText(f"● WS: {reason}")
            self._status_ws.setStyleSheet("color: #cc4444;")
            self._conn_dot.setText(tr("not_connected"))
            self._conn_dot.setStyleSheet("color: #cc4444;")
        ws_state = tr("log_ws_connected") if connected else tr("log_ws_disconnected")
        self._log(f"WebSocket {ws_state}: {reason}")

    @Slot(str, str)
    def _on_status_changed(self, sig_state: str, ord_state: str):
        status_text = f"{sig_state}\n({ord_state})"
        self._status_lbl.setText(status_text)
        self._order_status_lbl.setText(tr("order_lbl") + ord_state)

    @Slot(dict)
    def _on_position_updated(self, info: dict):
        qty = info.get("qty", 0)
        avg = info.get("avg_price", 0)
        high = info.get("high_after_buy", 0)
        trigger = info.get("sell_trigger", "--")
        pnl = info.get("unrealized_pnl", 0)

        self._pos_qty_lbl.setText(tr("pos_qty_fmt", q=qty))
        self._pos_avg_lbl.setText(tr("pos_avg_fmt", p=avg) if avg else "--")
        self._pos_high_lbl.setText(tr("pos_avg_fmt", p=high) if high else "--")
        self._pos_trigger_lbl.setText(trigger)

        self._position_lbl.setText(tr("position_fmt", q=qty))
        self._avg_price_lbl.setText(tr("avg_fmt", p=avg) if avg else tr("avg_none"))

        color = "#ff4444" if pnl >= 0 else "#4488ff"
        self._unrealized_inline.setText(f"{pnl:+,} KRW")
        self._unrealized_inline.setStyleSheet(
            f"color: {color}; font-weight: bold;")

    @Slot(dict)
    def _on_pnl_updated(self, info: dict):
        def fmt(v):
            color = "#ff4444" if v >= 0 else "#4488ff"
            return f'<span style="color:{color}; font-size:14px; font-weight:bold;">{v:+,} KRW</span>'

        self._unreal_lbl.setText(f"{info.get('unrealized', 0):+,} KRW")
        self._real_lbl.setText(f"{info.get('realized', 0):+,} KRW")
        self._total_lbl.setText(f"{info.get('total', 0):+,} KRW")

        t = info.get('trades', 0)
        w = info.get('wins', 0)
        l = info.get('losses', 0)
        wr = info.get('win_rate', 0.0)

        self._trades_lbl.setText(str(t))
        self._winloss_lbl.setText(f"{w} / {l}")
        self._winrate_lbl.setText(f"{wr:.1f} %")

        # Color P&L labels
        for lbl, val in [(self._unreal_lbl, info.get('unrealized', 0)),
                         (self._real_lbl, info.get('realized', 0)),
                         (self._total_lbl, info.get('total', 0))]:
            color = "#ff4444" if val >= 0 else "#4488ff"
            lbl.setStyleSheet(
                f"color: {color}; font-size: 14px; font-weight: bold;")

    @Slot(dict)
    def _on_trade_completed(self, trade: dict):
        """Add row to trade history table."""
        row = self._trade_table.rowCount()
        self._trade_table.insertRow(0)  # newest at top

        def cell(text, color=None):
            item = QTableWidgetItem(str(text))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if color:
                item.setForeground(QColor(color))
            return item

        t_type = trade.get("type", "")
        pnl = trade.get("pnl", 0)
        ticks = trade.get("ticks", 0)

        is_buy = t_type == "Buy"
        type_color = "#e74c3c" if is_buy else "#3498db"
        pnl_color = "#ff4444" if pnl >= 0 else "#4488ff"

        self._trade_table.setItem(0, 0, cell(trade.get("time", "")))
        self._trade_table.setItem(0, 1, cell(
            tr("trade_buy") if is_buy else tr("trade_sell"), type_color))
        self._trade_table.setItem(0, 2, cell(f"{trade.get('price',0):,}"))
        self._trade_table.setItem(0, 3, cell(str(trade.get("qty", ""))))
        self._trade_table.setItem(0, 4, cell(trade.get("reason", "")))
        self._trade_table.setItem(0, 5, cell(
            f"{ticks:+d}", "#e74c3c" if ticks >= 0 else "#3498db"))
        self._trade_table.setItem(0, 6, cell(
            f"{trade.get('high',0):,}" if trade.get("high") else "--"))
        self._trade_table.setItem(0, 7, cell(
            f"{pnl:+,}" if not is_buy else "--", pnl_color if not is_buy else None))

        # Also add chart marker
        self._chart_view.add_trade_marker(
            trade.get("price", 0), is_buy, datetime.now())

    @Slot(str)
    def _on_error(self, msg: str):
        self._log(tr("log_error_prefix") + msg)

    # ── ACTIONS ───────────────────────────────────────────────────────────────

    def _search_stock(self):
        symbol = self._sym_input.text().strip()
        if not symbol:
            return

        if not self.config.get("app_key"):
            QMessageBox.warning(self, tr("warning"), tr("enter_api_first"))
            return

        if not self.api._token:
            ok = self.api.get_token()
            if not ok:
                self._log(tr("log_auth_fail"))
                return

        info = self.api.get_stock_info(symbol)
        if info and info.get("price", 0) > 0:
            self._current_symbol = symbol
            self._current_stock_name = info.get("name", symbol)
            self._current_price = info["price"]
            self._stock_name_lbl.setText(self._current_stock_name)
            self._chart_name_lbl.setText(self._current_stock_name)
            self._price_lbl.setText(f"{info['price']:,}")
            change = info.get("change", 0)
            rate = info.get("change_rate", 0)
            color = "#e74c3c" if change >= 0 else "#3498db"
            sign = "▲" if change >= 0 else "▼"
            self._price_change_lbl.setText(
                f"{sign} {abs(change):,} ({rate:+.2f}%)")
            self._price_change_lbl.setStyleSheet(f"color: {color};")
            self._vol_lbl.setText(f"Volume: {info.get('volume',0):,}")

            # Start WS for this symbol
            self.ws.stop()
            self.engine.set_symbol(symbol)
            self.ws.start(symbol)
            self._log(tr("log_stock_selected",
                         name=self._current_stock_name, sym=symbol,
                         price=info['price']))
            self._api_connected = True
            self._status_conn.setText(tr("kis_connected_lbl"))
            self._status_conn.setStyleSheet("color: #44cc44;")
        else:
            self._log(tr("log_stock_fail") + symbol)
            QMessageBox.warning(self, tr("error_title"),
                                tr("stock_not_found") + symbol)

    def _start_trading(self):
        if not self._current_symbol:
            QMessageBox.warning(self, tr("warning"), tr("select_stock_warn"))
            return
        if not self.config.get("app_key"):
            QMessageBox.warning(self, tr("warning"), tr("enter_api_warn"))
            return

        self.config.set("start_time", self._start_time_edit.text().strip())
        self.config.set("end_time", self._end_time_edit.text().strip())

        mode = tr("paper_mode") if self.config.get("is_paper") else tr("live_mode")
        reply = QMessageBox.question(
            self, tr("start_confirm_title"),
            tr("start_confirm_msg", mode=mode, stock=self._current_stock_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._trading_active = True
        self.engine.start_trading()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._log(tr("log_start", mode=mode))

    def _stop_trading(self):
        reply = QMessageBox.question(
            self, tr("stop_confirm_title"), tr("stop_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._trading_active = False
        self.engine.stop_trading()
        self.btn_start.setEnabled(True)
        self._log(tr("log_stop"))

    def _emergency_stop(self):
        reply = QMessageBox.question(
            self, tr("emergency_title"), tr("emergency_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        liquidate_reply = QMessageBox.question(
            self, tr("liquidate_title"), tr("liquidate_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        liquidate = liquidate_reply == QMessageBox.StandardButton.Yes

        self._trading_active = False
        self.engine.emergency_stop(liquidate=liquidate)
        self.btn_start.setEnabled(True)
        yes_no = tr("yes") if liquidate else tr("no")
        self._log(tr("log_emergency", v=yes_no))

    def _set_order_type(self, order_type: str):
        self.config.set("order_type", order_type)
        self.config.save()
        is_market = order_type == "MARKET"
        self.btn_market.setChecked(is_market)
        self.btn_limit.setChecked(not is_market)
        active   = ("background-color:#1a3a8c; border:2px solid #3a5acc;"
                    "color:white; font-weight:bold; border-radius:4px;")
        inactive = ("background-color:#1e1e3a; border:1px solid #3a3a6a;"
                    "color:#a0a0c0; border-radius:4px;")
        self.btn_market.setStyleSheet(active   if is_market else inactive)
        self.btn_limit.setStyleSheet (inactive if is_market else active)

    def _inc_qty(self):
        qty = self.config.get("order_qty", 10) + 1
        self.config.set("order_qty", qty)
        self._qty_lbl.setText(str(qty))

    def _dec_qty(self):
        qty = max(1, self.config.get("order_qty", 10) - 1)
        self.config.set("order_qty", qty)
        self._qty_lbl.setText(str(qty))

    def _open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._log(tr("log_settings_saved"))
            is_live = not self.config.get("is_paper", True)
            mode_str = "🔴 LIVE" if is_live else "📄 PAPER"
            self.setWindowTitle(f"{APP_TITLE}  {mode_str}")
            self._qty_lbl.setText(str(self.config.get("order_qty", 10)))

    def _open_log(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("log_title"))
        dlg.setMinimumSize(700, 400)
        dlg.setStyleSheet(DARK_STYLE)
        layout = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setStyleSheet("background:#050508; color:#88cc88; font-family:Consolas;")
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            te.setPlainText(content[-20000:])
            from PySide6.QtGui import QTextCursor
            te.moveCursor(QTextCursor.MoveOperation.End)
        except Exception:
            te.setPlainText(tr("log_no_file"))
        layout.addWidget(te)
        dlg.exec()

    def _export_trades(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_title"), "trades.csv", "CSV (*.csv)")
        if path:
            self.db.export_trades_csv(path)
            QMessageBox.information(self, tr("export_done_title"),
                                    tr("export_done_msg") + path)
            self._log(tr("log_export") + path)

    # ── TIMER SLOTS ───────────────────────────────────────────────────────────

    def _update_chart(self):
        """Update chart with latest candle data."""
        candles = self.engine.candles.get_candles()
        if not candles:
            return
        # Calculate MA20 for each candle
        ma20_vals = []
        for i in range(len(candles)):
            if i >= 19:
                closes = [c.close for c in candles[i-19:i+1]]
                ma20_vals.append(sum(closes) / 20)
            else:
                ma20_vals.append(0)

        try:
            self._chart_view.update_candles(candles, ma20_vals)
        except Exception as e:
            log.debug(f"Chart update error: {e}")

    def _update_clock(self):
        now = QDateTime.currentDateTime()
        self._status_time.setText(now.toString("yyyy-MM-dd HH:mm:ss (KST)"))

    def _check_connection(self):
        """Periodic connection health check."""
        if self._ws_connected and self.engine.ws.is_connected:
            pass
        else:
            if self._trading_active:
                self._log(tr("log_conn_warn"))

    # ── LOGGING ───────────────────────────────────────────────────────────────

    @Slot(str)
    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log_view.append(line)
        # Scroll to bottom
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())
        log.info(msg)

    # ── CLOSE ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, tr("exit_title"), tr("exit_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        self.ws.stop()
        self.engine.stop_trading(reconcile=False)
        self.config.save()
        log.info("Application closed")
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("KIS Auto Trader")
    app.setApplicationVersion(VERSION)
    app.setStyle("Fusion")

    # Apply dark palette for native widgets
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0d0d1a"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#d0d0e8"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#1a1a2e"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#151530"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1a1a2e"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#d0d0e8"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#d0d0e8"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1a1a2e"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#d0d0e8"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2a2a5a"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()