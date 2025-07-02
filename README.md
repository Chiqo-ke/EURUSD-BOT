# EURUSD-BOT

This documentation provides a detailed guide of how i use the EURUSD-BOT for both backtesting and forward testing operations. **It does not gaurantee profitability**.

## Table of Contents
- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [System Requirements](#system-requirements)
- [Strategy Architecture](#strategy-architecture)
- [Backtesting Guide](#backtesting-guide)
- [Forward Testing Guide](#forward-testing-guide)

## Overview
EURUSD-BOT is a sophisticated trading bot designed for the EUR/USD currency pair, featuring:
- Backtesting: For testing trading strategies against historical data
- Forward Testing: For real-time strategy testing in current market conditions
- Multi-timeframe analysis using M30 and M3 data
- Advanced trend detection and risk management systems

## Technology Stack
- Python
- MetaTrader 5 (MT5) for ### ### execution
- tvDatafeed for data collection
- Custom modules:
  - `data.py`: Data collection and processing
  - `backtest.py`: Backtesting engine
  - `signals.py`: Signal generation
  - `simulation.py`: Trade simulation
  - `forward_test.py`: Live trading execution
  - `reporting.py`: Performance analysis

## System Requirements

### Common Requirements
- Python environment
- Required Python packages (install via pip):
  - MetaTrader5
  - tvDatafeed
  - Other dependencies (specified in requirements.txt)

### Forward Testing Specific
- MetaTrader 5 Desktop Application
- Active MT5 trading account
- Stable internet connection

### Backtesting Specific
- Access to the fetcher notebook for historical data
- Sufficient storage for CSV data files

## Strategy Architecture

### 1. Data Collection
- **Fetcher Component**
  - Utilizes tvDatafeed for data download
  - Saves EURUSD data in CSV format
  - Handles both real-time and historical data
  
### 2. Multi-Timeframe Analysis
#### M30 (30-minute) Timeframe - Trend Detection
- Implements Bollinger Bands strategy
  - Uptrend: Close above upper band
  - Downtrend: Close below lower band
- Volume filtering for trend confirmation

#### M3 (3-minute) Timeframe - Entry Signals
- Entry signal generation based on M30 trend alignment
- EMA-based entry system:
  - 10-period EMA reference
  - Configurable pip threshold for crosses
  - Buy signals: Previous close above EMA + threshold (during uptrend)
  - Sell signals: Previous close below EMA - threshold (during downtrend)

### 3. Risk Management
- Fixed Take Profit (TP) and Stop Loss (SL) in pips
- Maximum concurrent trades limit
- Default Settings:
  - TP: 80 pips
  - SL: 20 pips

## Backtesting Guide

### Step 1: Data Preparation
1. Access the fetcher notebook
2. Download historical EURUSD data
3. Ensure data includes both M30 and M3 timeframes
4. Save data in the correct CSV format

### Step 2: Configuration
1. Open the backtesting configuration file
2. Set strategy parameters:
   - Bollinger Bands settings
   - EMA period (default: 10)
   - Pip thresholds for entry
   - TP/SL levels
   - Volume thresholds
   - Maximum concurrent trades

### Step 3: Running Backtests
1. Navigate to the backtesting directory
2. Execute the backtesting script:
   ```bash
   python backtest.py --config your_config.json
   ```
3. Monitor the execution and wait for results

### Step 4: Analyzing Results
The reporting system provides:
- Win rate calculation
- Profit factor analysis
- Maximum consecutive wins/losses
- Detailed trade logs
- Performance metrics

## Forward Testing Guide

### Step 1: Initial Setup
1. Install MetaTrader 5 desktop application
2. Configure MT5 account settings
3. Verify data feed connection
4. Test API connectivity

### Step 2: Configuration
1. Open the forward testing configuration file
2. Configure:
   - MT5 credentials
   - Trading parameters (identical to backtest)
   - Risk management settings
   - Data collection parameters

### Step 3: Running Forward Tests
1. Ensure MT5 is running and logged in
2. Start the forward testing module:
   ```bash
   python forward_test.py --config live_config.json
   ```
3. Monitor real-time execution

### Step 4: Monitoring and Logging
- Real-time trade execution monitoring
- Position tracking
- Error logging
- Performance metrics tracking

## Best Practices
1. Always validate strategy in backtesting before live testing
2. Start with small position sizes in forward testing
3. Maintain comprehensive logs
4. Regular system monitoring
5. Keep MT5 platform updated

## Troubleshooting
Common issues and solutions:
1. MT5 connection errors
2. Data synchronization issues
3. Signal generation problems
4. Risk management violations

## Support
For additional support:
- Check the Issues section in the repository
- Review existing documentation
- Contact the repository maintainers

---

**Note**: This documentation will be continuously updated. Please create an issue if you find any areas that need clarification or improvement.
