# Test Suite

這是一個簡化的單元測試套件，專注在最重要的核心功能。

## 測試結構

```text
tests/
├── test_indicators.py    # 技術指標計算測試
├── test_utils.py        # yfinance工具函數測試
└── README.md           # 這個文件
```

## 運行測試

```bash
# 運行所有測試
PYTHONPATH=. pytest tests/ -v

# 只運行特定測試文件
PYTHONPATH=. pytest tests/test_indicators.py -v
```

## 測試覆蓋

### 技術指標 (test_indicators.py)

- ✅ 移動平均線 (Moving Averages)
- ✅ 布林通道 (Bollinger Bands)
- ✅ RSI (相對強弱指標)
- ✅ MACD (指數平滑移動平均線)
- ✅ 邊界條件測試 (空資料、單一值、常數值)

### 工具函數 (test_utils.py)

- ✅ 股票代碼驗證
- ✅ 基本錯誤處理

## 設計原則

1. **簡化優先**: 只測試最重要的純函數
2. **無外部依賴**: 使用模擬資料，不依賴網路請求
3. **快速執行**: 所有測試應該在1秒內完成
4. **易於維護**: 測試結構清晰，容易理解和擴展

## 未來擴展

可以考慮添加的測試：

- 更多技術指標 (CCI, KDJ, ADX等)
- 資料介面測試 (有適當的mock)
- Agent功能測試 (單元測試級別)
