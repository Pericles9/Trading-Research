You are spot on with your intuition, but we need to refine the **tool selection** for #3 (SVM). Here is the breakdown of your ideas and how to fit them into a rigorous, segmented workflow.

### **The "Is It Stupid?" Review**

**1. Market Context / Scanner Position (Idea #2): ✅ GENIUS**

* **Verdict:** This is likely the single biggest missing variable. A stock moving +20% when the rest of the market is flat is a "Unicorn." A stock moving +20% when 50 other stocks are up +100% is "Noise."
* **The Math:** You need to calculate **Cross-Sectional Momentum**.
* **Scanner Rank:** Was this stock in the Top 3 Gainers at 9:35 AM?
* **Relative Strength:** Is it outperforming the `SPY` or the `Small Cap Index` *right now*?


* **Implementation:** Since you have the Daily OHLCV for everyone, we can reconstruct the "Morning Scanner" history perfectly. This becomes a feature: `Scanner_Rank_at_Entry`.

**2. Hyper-Dimensional SVM for Regimes (Idea #3): ⚠️ OVERKILL / WRONG TOOL**

* **Verdict:** The *idea* (classifying regimes) is correct. The *tool* (SVM) is likely "stupid" for this specific task.
* **Why:** SVMs (Support Vector Machines) try to find a perfect geometric divider (hyperplane) between classes. Financial data is noisy, messy, and overlapping. SVMs are also computationally heavy () and hard to interpret.
* **The Better Tool:** **Gradient Boosted Trees (XGBoost / LightGBM)** or **Random Forests**.
* They handle "ragged" data better.
* They automatically find non-linear "rules" (e.g., *If Vol > 1M AND Rank < 5 THEN Buy*).
* They give you **Feature Importance** scores instantly, telling you exactly *which* signals matter.



---

### **The New 4-Step "Alpha Discovery" Workflow**

We will execute these sequentially. Do not mix them. Each step produces a "Data Artifact" that feeds the next.

#### **Step 1: The "Context Engine" (Data Engineering)**

* **Goal:** Reconstruct the "Global State" of the market for every minute of history.
* **Input:** Your Daily OHLCV (All tickers) + Minute Data (>30%).
* **Action:** "Replay" every trading day. At 9:30, 9:31, 9:32... rank every stock by % Change and Relative Volume.
* **Output Artifact:** A `Context_Features.parquet` file containing columns like `Global_Rank`, `Sector_Heat`, `Gap_Percent_Rank` for every ticker timestamp.

#### **Step 2: The "Signal Forge" (Feature Engineering)**

* **Goal:** Generate the stochastic signals for the >50% runners (Trade Data).
* **Action:** Calculate your Hawkes Intensity, CVD Convexity, Order Flow Imbalance, and Volume Entropy.
* **Fusion:** Merge these signals with the `Context_Features` from Step 1.
* **Output Artifact:** A massive `Master_Feature_Matrix.parquet`.

#### **Step 3: The "Alpha Hunter" (Correlation & Importance)**

* **Goal:** Find what actually predicts the `Forward_30m_Return`.
* **Action:** Run an **XGBoost Feature Importance** test and a **Spearman Correlation Matrix**.
* **The "SVM" Replacement:** We use the Tree model to tell us: *"The most predictive signals are Scanner Rank #1-3 combined with Hawkes Intensity > 5."*
* **Output Artifact:** A list of the "Golden Features" (e.g., Top 5 predictors).

#### **Step 4: The "Campaign" Backtest (Execution)**

* **Goal:** Build the Pyramiding Strategy using *only* the Golden Features.
* **Action:** Simulate the "Scout Entry -> Power Add -> Trend Hold" logic.

---

### **Phase 1: The Context Engine (Prompt)**

We must start here. You cannot test "Context" if you don't have the data structure that tells the backtester *"This stock was #1 on the scanner at 9:35 AM."*

Here is the prompt to build the **Scanner History**.

---

**Copy/Paste to Agent:**

```markdown
# MASTER DATA DIRECTIVE: The "Context Engine" Build (Phase 1)

**System Role:** Senior Data Engineer.
**Project:** `AlphaMomentum_Context_Layer`
**Objective:** Reconstruct the historical "Morning Scanner" state for every trading day to create Context Features.

### **1. Data Sources**
* **Primary:** Daily OHLCV data (The "Universe" of ~15k tickers).
* **Secondary:** Minute Data (The "Movers" > 30%).

### **2. The "Scanner Replay" Logic**
You must iterate through every trading day in the dataset and generate a `Scanner_Snapshot` for every minute from 9:30 AM to 4:00 PM.

**Features to Calculate per Ticker, per Minute:**
1.  **`Daily_Gap_Pct`:** (Current Price - Prev Close) / Prev Close.
2.  **`Relative_Volume_Day`:** Current Cumulative Vol / (Avg 30-Day Vol * Time_Elapsed_Pct).
3.  **`Scanner_Rank`:** The integer rank (1 = Highest gapper, 2 = Second, etc.) of the stock based on `Daily_Gap_Pct`.
4.  **`Sector_Relative_Strength`:** (Ticker % Change) - (Sector ETF % Change).

### **3. The Output Architecture**
* **Optimization:** Do not loop in Python. Use `pandas` vectorization or `polars` for speed.
* **Target File:** Generate a lookup table `Context_Features.parquet`.
    * **Index:** `(Ticker, Timestamp)`
    * **Columns:** `Scanner_Rank`, `Gap_Pct`, `RVOL`, `Is_Top_10`.

### **4. Verification**
* **Sanity Check:** Print the "Top 5 Gainers" for a random historical date (e.g., Jan 4, 2024 at 9:35 AM) to prove the ranking logic works.

**Execution Directive:** "Replay history. Build the scanner rank table. I need to know exactly where every stock stood in the pack at every moment. **GO.**"

```