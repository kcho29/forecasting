import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import nest_asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from collections import defaultdict
import dateutil.parser
import numpy as np

# Import the provided client library
from clients.clients import KalshiHttpClient, Environment

# Plotting style
sns.set_theme(style="darkgrid")

def init_client():
    try:
        nest_asyncio.apply()
        load_dotenv()
        env = Environment.PROD
        KEYID = os.getenv('KEYID')
        KEYFILE = os.getenv('KEYFILE')
        
        if not KEYID or not KEYFILE:
            # Fallback for testing if env vars not set in environment but file exists
            # You might want to adjust this based on actual setup
            pass

        try:
            with open(KEYFILE, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None
                )
        except FileNotFoundError:
            raise FileNotFoundError(f"Private key file not found at {KEYFILE}")
        except Exception as e:
            raise Exception(f"Error loading private key: {str(e)}")

        client = KalshiHttpClient(
            key_id=KEYID,
            private_key=private_key,
            environment=env
        )
        print("✅ Client initialized successfully.")
        return client
    except Exception as e:
        print(f"❌ Error initializing client: {e}")
        return None

client = init_client()

def get_nba_game_markets(limit=500):
    """
    Fetches recently settled NBA markets and filters for Daily Games.
    """
    print("Fetching settled NBA markets...")

    # Fetch a large batch to skip past the Season Futures
    response = client.get_markets(
        series_ticker="KXNBAGAME",
        status="settled",
        limit=limit
    )

    if 'markets' not in response:
        print("No markets found.")
        return []

    all_markets = response['markets']
    print(f"Fetched {len(all_markets)} total markets.")
    return all_markets

def analyze_event_scalp_potential(event_ticker, markets, candle_interval=1):
    # Select the first market to fetch data for
    market_a = markets[0]
    ticker_a = market_a['ticker']
    
    # 1. Determine End Time (Close/Expiration)
    end_ts = None
    for key in ['close_ts', 'expiration_ts', 'latest_expiration_ts', 'close_time']:
        if market_a.get(key):
            val = market_a[key]
            if isinstance(val, int):
                end_ts = val
                break
            elif isinstance(val, str):
                try:
                    end_ts = int(dateutil.parser.parse(val).timestamp())
                    break
                except:
                    continue
    
    if end_ts is None:
        return []

    # 2. Define Window: 2 days is enough for a daily game, stop looking 3 hours before game end
    start_ts = end_ts - (60 * 60 * 48)
    end_ts -= (60*60*3)

    try:
        # Fetch candlesticks for Market A
        candles_resp = client.get_market_candlesticks(
            series_ticker="KXNBAGAME",
            ticker=ticker_a,
            start_ts=start_ts,
            end_ts=end_ts,
            period_interval=candle_interval
        )
    except Exception:
        return []

    candles = candles_resp.get('candlesticks', [])
    if not candles:
        return []

    # Analyze Market A
    results = []
    
    # --- Market A Analysis ---
    first_candle = candles[0]
    yes_ask_a = first_candle.get('yes_ask', {}).get('close')
    yes_bid_a = first_candle.get('yes_bid', {}).get('close') # Need bid for inference
    
    if yes_ask_a is None:
        return []
        
    # Calculate stats for A
    open_price_a = yes_ask_a
    max_price_a = 0
    min_ask_a = 100 # For inferring B's max exit
    
    for candle in candles[1:]:
        bid = candle.get('yes_bid', {}).get('high')
        ask = candle.get('yes_ask', {}).get('low') # Low ask for B's max bid
        
        if bid and bid > max_price_a:
            max_price_a = bid
        
        if ask and ask < min_ask_a:
            min_ask_a = ask

    profit_a = max_price_a - open_price_a
    results.append({
        "ticker": ticker_a,
        "title": market_a['title'],
        "is_favorite": open_price_a > 50,
        "open_price": open_price_a,
        "max_exit_price": max_price_a,
        "profit_potential": profit_a,
        "win_5c": profit_a >= 5,
        "win_10c": profit_a >= 10,
        "result": market_a.get('result')
    })

    # --- Market B (Inferred) Analysis ---
    # Only if we have a second market
    if len(markets) > 1:
        market_b = markets[1]
        # Infer B from A
        # Entry B = 100 - Bid A (approx)
        # If Bid A is missing, we can't infer well.
        if yes_bid_a is not None:
            open_price_b = 100 - yes_bid_a
            # Max Exit B = 100 - Min Ask A
            # If Min Ask A is 100 (no data), then Max Exit B is 0.
            if min_ask_a == 100:
                 max_price_b = 0 # Conservative
            else:
                 max_price_b = 100 - min_ask_a
            
            profit_b = max_price_b - open_price_b
            
            results.append({
                "ticker": market_b['ticker'],
                "title": market_b['title'],
                "is_favorite": open_price_b > 50,
                "open_price": open_price_b,
                "max_exit_price": max_price_b,
                "profit_potential": profit_b,
                "win_5c": profit_b >= 5,
                "win_10c": profit_b >= 10,
                "result": market_b.get('result')
            })
            
    return results

def main():
    if not client:
        return

    # Fetch markets
    nba_markets = get_nba_game_markets()

    results = []
    if nba_markets:
        # Group by event
        events = defaultdict(list)
        for m in nba_markets:
            events[m['event_ticker']].append(m)
            
        print(f"Analyzing {len(events)} events (from {len(nba_markets)} markets)...")
        
        for event_ticker, mkts in events.items():
            # We only handle 2 markets per event for now (binary)
            if len(mkts) > 2:
                 mkts = mkts[:2] # Take first two
            
            event_results = analyze_event_scalp_potential(event_ticker, mkts)
            results.extend(event_results)

        df = pd.DataFrame(results)
        print(f"\\nAnalysis Complete!")
        print(f"Generated {len(df)} data points.")
        if not df.empty:
            print(df.head())
            
            # Save CSV
            df.to_csv("nba_analysis_results.csv", index=False)
            print("Results saved to nba_analysis_results.csv")

            # --- Visualizations ---
            # 1. Scatter Plot: Entry Price vs Max Exit Price (Favorites vs Underdogs)
            plt.figure(figsize=(12, 8))
            sns.scatterplot(data=df, x="open_price", y="max_exit_price", hue="is_favorite", style="win_5c", palette="viridis", s=100)
            
            plt.plot([0, 100], [0, 100], 'r--', label="Break Even", alpha=0.5)
            plt.plot([0, 95], [5, 100], 'g--', label="Target (+5¢)", alpha=0.5)
            
            plt.title("Momentum Scalping: Entry Price vs. Highest Exit Price")
            plt.xlabel("Entry Price (Cents)")
            plt.ylabel("Max Exit Price (Cents)")
            plt.legend(title="Favorite / Win")
            plt.savefig("scatter_plot.png")
            print("Saved scatter_plot.png")
            
            # 2. Win Rate Bar Chart (Favorites vs Underdogs)
            # Calculate win rates
            win_rates = df.groupby('is_favorite')[['win_5c', 'win_10c']].mean().reset_index()
            win_rates_melted = win_rates.melt(id_vars='is_favorite', var_name='Target', value_name='Win Rate')
            
            plt.figure(figsize=(8, 6))
            sns.barplot(data=win_rates_melted, x="Target", y="Win Rate", hue="is_favorite", palette="Blues_d")
            plt.ylim(0, 1.0)
            plt.title("Win Rate for Scalping Targets")
            plt.ylabel("Percentage Success")
            plt.savefig("win_rates.png")
            print("Saved win_rates.png")

            # 3. Distribution of Potential Profit
            plt.figure(figsize=(14, 6))
            sns.histplot(data=df, x='profit_potential', hue='is_favorite', discrete=True, kde=True, element="step")
            plt.axvline(0, color='red', linestyle='--', label="Break Even")
            plt.title("Distribution of Max Potential Profit (Cents)")
            plt.xlabel("Max Profit (Peak Bid - Entry Ask)")
            
            min_val = int(df['profit_potential'].min())
            max_val = int(df['profit_potential'].max())
            plt.xticks(np.arange(min_val, max_val + 1, 1), rotation=90)
            
            plt.legend()
            plt.tight_layout()
            plt.savefig("profit_distribution.png")
            print("Saved profit_distribution.png")

    else:
        print("No markets to analyze.")

if __name__ == "__main__":
    main()
