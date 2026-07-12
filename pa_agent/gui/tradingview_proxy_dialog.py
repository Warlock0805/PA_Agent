"""Local proxy settings used only by the TradingView data source."""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pa_agent.config.paths import SETTINGS_JSON_PATH
from pa_agent.config.settings import Settings, save_settings
from pa_agent.data.tradingview_proxy import TradingViewProxy


class _ConnectivityWorker(QThread):
    completed = pyqtSignal(bool, str)

    def __init__(self, proxy: TradingViewProxy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._proxy = proxy

    def run(self) -> None:
        from pa_agent.data.tradingview_connectivity import check_tradingview_connectivity

        ok, detail = check_tradingview_connectivity(proxy=self._proxy)
        self.completed.emit(ok, detail or "")


class TradingViewProxyDialog(QDialog):
    """Edit and test the unauthenticated local TradingView proxy."""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._worker: _ConnectivityWorker | None = None
        self.setWindowTitle("TradingView 代理设置")
        self.setMinimumWidth(420)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        hint = QLabel("仅用于 TradingView, 不影响 MT5、Codex 或其他数据源。")
        hint.setWordWrap(True)
        root.addWidget(hint)

        form = QFormLayout()
        self._enabled_check = QCheckBox("通过代理连接 TradingView")
        self._enabled_check.toggled.connect(self._sync_enabled_state)
        form.addRow("启用代理:", self._enabled_check)

        self._type_combo = QComboBox()
        self._type_combo.addItem("HTTP / HTTPS", "http")
        self._type_combo.addItem("SOCKS5", "socks5")
        form.addRow("协议:", self._type_combo)

        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("127.0.0.1")
        form.addRow("主机:", self._host_edit)

        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(7890)
        form.addRow("端口:", self._port_spin)
        root.addLayout(form)

        test_row = QHBoxLayout()
        self._test_btn = QPushButton("测试连接")
        self._test_btn.clicked.connect(self._on_test_connection)
        self._test_status = QLabel("")
        self._test_status.setWordWrap(True)
        test_row.addWidget(self._test_btn)
        test_row.addWidget(self._test_status, 1)
        root.addLayout(test_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_values(self) -> None:
        general = self._settings.general
        self._enabled_check.setChecked(general.tradingview_proxy_enabled)
        index = self._type_combo.findData(general.tradingview_proxy_type)
        if index >= 0:
            self._type_combo.setCurrentIndex(index)
        self._host_edit.setText(general.tradingview_proxy_host)
        self._port_spin.setValue(general.tradingview_proxy_port or 7890)
        self._sync_enabled_state(self._enabled_check.isChecked())

    def _sync_enabled_state(self, enabled: bool) -> None:
        for control in (self._type_combo, self._host_edit, self._port_spin, self._test_btn):
            control.setEnabled(enabled)

    def current_proxy(self) -> TradingViewProxy:
        return TradingViewProxy(
            enabled=self._enabled_check.isChecked(),
            proxy_type=self._type_combo.currentData(),
            host=self._host_edit.text().strip(),
            port=self._port_spin.value(),
        )

    def _validate_proxy(self) -> TradingViewProxy | None:
        proxy = self.current_proxy()
        try:
            proxy.websocket_options()
        except ValueError as exc:
            QMessageBox.warning(self, "代理设置无效", str(exc))
            return None
        return proxy

    def _on_save(self) -> None:
        proxy = self._validate_proxy()
        if proxy is None:
            return
        general = self._settings.general
        general.tradingview_proxy_enabled = proxy.enabled
        general.tradingview_proxy_type = proxy.proxy_type
        general.tradingview_proxy_host = proxy.host
        general.tradingview_proxy_port = proxy.port if proxy.enabled else 0
        save_settings(self._settings, SETTINGS_JSON_PATH)
        self.accept()

    def _on_test_connection(self) -> None:
        proxy = self._validate_proxy()
        if proxy is None:
            return
        self._test_btn.setEnabled(False)
        self._test_status.setText("正在通过代理连接 TradingView…")
        self._worker = _ConnectivityWorker(proxy, self)
        self._worker.completed.connect(self._on_test_completed)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_test_completed(self, ok: bool, detail: str) -> None:
        self._test_btn.setEnabled(self._enabled_check.isChecked())
        if ok:
            self._test_status.setText("代理连接 TradingView 成功。")
            return
        self._test_status.setText(
            f"代理不可达、协议不匹配或 TradingView 不可达: {detail or '未知原因'}"
        )
