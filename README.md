# Telegram AI Trading Assistant

Enterprise-grade Telegram bot for automated trading signals, market analysis, and technical indicators.

## Features

### Automatic Telegram Features
- Automatically send AI Trading Signals to Telegram Channels and Groups
- Support unlimited Telegram Channels and Groups
- Good Morning message every day with market outlook (6 AM UTC)
- Good Night message every night with trading summary (10 PM UTC)
- Daily motivational trading messages (9 AM UTC)
- Market opening/closing notifications (Sydney, Tokyo, London, New York)
- Daily market analysis (8 AM UTC)
- Daily trading plan

### Trading Signals
- Automatically generate Buy/Sell signals with technical analysis
- Automatically publish signals to Telegram
- Edit signal messages after updates
- Signal expiration notifications
- Cancel expired signals automatically

### SL / TP Notifications
- Trade Opened notification
- Entry Hit notification
- Take Profit 1 Hit ✅ notification
- Take Profit 2 Hit ✅ notification
- Take Profit 3 Hit ✅ notification
- Stop Loss Hit ❌ notification
- Signal Cancelled notification
- Signal Updated notification

### Performance Tracking
- Win Rate calculation
- Loss Rate calculation
- Risk/Reward Ratio tracking
- Daily performance report
- Weekly performance report
- Monthly performance report
- Signal accuracy report
- Profit/Loss summary
- Admin statistics dashboard

### User Features
- User profiles
- VIP/Premium membership
- Referral system
- Multi-language support (English, Sinhala)
- Trading journal
- Favorite markets
- Price alerts
- Watchlist management
- Portfolio tracking
- Trade history

### Admin Features
- Admin dashboard
- User management (add, remove, ban, unban)
- Broadcast messages to all users
- Manual signal posting
- Automatic signal enable/disable
- Channel management
- Group management
- Premium user management
- Statistics dashboard
- Logs and monitoring

### Market Analysis
- Support for Crypto and Forex markets
- Binance and Bybit integration
- Technical indicators: EMA, SMA, RSI, MACD, Bollinger Bands, ATR
- Candlestick pattern detection
- Support/Resistance level identification

## Tech Stack

- Python 3.11
- aiogram 3.x (Telegram Bot Framework)
- ccxt (Exchange API)
- pandas, numpy (Data Analysis)
- matplotlib, mplfinance (Charts)
- Supabase (Primary Database - PostgreSQL)
- SQLite (Fallback Database)
- Docker

## Quick Start

### Prerequisites
- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd trading-bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t trading-bot .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     --name trading-bot \
     --env-file .env \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/logs:/app/logs \
     -v $(pwd)/charts:/app/charts \
     trading-bot
   ```

### Render Deployment

1. Connect your repository to Render
2. Set environment variables in Render dashboard
3. Deploy with Docker runtime

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram Bot Token | Required |
| `ADMIN_IDS` | Comma-separated admin IDs | Required |
| `SUPER_ADMIN_ID` | Super admin Telegram ID | Required |
| `CHANNEL_ID` | Main channel ID | Optional |
| `GROUP_ID` | Main group ID | Optional |
| `BINANCE_API_KEY` | Binance API Key | Optional |
| `BINANCE_API_SECRET` | Binance API Secret | Optional |
| `BYBIT_API_KEY` | Bybit API Key | Optional |
| `BYBIT_API_SECRET` | Bybit API Secret | Optional |
| `DATABASE_PATH` | SQLite database path | data/trading_bot.db |
| `LOG_LEVEL` | Logging level | INFO |
| `DEFAULT_TIMEFRAME` | Default chart timeframe | 1h |
| `AUTO_SIGNAL_INTERVAL` | Auto signal interval (seconds) | 300 |
| `MAX_DAILY_SIGNALS` | Maximum signals per day | 10 |
| `ENABLE_AUTO_SIGNALS` | Enable auto signals | true |
| `ENABLE_PRICE_ALERTS` | Enable price alerts | true |
| `DEFAULT_LANGUAGE` | Default bot language | en |

## Database Configuration

### Supabase (Recommended for Production)

The bot uses Supabase as its primary database for cloud-based PostgreSQL storage with:

- **Automatic failover**: Falls back to SQLite if Supabase is unavailable
- **Real-time capabilities**: Ready for future real-time features
- **Row Level Security**: All tables have RLS policies enabled
- **Automatic migrations**: Schema created via Supabase migrations

**Setup:**
1. Create a project at [supabase.com](https://supabase.com)
2. Copy your project URL and keys from Settings > API
3. Add to your `.env`:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   ```

### SQLite (Local Development)

If Supabase is not configured, the bot automatically falls back to SQLite:

```
DATABASE_PATH=data/trading_bot.db
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot |
| `/help` | Show help information |
| `/menu` | Open main menu |
| `/signal` | Get current signals |
| `/market` | Market information |
| `/chart` | Generate chart |
| `/price` | Get current price |
| `/alerts` | Manage alerts |
| `/settings` | Bot settings |
| `/profile` | Your profile |
| `/vip` | Premium membership |
| `/watchlist` | Manage watchlist |
| `/portfolio` | Track positions |
| `/report` | Performance reports |
| `/journal` | Trading journal |
| `/admin` | Admin panel (admins only) |

## Watchlist Commands

| Command | Description |
|---------|-------------|
| `/watchlist` | View your watchlist |
| `/watchlist add SYMBOL` | Add symbol to watchlist |
| `/watchlist remove SYMBOL` | Remove symbol |
| `/watchlist clear` | Clear watchlist |

## Portfolio Commands

| Command | Description |
|---------|-------------|
| `/portfolio` | View portfolio summary |
| `/portfolio list` | View all positions |
| `/portfolio add SYMBOL ENTRY SIZE [long/short]` | Add position |
| `/portfolio close ID EXIT_PRICE` | Close position |
| `/portfolio history` | View trade history |

## Report Commands

| Command | Description |
|---------|-------------|
| `/report` | Today's performance |
| `/report daily` | Daily report |
| `/report weekly` | Weekly report |
| `/report monthly` | Monthly report |
| `/report accuracy` | Signal accuracy report |

## Admin Commands

| Command | Description |
|---------|-------------|
| `/ban USER_ID` | Ban a user |
| `/unban USER_ID` | Unban a user |
| `/premium_add USER_ID` | Add premium to user |
| `/premium_remove USER_ID` | Remove premium |
| `/admin_add USER_ID` | Make user admin |
| `/autosignals_on` | Enable auto signals |
| `/autosignals_off` | Disable auto signals |

## API Integration

### Binance
```env
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

### Bybit
```env
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
```

## Technical Indicators

- **Moving Averages**: EMA (9, 20, 50, 200), SMA (20, 50, 100, 200)
- **Momentum**: RSI (14), MACD (12, 26, 9), Stochastic
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, Volume Analysis
- **Trend**: ADX, EMA Crossovers

## Candlestick Patterns

- Doji
- Hammer / Inverted Hammer
- Morning Star / Evening Star
- Three White Soldiers / Three Black Crows
- Engulfing Patterns
- Tweezer Tops / Bottoms
- Piercing Line / Dark Cloud Cover
- Shooting Star / Hanging Man

## Supported Trading Pairs

### Crypto
BTC/USDT, ETH/USDT, BNB/USDT, XRP/USDT, ADA/USDT, SOL/USDT, DOGE/USDT, DOT/USDT, AVAX/USDT, MATIC/USDT, LINK/USDT, LTC/USDT, UNI/USDT, ATOM/USDT, XLM/USDT

### Forex
EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, NZD/USD, EUR/GBP, EUR/JPY, GBP/JPY

## Security Best Practices

- Never commit `.env` file
- Use environment variables for secrets
- Enable rate limiting
- Validate all user inputs
- Enable database RLS policies
- Regular security audits

## License

This project is licensed under the MIT License.

## Disclaimer

**This bot is for educational purposes only. Trading cryptocurrencies and forex involves significant risk. Past performance is not indicative of future results. Always do your own research before making trading decisions.**

---

Built with Python 3.11 | aiogram 3.x | Docker Ready
