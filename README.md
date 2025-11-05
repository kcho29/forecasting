# Prediction Pod

A lightweight Python client for interacting with the Kalshi prediction markets API.

---

## Quick Start

### Prerequisites
- Python 3.8+
- Kalshi API credentials ([Get them here](https://docs.kalshi.com/getting_started/api_keys))

### Installation

1. Clone the repository
2. Install dependencies:
```bash
   pip install requests cryptography python-dotenv websockets plotly
```

### Configuration

Create a `.env` file in your project root with your Kalshi credentials:
```env
KEYID=your-api-key-id
KEYFILE=kalshi.key
DEMOID=your-demo-id
DEMOFILE=demo.key
```

**Note:** The `KEYFILE` should point to your PEM-encoded RSA private key file.

#### Private Key Format

Your `kalshi.key` file should look like this:
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAyourprivatekeycontentgoeshere...
(multiple lines of base64-encoded key data)
...
-----END RSA PRIVATE KEY-----
```

You'll receive this file from Kalshi when generating your API keys.

#### Security Best Practices

- **Never commit** `.env` files or `.key` files to version control
- Use appropriate file permissions: `chmod 600 kalshi.key` (Unix/Mac)
- Add these entries to your `.gitignore`:
```gitignore
# Secrets
.env
*.key

# Python
__pycache__/
*.py[cod]
.ipynb_checkpoints
```

---

## Usage

### Initialize the Client
```python
from kalshi_client import KalshiHttpClient, Environment
import os
from cryptography.hazmat.primitives import serialization

# Load credentials
key_id = os.getenv('KEYID')
with open(os.getenv('KEYFILE'), 'rb') as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

# Initialize client (use Environment.DEMO for testing)
api = KalshiHttpClient(key_id, private_key, environment=Environment.PROD)
```

---

## API Reference

### Exchange Operations

Monitor exchange status and announcements:
```python
api.get_exchange_status()                    # Current trading status
api.get_exchange_schedule()                  # Trading hours
api.get_exchange_announcements(limit=10)     # Latest announcements
```

---

### Portfolio Management

#### Account Information
```python
api.get_balance()                            # Available balance
api.get_total_market_exposure()              # Total capital at risk
```

#### Positions
```python
api.get_positions(settlement_status='unsettled')     # All open positions
api.get_exposed_positions()                          # Positions with non-zero exposure
api.get_settlements(limit=50)                        # Settlement history
```

#### Order Management

**Placing Orders:**
```python
api.create_order(
    action='buy',
    client_order_id='my-order-1',
    count=10,
    side='yes',
    ticker='KXBTC-25DEC31-T100K',
    type='limit',
    yes_price=65
)
```

**Managing Orders:**
```python
api.get_orders(status='resting')             # View active orders
api.get_order(order_id='abc123')             # Get specific order
api.cancel_order(order_id='abc123')          # Cancel order
api.amend_order(order_id='abc123', count=5)  # Modify order
api.decrease_order(order_id='abc123', reduce_by=5)  # Reduce size
```

**Batch Operations:**
```python
api.create_batched_orders(orders=[{...}, {...}])   # Place multiple orders
api.cancel_batched_orders(ids=['id1', 'id2'])      # Cancel multiple orders
```

#### Risk Management with Order Groups
```python
# Create order group with contract limit
group = api.create_order_group(contracts_limit=100)
group_id = group['order_group']['order_group_id']

# View and manage groups
api.get_order_groups()                       # List all groups
api.get_order_group(order_group_id='xyz')    # Get specific group
api.reset_order_group(order_group_id='xyz')  # Reset fill counter
api.delete_order_group(order_group_id='xyz') # Delete group
```

#### Order Queue Information
```python
api.get_orders_queue_positions()             # Queue position for all orders
api.get_order_queue_position(order_id='abc') # Queue position for specific order
```

#### Fill History
```python
api.get_fills(ticker='KXBTC-25DEC31-T100K')  # Recent fills for a market
```

---

### Market Data

#### Basic Queries
```python
api.get_market(ticker='KXBTC-25DEC31-T100K')          # Single market
api.get_markets(series_ticker='KXBTC', status='open') # Filter markets
api.get_market_orderbook(ticker='KXBTC-25DEC31-T100K') # Order book
api.get_trades(ticker='KXBTC-25DEC31-T100K', limit=100) # Trade history
```

#### Advanced Filtering
```python
# Get markets and filter by field
markets_data = api.get_markets(series_ticker='KXHIGHMIA')
filtered = api.filter_markets(markets_data, 'strike_type', 'between')

# Combined query and filter
results = api.get_markets_by_field('status', 'open', series_ticker='KXBTC')

# Create ticker lookup dictionary
ticker_map = api.get_ticker_map(series_ticker='KXBTC')
market = ticker_map['KXBTC-25DEC31-T100K']
```

---

### Events
```python
api.get_events()                                  # List all events
api.get_event(event_ticker='KXBTC-25DEC31')      # Event details
api.get_event_metadata(event_ticker='KXBTC-25DEC31')  # Additional metadata
api.get_multivariate_events(status='open')        # Mutually exclusive events
```

#### Event Price History
```python
api.get_event_candlesticks(
    series_ticker='KXBTC',
    event_ticker='KXBTC-25DEC31',
    start_ts=1704067200,
    end_ts=1735689600,
    period_interval=60
)

api.get_event_forecast_percentile_history(
    series_ticker='KXBTC',
    event_ticker='KXBTC-25DEC31'
)
```

---

### Series
```python
api.get_all_series(limit=100)                # List all series
api.get_series(series_ticker='KXBTC')        # Single series details
```

#### Market Candlesticks
```python
api.get_market_candlesticks(
    series_ticker='KXBTC',
    ticker='KXBTC-25DEC31-T100K',
    start_ts=1704067200,
    end_ts=1735689600,
    period_interval=60
)
```

---

### Communications
```python
api.get_quotes(market_ticker='KXBTC-25DEC31-T100K')  # Market quotes
```

---

### Live Data

Real-time event data (elections, sports, etc.):
```python
# Single milestone
api.get_live_data_milestone(
    data_type='election',
    milestone_id='milestone-123'
)

# Multiple milestones in batch
api.get_live_data_batch(
    milestone_ids=['m1', 'm2'],
    data_types=['election', 'votes']
)
```

---

### Visualization & Analytics

#### Interactive Price Charts
```python
fig = api.plot_market_candlesticks(
    ticker='KXBTC-25DEC31-T100K',
    days=7,
    chart_type='mid_price',      # Options: 'mid_price', 'bid_ask', 'spread', 'volume', 'candlestick'
    period_interval=60,
    show=True,                   # Display in browser
    save_path='chart.html'       # Save to file
)
```

**Chart Types:**
- `mid_price` - Mid-market price over time
- `bid_ask` - Bid and ask prices
- `spread` - Bid-ask spread
- `volume` - Price with volume bars
- `candlestick` - OHLC candlestick chart

#### Trading Calculations

**Expected Value:**
```python
ev = api.calculate_expected_value(
    yes_price=65,                # Current price in cents
    true_probability=0.75,       # Your probability estimate
    contract_count=10
)
```

**Kelly Criterion Position Sizing:**
```python
kelly_size = api.calculate_kelly_criterion(
    yes_price=65,
    true_probability=0.75,
    bankroll=10000,              # Your balance in cents
    adjustment_factor=0.5        # Use half-Kelly for safety (default)
)
```

---

## Common Usage Patterns

### Finding and Filtering Markets
```python
# Get all open markets in a series
markets = api.get_markets(series_ticker='KXBTC', status='open')

# Group markets by strike type
by_strike = api.filter_markets(markets, 'strike_type')
between_markets = by_strike['between']
less_markets = by_strike['less']

# Create lookup dictionary for fast access
ticker_map = api.get_ticker_map(series_ticker='KXBTC')
specific_market = ticker_map['KXBTC-25DEC31-T100K']
```

### Managing Positions
```python
# Get all positions with exposure
positions = api.get_exposed_positions(settlement_status='unsettled')

# Calculate total exposure across all positions
total_exposure = api.get_total_market_exposure()

# Get recent fills with time filter
fills = api.get_fills(min_ts=1704067200, limit=100)
```

### Placing Orders with Risk Management
```python
# Create order group for risk limit (max 100 contracts filled across all orders)
group = api.create_order_group(contracts_limit=100)
group_id = group['order_group']['order_group_id']

# Place multiple orders in the group
api.create_batched_orders(orders=[
    {
        'ticker': 'KXBTC-25DEC31-T100K',
        'client_order_id': 'order-1',
        'side': 'yes',
        'action': 'buy',
        'count': 50,
        'type': 'limit',
        'yes_price': 65,
        'order_group_id': group_id
    },
    {
        'ticker': 'KXBTC-25DEC31-T150K',
        'client_order_id': 'order-2',
        'side': 'yes',
        'action': 'buy',
        'count': 50,
        'type': 'limit',
        'yes_price': 35,
        'order_group_id': group_id
    }
])
```

### Analyzing Market History
```python
# Visualize price history with volume
api.plot_market_candlesticks(
    ticker='KXBTC-25DEC31-T100K',
    days=30,
    chart_type='volume',
    period_interval=60
)

# Get detailed trade history
trades = api.get_trades(
    ticker='KXBTC-25DEC31-T100K',
    min_ts=1704067200,
    limit=1000
)
```

---

## Technical Details

### Rate Limiting
- Automatic rate limiting: 75ms between requests
- All authentication and request signing handled automatically

### Error Handling

All API methods raise `HTTPError` on non-2xx responses. Always wrap calls in try-except:
```python
try:
    market = api.get_market(ticker='INVALID-TICKER')
except requests.exceptions.HTTPError as e:
    print(f"API error: {e.response.status_code} - {e.response.text}")
```

### Timestamps

All timestamp parameters use Unix time in seconds:
```python
from datetime import datetime

# Convert datetime to Unix timestamp
start_time = datetime(2024, 1, 1)
start_ts = int(start_time.timestamp())

# Use in API call
api.get_market_candlesticks(
    series_ticker='KXBTC',
    ticker='KXBTC-25DEC31-T100K',
    start_ts=start_ts,
    end_ts=int(datetime.now().timestamp()),
    period_interval=60
)
```

### Price Units

All prices are in **cents** (not dollars):
- Market price of 65¢ = 65% probability
- Order for 10 contracts at 65¢ = $6.50 total cost
- Winning contract pays 100¢ = $1.00

---

## WebSocket Support

For real-time market data streaming:
```python
from kalshi_client import KalshiWebSocketClient
import asyncio

# Initialize WebSocket client
ws_client = KalshiWebSocketClient(key_id, private_key, environment=Environment.PROD)

# Connect and subscribe
async def main():
    await ws_client.connect()

asyncio.run(main())
```

**Available subscriptions:**
- `subscribe_to_tickers()` - All market tickers
- `subscribe_to_specific_tickers(tickers)` - Specific markets
- `subscribe_to_orderbook(ticker)` - Order book updates
- `subscribe_to_trades(ticker)` - Trade feed

---

## Examples

Check out the `base/get_data.ipynb` notebook for complete working examples.

---

## Support

- [Kalshi API Documentation](https://docs.kalshi.com)
- [Kalshi Support](https://kalshi.com/support)

---

## License

MIT License - See LICENSE file for details
