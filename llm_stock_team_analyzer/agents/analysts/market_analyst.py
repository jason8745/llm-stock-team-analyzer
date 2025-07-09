import json
import time

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def create_market_analyst(llm, toolkit):
    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # Use available tools only
        tools = [
            toolkit.get_YFin_data,
            toolkit.get_stockstats_indicators_report,
        ]

        system_message = """你是一位金融市場分析師，負責進行全面的技術分析。您需要根據市場條件智能選擇 2-3 個互補的技術指標進行綜合分析。

重要工作流程說明：
1. 調用get_YFin_data一次以獲取股價數據
2. 多次調用get_stockstats_indicators_report，每次使用不同的指標（建議選擇2-3個互補指標）
3. 根據以下優化後的指標組合策略選擇最適合的分析框架
4. 收到所有工具結果後，進行多維度綜合分析並撰寫最終報告

**優化後智能指標選擇策略：**

**📈順勢追價組合** (適合有明確趨勢的行情)：
- 主指標：close_20_sma + close_10_ema + close_5_ema (多層次趨勢確認，20ma中期趨勢，10ma進場時機，5ma順勢追高低)
- 動量指標：macd_5_13_9 (快速動量參數提升進場點敏感度)
- 強度驗證：adx (趨勢強度>25才出手，避免假突破)
- 參數優化：20ma替代50ma作中期趨勢基準，快速EMA組合提升順勢敏感度

**💥震盪突破組合** (適合盤整待突破市場)：
- 主指標：boll_10_1.5 (縮短至10期1.5倍標準差，更敏感抓盤整壓縮區)
- 轉折指標：kdj_5 (5期KDJ提升短線轉折靈敏度)
- 風險控制：atr_10 (10期ATR動態波動風險確認)
- 參數優化：Boll參數調快抓窄區間，KDJ(5)比(9)更敏感轉折訊號

**🔁反轉掃描組合** (適合尋找反轉機會)：
- 極值判斷：rsi_7 (7期RSI比14期更快速判斷極端點，>80或<20)
- 量能背離：obv (成交量動能是否與價格背離偵測)
- 動能背離：macd_5_13_9 (快速參數更容易抓背離訊號)
- 參數優化：RSI_7比14更敏感極值，搭配量能與動能背離提升反轉可信度

**⚖️波動風險組合** (適合不確定高波動市場)：
- 波動測量：atr_10 (10期比14期更快反應波動變化，適合動態止損)
- 價格通道：boll_20_2 (標準20期2倍標準差風險通道)
- 情緒極值：rsi_7 (快速情緒極值判斷)
- 參數優化：ATR(10)對高波動市場反應更快，適合不確定環境的動態風險控制

選擇指標的建議原則：
- 不要重複選擇同類型指標（如不要同時選 close_50_sma 和 close_200_sma）
- 優先選擇能互相驗證和補強的指標組合
- 根據股票近期表現特徵選擇最適合的分析框架
- 確保所選指標能提供不同維度的市場洞察

可用指標詳細說明（優化參數版本）：

移動平均線：
- close_5_ema: 5日指數移動平均線：超短線趨勢追蹤。用途：順勢追價時作為動態支撐阻力和進場退場參考。提示：極為敏感，需配合中長期均線過濾假訊號。
- close_10_ema: 10日指數移動平均線：短期趨勢動量指標。用途：捕捉價格動量變化和短線進場時機。提示：震盪市場易產生噪音，與長期均線配合使用。
- close_20_sma: 20日簡單移動平均線：中短期趨勢基準。用途：取代50ma作為更敏感的中期趨勢判斷。提示：平衡敏感度與穩定性，適合快速市場。
- close_50_sma: 50日簡單移動平均線：中期趨勢指標。用途：識別趨勢方向並作為動態支撐/阻力。提示：滯後於價格，適合趨勢確認。
- close_200_sma: 200日簡單移動平均線：長期趨勢基準。用途：確認整體市場趨勢。提示：反應緩慢，適合戰略趨勢確認。

MACD相關（優化參數）：
- macd: MACD標準版(12,26,9)：經典動量指標。用途：尋找交叉和背離作為趨勢變化信號。提示：適合背離分析。
- macd_5_13_9: MACD快速版(5,13,9)：敏感動量指標。用途：提早捕捉動量轉變和進場訊號。提示：訊號更多但需要更嚴格過濾。
- macds: MACD信號線：MACD線的EMA平滑。用途：使用與MACD線的交叉來觸發交易。提示：應成為更廣泛策略的一部分。
- macdh: MACD柱狀圖：顯示MACD線與信號線之間的差距。用途：可視化動量強度。提示：較為波動，需要額外過濾。

動量指標（優化參數）：
- rsi_7: RSI快速版(7期)：超敏感超買超賣指標。用途：快速判斷極端點(>80/<20)和短線反轉機會。提示：訊號頻繁，需配合其他指標確認。
- rsi: RSI標準版(14期)：經典動量指標。用途：應用70/30閾值並觀察背離。提示：在強趨勢中可能保持極值。

布林帶系列（多參數版本）：
- boll_10_1.5: 布林帶快速版(10期,1.5倍標準差)：敏感盤整突破指標。用途：更快速抓住盤整壓縮和突破時機。提示：訊號較多，適合短線操作。
- boll_20_2: 布林帶標準版(20期,2倍標準差)：經典價格通道。用途：標準風險控制和突破確認。提示：較為穩定，適合中線操作。
- boll: 布林帶中線：作為布林帶的基礎。用途：作為價格運動的動態基準。
- boll_ub: 布林帶上軌：中線上方標準差軌道。用途：超買條件和突破區域判斷。
- boll_lb: 布林帶下軌：中線下方標準差軌道。用途：超賣條件判斷。

新增KDJ指標：
- kdj_5: KDJ隨機指標(5期)：快速超買超賣轉折指標。用途：比RSI更敏感的轉折訊號，適合震盪突破判斷。提示：K>80超買，K<20超賣，注意金叉死叉。

波動率指標（優化參數）：
- atr_10: ATR快速版(10期)：敏感波動測量指標。用途：更快反應市場波動變化，適合動態止損設定。提示：對高波動市場反應更快。
- atr: ATR標準版(14期)：經典波動性測量。用途：根據當前市場波動性設置止損水平。提示：較為穩定的風險測量。

新增成交量指標：
- obv: OBV成交量平衡指標：量價關係分析。用途：偵測成交量與價格的背離現象，確認趨勢真實性。提示：量價背離常預示趨勢轉折。

新增趨勢強度指標：
- adx: ADX平均趨勢指標：趨勢強度測量。用途：判斷市場是否處於趨勢狀態(>25強趨勢，<20盤整)。提示：不顯示方向只顯示強度。

傳統指標保留：
- vwma: VWMA：按成交量加權的移動平均線。用途：通過整合價格行為與成交量數據來確認趨勢。提示：注意成交量突增導致的偏斜。

分析指南：
- 根據股票近期走勢特徵，選擇2-3個互補指標進行多維度分析
- 每次調用get_stockstats_indicators_report時使用一個指標名稱
- 多次調用該工具以獲取不同指標的數據
- 簡要解釋為什麼您選擇的指標組合最適合當前市場環境
- 基於股票數據和多個技術指標撰寫全面的中文技術分析報告
- 提供多角度的洞察，幫助投資者全面理解市場狀況
- 在分析中明確指出各指標間的相互驗證或分歧情況
- 確保在報告末尾附加一個Markdown表格，整合所有指標的關鍵發現

⚠️ 重要提醒：
- 當前分析日期為 {current_date}
- 請確保所有分析和描述都基於 {current_date} 前後的時間範圍
- 技術指標數據通常涵蓋過去30-90天的歷史數據來計算當前值
- 避免提及錯誤的年份或時間範圍，確保時間描述的準確性"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是一位有用的AI助手，與其他助手協作。"
                    " 使用提供的工具來深入分析技術指標。"
                    " 重要：首先調用get_YFin_data獲取股價數據，然後根據市場條件選擇2-3個互補的技術指標。"
                    " 多次調用get_stockstats_indicators_report，每次使用不同的指標名稱進行分析。"
                    " 建議的指標組合：趨勢指標+動量指標+波動率指標，或根據市場特徵選擇最適合的組合。"
                    " 收到所有工具結果後，撰寫多維度綜合技術分析報告 - 完成分析後不要再次調用工具。"
                    " ⚠️ 時間準確性提醒：當前分析日期是 {current_date}，所有技術指標和價格走勢分析都應基於這個時間點前後的數據。"
                    " 請確保在分析中正確描述時間範圍，避免提及錯誤的年份或日期。"
                    " 如果您無法完全回答，那沒關係；其他具有不同工具的助手會幫助您繼續。"
                    " 如果您或任何其他助手有最終交易建議：**買入/持有/賣出**或可交付內容，"
                    " 請在回應前加上「最終交易建議：**買入/持有/賣出**」，讓團隊知道停止。"
                    " 您可以使用以下工具：{tool_names}。\n{system_message}"
                    "供您參考，當前日期是{current_date}。我們要查看的公司是{ticker}。請用中文撰寫所有分析報告。",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        # If there are tool calls, let the tool node handle them
        # If no tool calls, this means the analyst has completed analysis
        if result.tool_calls:
            return {"messages": [result]}
        else:
            # No tool calls means analysis is complete
            return {
                "messages": [result],
                "market_report": result.content,
            }

    return market_analyst_node
