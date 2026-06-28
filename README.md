# Telegram AI Trading Assistant

Enterprise-grade Telegram bot for automated trading signals, market analysis, and technical indicators.

## Features

### Trading Signals
- Automated signal generation with technical analysis
- Manual signal posting by admins
- Real-time price alerts
- Signal performance tracking

### Market Analysis
- Support for Crypto and Forex markets
- Binance and Bybit integration
- Technical indicators: EMA, SMA, RSI, MACD, Bollinger Bands, ATR
- Candlestick pattern detection
- Support/Resistance level identification

### Bot Features
- Professional Telegram interface
- Multi-language support (English, Sinhala)
- Premium membership system
- User management with admin panel
- Price alerts and notifications
- Market scanner for opportunities
- Chart generation with matplotlib

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
| `BINANCE_API_KEY` | Binance API Key | Optional |
| `BINANCE_API_SECRET` | Binance API Secret | Optional |
| `BYBIT_API_KEY` | Bybit API Key | Optional |
| `BYBIT_API_SECRET` | Bybit API Secret | Optional |
| `CHANNEL_ID` | Main channel ID | Optional |
| `PREMIUM_CHANNEL_ID` | Premium channel ID | Optional |
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
| `/admin` | Admin panel (admins only) |

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

## Project Structure

```
trading-bot/
├── main.py                 # Application entry point
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── .env.example            # Environment template
├── database/
│   ├── __init__.py
│   ├── models.py           # Database models
│   └── repository.py       # Data access layer
├ handlers/
│   ├── __init__.py
│   ├── commands.py         # Command handlers
│   ├── callbacks.py        # Callback handlers
│   └── admin.py            # Admin handlers
├── market/
│   ├── __init__.py
│   ├── exchange.py         # Exchange clients
│   ├── indicators.py       # Technical indicators
│   ├── patterns.py         # Pattern detection
│   ├── scanner.py          # Market scanner
│   └── analysis.py         # Market analysis
├── charts/
│   ├── __init__.py
│   └── generator.py        # Chart generation
├── signals/
│   ├── __init__.py
│   ├── generator.py        # Signal generation
│   └── manager.py          # Signal management
├── services/
│   ├── __init__.py
│   ├── alerts.py           # Alert service
│   ├── notifications.py    # Notification service
│   └── scheduler.py        # Task scheduler
├── middlewares/
│   ├── __init__.py
│   ├── auth.py             # Authentication
│   ├── rate_limit.py       # Rate limiting
│   ├── logging.py          # Request logging
│   └── admin.py            # Admin check
├── keyboards/
│   ├── __init__.py
│   └── keyboards.py        # Inline keyboards
├── utils/
│   ├── __init__.py
│   ├── logger.py           # Logging setup
│   ├── helpers.py          # Helper functions
│   └── validators.py       # Input validation
├── data/                   # Database storage
├── logs/                   # Log files
└── charts/                 # Generated charts
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

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

**This bot is for educational purposes only. Trading cryptocurrencies and forex involves significant risk. Past performance is not indicative of future results. Always do your own research before making trading decisions.**

## Support

For support, please contact the bot administrator or open an issue on the repository.

---

Built with Python 3.11 | aiogram 3.x | Docker Ready
