# Prediction Pod — Quick Start

Summary
- Small client that talks to Kalshi via a local client package and example notebook (base/get_data.ipynb).

Prerequisites
- Python 3.8+ (Windows)
- Git (optional)

API KEY
- Get from Kalshi - https://docs.kalshi.com/getting_started/api_keys

Environment (.env)
- Place a .env file in the same folder that your code loads from (this project uses `base/.env` in the repo example).
- Required variables (example values shown — do NOT commit real secrets):

  KEYID='your-api-key-id'
  KEYFILE='kalshi.key'       # path to PEM private key file used to sign 
  DEMOID='your-demo-id'      # optional demo account id
  DEMOFILE='demo.key'        # optional demo private key path

Notes on formatting
- Values can be quoted or unquoted; python-dotenv will load them. Use relative paths (relative to project root) or absolute paths for KEYFILE/DEMOFILE.

kalshi.key (private key) requirements
- The client expects a PEM-encoded private key readable as bytes and loadable via cryptography.hazmat.primitives.serialization.load_pem_private_key(...).
- You get one from Kalshi and should be formatted like: 
-----BEGIN RSA PRIVATE KEY-----
blah balh balh akdjflkasjdklfas
asdfdsjfalksdjfklsadjlkfjaskldf
asdfasdklfjlkasdfjkladsjfsdsssd
asdadskjflkasjdfkladsjklfjadskl
fasakdjfhkjsdfjkajlkfsdfsfdsfds
sfdasdfjalksdjfklsjkdfljdkjfkdj
-----END RSA PRIVATE KEY-----

Security
- Treat KEYID and key files as secrets. Do not push them to public repositories. Use appropriate OS file permissions and .gitignore entries.

---

## API Client Functionality

The `KalshiHttpClient` (typically instantiated as `api`) provides comprehensive access to the Kalshi prediction market API. Below is an overview of available methods organized by category.

### Initialization
```python
from kalshi_client import KalshiHttpClient, Environment
import os
from cryptography.hazmat.primitives import serialization

# Load credentials
key_id = os.getenv('KEYID')
with open(os.getenv('KEYFILE'), 'rb') as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

# Initialize client
api = KalshiHttpClient(key_id, private_key, environment=Environment.PROD)
```

### Exchange Methods
Get exchange status, schedule, and announcements:
```python
api.get_exchange_status()                                    # Current exchange status
api.get_exchange_schedule()                                  # Trading schedule
api.get_exchange_announcements(limit=10)                    # Recent announcements
```

### Portfolio Methods
Manage your account, orders, and positions:
```python
# Account information
api.get_balance()                                           # Current balance
api.get_total_market_exposure()                             # Total exposure across positions

# Positions
api.get_positions(settlement_status='unsettled')            # All positions
api.get_exposed_positions()                                 # Only positions with non-zero exposure
api.get_settlements(limit=50)                               # Settlement history

# Orders
api.get_orders(status='resting')                            # Filter by status
api.get_order(order_id='abc123')                            # Get specific order
api.create_order(                                           # Place new order
    action='buy',
    client_order_id='my-order-1',
    count=10,
    side='yes',
    ticker='KXBTC-25DEC31-T100K',
    type='limit',
    yes_price=65
)
api.cancel_order(order_id='abc123')                         # Cancel order
api.amend_order(order_id='abc123', count=5, ...)           # Modify order
api.decrease_order(order_id='abc123', reduce_by=5)         # Reduce order size

# Batch operations
api.create_batched_orders(orders=[{...}, {...}])           # Submit multiple orders
api.cancel_batched_orders(ids=['id1', 'id2'])              # Cancel multiple orders

# Order groups (risk management)
api.create_order_group(contracts_limit=100)                 # Create group with limit
api.get_order_groups()                                      # List all groups
api.reset_order_group(order_group_id='xyz')                 # Reset fill counter

# Queue positions
api.get_orders_queue_positions()                            # All order queue positions
api.get_order_queue_position(order_id='abc123')            # Specific order position

# Fills
api.get_fills(ticker='KXBTC-25DEC31-T100K')                # Trade fills
```

### Market Methods
Query and filter markets:
```python
# Basic market queries
api.get_market(ticker='KXBTC-25DEC31-T100K')               # Single market details
api.get_markets(series_ticker='KXBTC', status='open')      # Filter markets
api.get_market_orderbook(ticker='KXBTC-25DEC31-T100K')     # Current orderbook
api.get_trades(ticker='KXBTC-25DEC31-T100K', limit=100)    # Recent trades

# Advanced filtering
markets_data = api.get_markets(series_ticker='KXHIGHMIA')
api.filter_markets(markets_data, 'strike_type', 'between')  # Filter by field
api.get_markets_by_field('status', 'open', series_ticker='KXBTC')  # Combined query+filter

# Ticker mapping
ticker_map = api.get_ticker_map(series_ticker='KXBTC')      # Dict of ticker -> market data
market = ticker_map['KXBTC-25DEC31-T100K']                  # Direct access by ticker
```

### Event Methods
Query events and their metadata:
```python
api.get_events()                                            # List all events
api.get_event(event_ticker='KXBTC-25DEC31')                # Single event details
api.get_event_metadata(event_ticker='KXBTC-25DEC31')       # Additional metadata
api.get_multivariate_events(status='open')                  # Mutually exclusive events
api.get_event_candlesticks(                                 # Price history for event
    series_ticker='KXBTC',
    event_ticker='KXBTC-25DEC31',
    start_ts=1704067200,
    end_ts=1735689600,
    period_interval=60
)
api.get_event_forecast_percentile_history(                  # Forecast evolution
    series_ticker='KXBTC',
    event_ticker='KXBTC-25DEC31'
)
```

### Series Methods
Query market series:
```python
api.get_all_series(limit=100)                               # List all series
api.get_series(series_ticker='KXBTC')                       # Single series details
api.get_market_candlesticks(                                # Price history for market
    series_ticker='KXBTC',
    ticker='KXBTC-25DEC31-T100K',
    start_ts=1704067200,
    end_ts=1735689600,
    period_interval=60
)
```

### Communications Methods
```python
api.get_quotes(market_ticker='KXBTC-25DEC31-T100K')        # Market quotes
```

### Live Data Methods
Real-time event data (elections, etc.):
```python
api.get_live_data_milestone(                                # Single milestone
    data_type='election',
    milestone_id='milestone-123'
)
api.get_live_data_batch(                                    # Multiple milestones
    milestone_ids=['m1', 'm2'],
    data_types=['election', 'votes']
)
```

### Visualization & Analysis Helpers
Built-in charting and calculation utilities:
```python
# Interactive price charts
fig = api.plot_market_candlesticks(
    ticker='KXBTC-25DEC31-T100K',
    days=7,
    chart_type='mid_price',      # Options: 'mid_price', 'bid_ask', 'spread', 'volume', 'candlestick'
    period_interval=60,
    show=True,                   # Display in browser
    save_path='chart.html'       # Save to file
)

# Trading calculations
ev = api.calculate_expected_value(
    yes_price=65,                # Current price in cents
    true_probability=0.75,       # Your estimate
    contract_count=10
)

kelly_size = api.calculate_kelly_criterion(
    yes_price=65,
    true_probability=0.75,
    bankroll=10000,              # Your balance in cents
    adjustment_factor=0.5        # Use half-Kelly for safety
)
```

### Common Usage Patterns

**Finding and filtering markets:**
```python
# Get all open markets in a series
markets = api.get_markets(series_ticker='KXBTC', status='open')

# Group markets by strike type
by_strike = api.filter_markets(markets, 'strike_type')
between_markets = by_strike['between']
less_markets = by_strike['less']

# Create lookup dictionary
ticker_map = api.get_ticker_map(series_ticker='KXBTC')
specific_market = ticker_map['KXBTC-25DEC31-T100K']
```

**Managing positions:**
```python
# Get all positions with exposure
positions = api.get_exposed_positions(settlement_status='unsettled')

# Calculate total exposure
total_exposure = api.get_total_market_exposure()

# Get recent fills
fills = api.get_fills(min_ts=1704067200, limit=100)
```

**Placing orders with risk management:**
```python
# Create order group for risk limit
group = api.create_order_group(contracts_limit=100)
group_id = group['order_group']['order_group_id']

# Place orders in the group
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

**Analyzing market history:**
```python
# Get and visualize price history
api.plot_market_candlesticks(
    ticker='KXBTC-25DEC31-T100K',
    days=30,
    chart_type='volume',
    period_interval=60
)

# Get trade history
trades = api.get_trades(
    ticker='KXBTC-25DEC31-T100K',
    min_ts=1704067200,
    limit=1000
)
```

### Rate Limiting
The client includes automatic rate limiting (100ms between requests). All methods handle authentication and request signing automatically.

### Error Handling
All API methods raise `HTTPError` on non-2xx responses. Wrap calls in try-except blocks:
```python
try:
    market = api.get_market(ticker='INVALID-TICKER')
except requests.exceptions.HTTPError as e:
    print(f"API error: {e}")
```

