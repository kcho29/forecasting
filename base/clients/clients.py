import requests
import base64
import time
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
import json

from requests.exceptions import HTTPError

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

import websockets

class Environment(Enum):
    DEMO = "demo"
    PROD = "prod"

class KalshiBaseClient:
    """Base client class for interacting with the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ):
        """Initializes the client with the provided API key and private key.

        Args:
            key_id (str): Your Kalshi API key ID.
            private_key (rsa.RSAPrivateKey): Your RSA private key.
            environment (Environment): The API environment to use (DEMO or PROD).
        """
        self.key_id = key_id
        self.private_key = private_key
        self.environment = environment
        self.last_api_call = datetime.now()

        if self.environment == Environment.DEMO:
            self.HTTP_BASE_URL = "https://demo-api.kalshi.co"
            self.WS_BASE_URL = "wss://demo-api.kalshi.co"
        elif self.environment == Environment.PROD:
            self.HTTP_BASE_URL = "https://api.elections.kalshi.com"
            self.WS_BASE_URL = "wss://api.elections.kalshi.com"
        else:
            raise ValueError("Invalid environment")

    def request_headers(self, method: str, path: str) -> Dict[str, Any]:
        """Generates the required authentication headers for API requests."""
        current_time_milliseconds = int(time.time() * 1000)
        timestamp_str = str(current_time_milliseconds)

        # Remove query params from path
        path_parts = path.split('?')

        msg_string = timestamp_str + method + path_parts[0]
        signature = self.sign_pss_text(msg_string)

        headers = {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }
        return headers

    def sign_pss_text(self, text: str) -> str:
        """Signs the text using RSA-PSS and returns the base64 encoded signature."""
        message = text.encode('utf-8')
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH
                ),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except InvalidSignature as e:
            raise ValueError("RSA sign PSS failed") from e

class KalshiHttpClient(KalshiBaseClient):
    """Client for handling HTTP connections to the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ):
        super().__init__(key_id, private_key, environment)
        self.host = self.HTTP_BASE_URL
        self.base = "/trade-api/v2"
        self.exchange_url = self.base + "/exchange"
        self.markets_url = self.base + "/markets"
        self.portfolio_url = self.base + "/portfolio"
        self.events_url = self.base + "/events"
        self.series_url = self.base + "/series"
        self.communications_url = self.base + "/communications"
        self.search_url = self.base + "/search"
        self.structured_targets_url = self.base + "/structured-targets"
        self.milestones_url = self.base + "/milestones"
        self.collections_url = self.base + "/multivariate_event_collections"


    def rate_limit(self) -> None:
        """Built-in rate limiter to prevent exceeding API rate limits."""
        THRESHOLD_IN_MILLISECONDS = 100
        now = datetime.now()
        threshold_in_microseconds = 1000 * THRESHOLD_IN_MILLISECONDS
        threshold_in_seconds = THRESHOLD_IN_MILLISECONDS / 1000
        if now - self.last_api_call < timedelta(microseconds=threshold_in_microseconds):
            time.sleep(threshold_in_seconds)
        self.last_api_call = datetime.now()

    def raise_if_bad_response(self, response: requests.Response) -> None:
        """Raises an HTTPError if the response status code indicates an error."""
        if response.status_code not in range(200, 299):
            response.raise_for_status()

    # ==================== HTTP Methods ====================

    def post(self, path: str, body: dict) -> Any:
        """Performs an authenticated POST request to the Kalshi API."""
        self.rate_limit()
        response = requests.post(
            self.host + path,
            json=body,
            headers=self.request_headers("POST", path)
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Performs an authenticated GET request to the Kalshi API."""
        self.rate_limit()
        response = requests.get(
            self.host + path,
            headers=self.request_headers("GET", path),
            params=params
        )
        self.raise_if_bad_response(response)
        return response.json()

    def delete(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Performs an authenticated DELETE request to the Kalshi API."""
        self.rate_limit()
        response = requests.delete(
            self.host + path,
            headers=self.request_headers("DELETE", path),
            params=params
        )
        self.raise_if_bad_response(response)
        return response.json()

    # ==================== Exchange Methods ====================

    def get_exchange_status(self) -> Dict[str, Any]:
        """Retrieves the exchange status."""
        return self.get(self.exchange_url + "/status")
    
    def get_exchange_schedule(self) -> Dict[str, Any]:
        """Retrieves the exchange schedule."""
        return self.get(self.exchange_url + '/schedule')
    
    def get_exchange_announcements(self, cursor: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Retrieves exchange announcements."""
        params = {
            'cursor': cursor,
            'limit': limit,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.exchange_url + '/announcements', params=params)
    
    def get_exchange_announcement(self) -> Dict[str, Any]:
        """Retrieves a specific exchange announcement by its ID."""
        return self.get(self.exchange_url + '/announcements/')

    # ==================== Portfolio Methods ====================

    def get_balance(self) -> Dict[str, Any]:
        """Retrieves the account balance."""
        return self.get(self.portfolio_url + '/balance')

    def get_positions(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        count_filter: Optional[str] = None,
        settlement_status: Optional[str] = None,
        ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        ) -> Dict[str, Any]:
        """
        Retrieves all market positions for the member with optional filters.

        Args:
            cursor (Optional[str]): Pointer to the next page of records for pagination.
            limit (Optional[int]): Number of results per page (1 to 1000, defaults to 100 if not provided).
            count_filter (Optional[str]): Comma-separated list to restrict positions to those with non-zero fields.
                                        Acceptable values: position, total_traded, resting_order_count.
            settlement_status (Optional[str]): Settlement status of the markets to return.
                                            Defaults to "unsettled". Other options: "all", "settled".
            ticker (Optional[str]): Ticker of the desired positions.
            event_ticker (Optional[str]): Event ticker of the desired positions.

        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        params = {
            "cursor": cursor,
            "limit": limit,
            "count_filter": count_filter,
            "settlement_status": settlement_status,
            "ticker": ticker,
            "event_ticker": event_ticker,
        }
        # Remove keys with None values to avoid sending unnecessary parameters.
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/positions', params=params)

    def get_fills(
    self,
    ticker: Optional[str] = None,
    order_id: Optional[str] = None,
    min_ts: Optional[int] = None,
    max_ts: Optional[int] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves all fills for the member with optional filters.

        Args:
            ticker (Optional[str]): Restricts the response to trades in a specific market.
            order_id (Optional[str]): Restricts the response to trades related to a specific order.
            min_ts (Optional[int]): Restricts the response to trades after this timestamp.
            max_ts (Optional[int]): Restricts the response to trades before this timestamp.
            limit (Optional[int]): Number of results per page (1 to 1000, defaults to 100 if not provided).
            cursor (Optional[str]): Cursor for pagination from a previous request.

        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        params = {
            "ticker": ticker,
            "order_id": order_id,
            "min_ts": min_ts,
            "max_ts": max_ts,
            "limit": limit,
            "cursor": cursor,
        }
        # Remove keys with None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/fills', params=params)

    def get_orders(
        self,
        ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
        status: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves all orders for the member with optional filters.

        Args:
            ticker (Optional[str]): Restricts the response to orders in a single market.
            event_ticker (Optional[str]): Restricts the response to orders in a single event.
            min_ts (Optional[int]): Restricts the response to orders after this Unix timestamp.
            max_ts (Optional[int]): Restricts the response to orders before this Unix timestamp.
            status (Optional[str]): Restricts the response to orders with a certain status (resting, canceled, or executed).
            cursor (Optional[str]): Cursor for pagination from a previous request.
            limit (Optional[int]): Number of results per page (1 to 1000, defaults to 100 if not provided).

        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        params = {
            "ticker": ticker,
            "event_ticker": event_ticker,
            "min_ts": min_ts,
            "max_ts": max_ts,
            "status": status,
            "cursor": cursor,
            "limit": limit,
        }
        # Remove keys with None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/orders', params=params)
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Retrieves a specific order by its ID."""
        return self.get(self.portfolio_url + '/orders/' + order_id)

    def create_order(
    self,
    action: str,
    client_order_id: str,
    count: int,
    side: str,
    ticker: str,
    type: str,
    buy_max_cost: Optional[int] = None,
    expiration_ts: Optional[int] = None,
    no_price: Optional[int] = None,
    post_only: Optional[bool] = None,
    sell_position_floor: Optional[int] = None,
    yes_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Submits an order for a market.

        Args:
            action (str): Specifies if this is a buy or sell order.
            client_order_id (str): Unique identifier for the order.
            count (int): Number of contracts to be bought or sold.
            side (str): Specifies if this is a 'yes' or 'no' order.
            ticker (str): The ticker of the market the order will be placed in.
            type (str): Specifies if this is a "market" or "limit" order.
            buy_max_cost (Optional[int]): For market orders when action is buy, the maximum cents to be spent.
            expiration_ts (Optional[int]): Expiration time of the order, in Unix seconds.
                                    If not supplied, the order remains active until explicitly cancelled (GTC).
                                    If in the past, the order behaves as Immediate-or-Cancel (IOC).
            no_price (Optional[int]): Price for the No side of the trade, in cents.
                                    Exactly one of yes_price and no_price must be provided.
            post_only (Optional[bool]): If True, the order is rejected if it crosses the spread and executes.
            sell_position_floor (Optional[int]): Prevents flipping position for a market order if set to 0.
            yes_price (Optional[int]): Price for the Yes side of the trade, in cents.
                                    Exactly one of yes_price and no_price must be provided.

        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        order_data = {
            "action": action,
            "client_order_id": client_order_id,
            "count": count,
            "side": side,
            "ticker": ticker,
            "type": type,
            "buy_max_cost": buy_max_cost,
            "expiration_ts": expiration_ts,
            "no_price": no_price,
            "post_only": post_only,
            "sell_position_floor": sell_position_floor,
            "yes_price": yes_price,
        }
        # Remove keys with None values to avoid sending unnecessary fields
        order_data = {k: v for k, v in order_data.items() if v is not None}
        return self.post(self.portfolio_url + '/orders', body=order_data)
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancels a specific order by its ID."""
        return self.delete(self.portfolio_url + '/orders/' + order_id)
    
    def amend_order(
    self,
    order_id: str,
    action: str,
    client_order_id: str,
    count: int,
    side: str,
    ticker: str,
    updated_client_order_id: str,
    no_price: Optional[int] = None,
    yes_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Amends an existing order's maximum fillable contracts and/or price.

        Args:
            order_id (str): ID of the order to be amended.
            action (str): Specifies if this is a buy or sell order (cannot be amended).
            client_order_id (str): The original client order ID.
            count (int): Number of contracts to be bought or sold (max fillable contracts).
            side (str): Specifies if this is a 'yes' or 'no' order (cannot be amended).
            ticker (str): The market ticker for the order (cannot be amended).
            updated_client_order_id (str): New client order ID for the amended order.
            no_price (Optional[int]): Price of the No side of the trade, in cents.
                                    Exactly one of yes_price and no_price must be provided.
            yes_price (Optional[int]): Price of the Yes side of the trade, in cents.
                                    Exactly one of yes_price and no_price must be provided.

        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        # Ensure exactly one of yes_price or no_price is provided
        if (yes_price is None and no_price is None) or (yes_price is not None and no_price is not None):
            raise ValueError("Exactly one of yes_price or no_price must be provided.")
        
        amend_data = {
            "action": action,
            "client_order_id": client_order_id,
            "count": count,
            "side": side,
            "ticker": ticker,
            "updated_client_order_id": updated_client_order_id,
            "no_price": no_price,
            "yes_price": yes_price,
        }
        # Remove keys with None values to avoid sending unnecessary fields
        amend_data = {k: v for k, v in amend_data.items() if v is not None}
        return self.post(self.portfolio_url + f"/orders/{order_id}/amend", body=amend_data)

    def decrease_order(
        self,
        order_id: str,
        reduce_by: Optional[int] = None,
        reduce_to: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Decreases the number of contracts in an existing order.

        Args:
            order_id (str): ID of the order to be decreased.
            reduce_by (Optional[int]): Number of contracts to decrease the order's count by.
                                    One of reduce_by or reduce_to must be provided.
            reduce_to (Optional[int]): Number of contracts to decrease the order to.
                                    One of reduce_by or reduce_to must be provided.
        
        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        # Ensure exactly one of reduce_by or reduce_to is provided.
        if (reduce_by is None and reduce_to is None) or (reduce_by is not None and reduce_to is not None):
            raise ValueError("Exactly one of reduce_by or reduce_to must be provided.")
        
        payload = {
            "reduce_by": reduce_by,
            "reduce_to": reduce_to,
        }
        # Remove keys with None values to avoid sending unnecessary fields.
        payload = {k: v for k, v in payload.items() if v is not None}
        
        endpoint = f"{self.portfolio_url}/orders/{order_id}/decrease"
        return self.post(endpoint, body=payload)


    
    def get_exposed_positions(self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        count_filter: Optional[str] = None,
        settlement_status: Optional[str] = None,
        ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        ) -> Dict[str, Any]:
        """
        Retrieves all market positions with non-zero market exposure for the member with optional filters.
        Args:
            cursor (Optional[str]): Pointer to the next page of records for pagination.
            limit (Optional[int]): Number of results per page (1 to 1000, defaults to 100 if not provided).
            count_filter (Optional[str]): Comma-separated list to restrict positions to those with non-zero fields.
                                        Acceptable values: position, total_traded, resting_order_count.
            settlement_status (Optional[str]): Settlement status of the markets to return.
                                            Defaults to "unsettled". Other options: "all", "settled".
            ticker (Optional[str]): Ticker of the desired positions.
            event_ticker (Optional[str]): Event ticker of the desired positions.
        """
        portfolio_data = self.get_positions(cursor, limit, count_filter, settlement_status, ticker, event_ticker)
        filtered_positions = [
            position for position in portfolio_data.get("market_positions", [])
            if position.get("market_exposure", 0) != 0
        ]
        return {"cursor": portfolio_data.get("cursor", ""), "market_positions": filtered_positions}
    
    def get_order_groups(self) -> Dict[str, Any]:
        """
        Retrieves all order groups for the member.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing all order groups.
        """
        return self.get(self.portfolio_url + '/order_groups')
    
    def get_order_group(self, order_group_id: str) -> Dict[str, Any]:
        """
        Retrieves a specific order group by its ID.
        
        Args:
            order_group_id (str): The ID of the order group to retrieve.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing the order group details.
        """
        return self.get(self.portfolio_url + '/order_groups/' + order_group_id)

    def create_order_group(self, contracts_limit: int) -> Dict[str, Any]:
        """
        Creates a new order group with a specified contracts limit.
        
        Order groups allow you to enforce risk limits across multiple orders by setting
        a maximum number of contracts that can be filled across all orders in the group.

        Args:
            contracts_limit (int): The maximum number of contracts that can be filled 
                                across all orders in this group.

        Returns:
            Dict[str, Any]: The JSON response from the API containing the order group details.
        """
        payload = {
            "contracts_limit": contracts_limit
        }
        return self.post(self.portfolio_url + '/order_groups/create', body=payload)
    

    def delete_order_group(self, order_group_id: str) -> Dict[str, Any]:
        """
        Deletes a specific order group by its ID.
        
        Args:
            order_group_id (str): The ID of the order group to delete.
        
        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        return self.delete(self.portfolio_url + '/order_groups/' + order_group_id)
    
    def reset_order_group(self, order_group_id: str) -> Dict[str, Any]:
        """
        Resets a specific order group by its ID.
        
        Resetting an order group clears the current fill count back to zero,
        allowing the group to accept new fills up to the contracts_limit again.
        
        Args:
            order_group_id (str): The ID of the order group to reset.
        
        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        return self.put(self.portfolio_url + '/order_groups/' + order_group_id + '/reset', body={})
    
    def create_batched_orders(
        self,
        orders: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Submits multiple orders in a single batch request.
        
        Args:
            orders (list[Dict[str, Any]])
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing the batch order results.
        """
        payload = {
            "orders": orders
        }
        return self.post(self.portfolio_url + '/orders/batched', body=payload)

    def cancel_batched_orders(
        self,
        ids: list[str]
    ) -> Dict[str, Any]:
        """
        Cancels multiple orders in a single batch request.
        
        Args:
            ids (list[str]): List of order IDs to cancel.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing the batch cancellation results.
        """
        payload = {
            "ids": ids
        }
        # Note: DELETE with body requires special handling
        self.rate_limit()
        response = requests.delete(
            self.host + self.portfolio_url + '/orders/batched',
            json=payload,
            headers=self.request_headers("DELETE", self.portfolio_url + '/orders/batched')
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get_settlements(
        self,
        ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves all settlements for the member with optional filters.

        Args:
            ticker (Optional[str]): Restricts the response to settlements in a specific market.
            min_ts (Optional[int]): Restricts the response to settlements after this timestamp.
            max_ts (Optional[int]): Restricts the response to settlements before this timestamp.
            limit (Optional[int]): Number of results per page (1 to 1000, defaults to 100 if not provided).
            cursor (Optional[str]): Cursor for pagination from a previous request.

        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        params = {
            "ticker": ticker,
            "event_ticker": event_ticker,
            "min_ts": min_ts,
            "max_ts": max_ts,
            "limit": limit,
            "cursor": cursor,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/settlements', params=params)
    
    def get_portfolio_settlements(
        self,
        limit: Optional[int] = None,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves the member's settlements historical track.

        Args:
            limit (Optional[int]): Number of results per page (1 to 1000, defaults to 100 if not provided).
            min_ts (Optional[int]): Restricts the response to settlements after this timestamp.
            max_ts (Optional[int]): Restricts the response to settlements before this timestamp.
            cursor (Optional[str]): Pointer to the next page of records for pagination.
        
        Returns:
            Dict[str, Any]: The JSON response from the API.
        """
        params = {
            "limit": limit,
            "min_ts": min_ts,
            "max_ts": max_ts,
            "cursor": cursor,
        }
        # Remove keys with None values to avoid sending unnecessary parameters.
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/settlements', params=params)
    
    def get_portfolio_resting_order_total_value(self) -> Dict[str, Any]:
        """Retrieves the total value of resting orders in the portfolio."""
        return self.get(self.portfolio_url + '/summary/total_resting_order_value')
   
    def get_total_market_exposure(self) -> int:
        """
        Retrieves all market positions and calculates the total absolute market exposure.

        Returns:
            int: The sum of the absolute market exposure for all positions.
        """
        positions_data = self.get_positions()
        total_exposure = sum(
            abs(position.get("market_exposure", 0))
            for position in positions_data.get("market_positions", [])
        )
        return total_exposure

    def get_orders_queue_positions(self) -> Dict[str, Any]:
        """
        Retrieves the queue positions for all resting orders.
        
        Queue position indicates where your order sits in the order book relative to other
        orders at the same price level. Lower numbers indicate higher priority for execution.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing queue positions for all orders.
        """
        return self.get(self.portfolio_url + '/orders/queue_positions')

    def get_order_queue_position(self, order_id: str) -> Dict[str, Any]:
        """
        Retrieves the queue position for a specific order.
        
        Queue position indicates where your order sits in the order book relative to other
        orders at the same price level. Lower numbers indicate higher priority for execution.
        
        Args:
            order_id (str): The ID of the order to get queue position for.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing the order's queue position.
        """
        return self.get(self.portfolio_url + '/orders/' + order_id + '/queue_position')

    # ==================== Market Methods ====================

    def get_market(self, ticker: str) -> Dict[str, Any]:
        """Retrieves a specific market by its ticker."""
        return self.get(self.markets_url + '/' + ticker)

    def get_markets(self, event_ticker: Optional[str] = None, series_ticker: Optional[str] = None, max_close_ts: Optional[int] = None, min_close_ts: Optional[int] = None, limit: Optional[int] = None, cursor: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves markets with optional filters."""
        params = {
            'event_ticker': event_ticker,
            'series_ticker': series_ticker,
            'max_close_ts': max_close_ts,
            'min_close_ts': min_close_ts,
            'limit': limit,
            'cursor': cursor,
            'status' : status,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.markets_url, params=params)
    
    def filter_markets(
    self,
    markets_data: Dict[str, Any],
    filter_key: str,
    filter_value: Any = None
    ) -> Dict[str, Any]:
        """
        Filters and organizes market data by a specific field.
        
        Args:
            markets_data (Dict[str, Any]): The markets data returned from get_markets().
            filter_key (str): The field to filter/organize by (e.g., 'strike_type', 'ticker', 'status').
            filter_value (Any, optional): If provided, only returns markets matching this value.
                                        If None, returns a dict mapping all unique values to their markets.
        
        Returns:
            Dict[str, Any]: If filter_value is provided, returns markets matching that value.
                            If filter_value is None, returns dict mapping each unique value to list of markets.
        
        Examples:
            # Get all markets grouped by strike_type
            filter_markets(data, 'strike_type')
            # Returns: {'between': [markets...], 'less': [markets...], 'greater': [markets...]}
            
            # Get only markets with strike_type='between'
            filter_markets(data, 'strike_type', 'between')
            # Returns: {'markets': [markets with strike_type='between']}
            
            # Create ticker to market mapping
            filter_markets(data, 'ticker')
            # Returns: {'KXHIGHMIA-25JUL07-B85.5': {market_data}, ...}
        """
        markets = markets_data.get('markets', [])
        
        if filter_value is not None:
            # Return only markets matching the filter value
            filtered = [m for m in markets if m.get(filter_key) == filter_value]
            return {'markets': filtered, 'count': len(filtered)}
        
        # Group markets by unique values of filter_key
        result = {}
        for market in markets:
            key_value = market.get(filter_key)
            
            # Special handling for ticker - map ticker to single market object
            if filter_key == 'ticker':
                result[key_value] = market
            else:
                # For other keys, group markets by value
                if key_value not in result:
                    result[key_value] = []
                result[key_value].append(market)
        
        return result

    def get_markets_by_field(
        self,
        field: str,
        value: Any,
        series_ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retrieves markets and filters them by a specific field value.
        
        Convenience method that combines get_markets() and filter_markets().
        
        Args:
            field (str): The field to filter by (e.g., 'strike_type', 'status', 'result').
            value (Any): The value to filter for.
            series_ticker (Optional[str]): Filter by series ticker.
            event_ticker (Optional[str]): Filter by event ticker.
            **kwargs: Additional parameters to pass to get_markets().
        
        Returns:
            Dict[str, Any]: Markets matching the field/value criteria.
        
        Examples:
            # Get all 'between' strike type markets for a series
            api.get_markets_by_field('strike_type', 'between', series_ticker='KXHIGHMIA')
            
            # Get all finalized markets
            api.get_markets_by_field('status', 'finalized')
        """
        markets_data = self.get_markets(
            series_ticker=series_ticker,
            event_ticker=event_ticker,
            **kwargs
        )
        return self.filter_markets(markets_data, field, value)

    def get_ticker_map(
        self,
        series_ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """
        Creates a dictionary mapping tickers to their full market data.
        
        Args:
            series_ticker (Optional[str]): Filter by series ticker.
            event_ticker (Optional[str]): Filter by event ticker.
            **kwargs: Additional parameters to pass to get_markets().
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping each ticker to its market data.
        
        Example:
            ticker_map = api.get_ticker_map(series_ticker='KXHIGHMIA')
            # Access specific market by ticker
            market = ticker_map['KXHIGHMIA-25JUL07-B85.5']
        """
        markets_data = self.get_markets(
            series_ticker=series_ticker,
            event_ticker=event_ticker,
            **kwargs
        )
        return self.filter_markets(markets_data, 'ticker')
    
    def get_market_orderbook(self, ticker: str) -> Dict[str, Any]:
        """Retrieves the order book for a specific market ticker."""                  
        return self.get(self.markets_url + "/" + ticker + "/orderbook")

    def get_trades(
        self,
        ticker: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        max_ts: Optional[int] = None,
        min_ts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieves trades based on provided filters."""
        params = {
            'ticker': ticker,
            'limit': limit,
            'cursor': cursor,
            'max_ts': max_ts,
            'min_ts': min_ts,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.markets_url + '/trades', params=params)

    # ==================== Event Methods ====================

    def get_events(self, ticker: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves events based on provided filters."""
        params = {'ticker': ticker} if ticker else {}
        return self.get('/trade-api/v2/events/', params=params)

    def get_event(self, event_ticker: str) -> Dict[str, Any]:   
        """Retrieves a specific event by its ID."""
        return self.get(self.events_url + '/' + event_ticker)
    
    def get_event_candlesticks(
    self,
    series_ticker: str,
    event_ticker: str,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    period_interval: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieves candlesticks for a specific event within a series.
        
        Args:
            series_ticker (str): The ticker of the series.
            event_ticker (str): The ticker of the event.
            start_ts (Optional[int]): Start timestamp for the candlestick data.
            end_ts (Optional[int]): End timestamp for the candlestick data.
            period_interval (Optional[int]): The interval period for each candlestick.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing candlestick data.
        """
        params = {
            'start_ts': start_ts,
            'end_ts': end_ts,
            'period_interval': period_interval,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(f"{self.series_url}/{series_ticker}/events/{event_ticker}/candlesticks", params=params)

    def get_multivariate_events(
    self,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves multivariate events with optional filters.
        
        Multivariate events are events that have multiple related markets that
        are mutually exclusive (only one outcome can occur).
        
        Args:
            limit (Optional[int]): Number of results per page.
            cursor (Optional[str]): Cursor for pagination from a previous request.
            status (Optional[str]): Filter by event status (e.g., "open", "closed", "settled").
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing multivariate events.
        """
        params = {
            'limit': limit,
            'cursor': cursor,
            'status': status,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self.get('/trade-api/v2/events/multivariate', params=params)
    
    def get_event_metadata(self, event_ticker: str) -> Dict[str, Any]:
        """
        Retrieves metadata for a specific event.
        
        Event metadata includes additional information about the event such as
        description, resolution details, and other event-specific data.
        
        Args:
            event_ticker (str): The ticker of the event.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing event metadata.
        """
        return self.get(self.events_url + '/' + event_ticker + '/metadata')
    
    def get_event_forecast_percentile_history(
        self,
        series_ticker: str,
        event_ticker: str,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieves the forecast percentile history for a specific event within a series.
        
        This shows how the market's probability forecast has changed over time,
        displayed as percentile data.
        
        Args:
            series_ticker (str): The ticker of the series.
            event_ticker (str): The ticker of the event.
            min_ts (Optional[int]): Minimum timestamp to filter results from.
            max_ts (Optional[int]): Maximum timestamp to filter results to.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing forecast percentile history.
        """
        params = {
            'min_ts': min_ts,
            'max_ts': max_ts,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(f"{self.series_url}/{series_ticker}/events/{event_ticker}/forecast_percentile_history", params=params)
    # ==================== Series Methods ====================
    
    def get_series(self, series_ticker: str) -> Dict[str, Any]:
        """Retrieves series for a specific market ticker."""
        return self.get(self.series_url + '/' + series_ticker)
    
    def get_all_series(
    self,
    limit: Optional[int] = None,
    cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves all series with optional pagination.
        
        Args:
            limit (Optional[int]): Number of results per page.
            cursor (Optional[str]): Cursor for pagination from a previous request.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing all series.
        """
        params = {
            'limit': limit,
            'cursor': cursor,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.series_url, params=params)

    def get_market_candlesticks(self, series_ticker: str, ticker: str, start_ts: int, end_ts: int, period_interval: int) -> Dict[str, Any]:
        """Retrieves candlesticks for a specific market ticker within a series."""
        return self.get(f"/trade-api/v2/series/{series_ticker}/markets/{ticker}/candlesticks?start_ts={start_ts}&end_ts={end_ts}&period_interval={period_interval}")

    # ==================== Communications Methods ====================

    def get_quotes(self, cursor: Optional[str] = None, limit: Optional[int] = None, market_ticker: Optional[str] = None, event_ticker: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves quotes for a specific market ticker."""
        params = {
            'market_ticker': market_ticker,
            'event_ticker': event_ticker,
            'status': status,
            'cursor': cursor,
            'limit': limit,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.communications_url + '/quotes', params=params)
    
    # ==================== Live Data ====================
    def get_live_data_milestone(
        self,
        data_type: str,
        milestone_id: str
    ) -> Dict[str, Any]:
        """
        Retrieves live data for a specific milestone.
        
        Live data provides real-time information about ongoing events such as
        election results, vote counts, or other time-sensitive data.
        
        Args:
            data_type (str): The type of live data (e.g., "election", "votes").
            milestone_id (str): The ID of the specific milestone to retrieve.
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing live milestone data.
        """
        return self.get(f"/trade-api/v2/live_data/{data_type}/milestone/{milestone_id}")
    
    
    def get_live_data_batch(
    self,
    milestone_ids: Optional[list[str]] = None,
    data_types: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Retrieves live data for multiple milestones in a single batch request.
        
        Allows efficient fetching of live data across multiple milestones and data types.
        
        Args:
            milestone_ids (Optional[list[str]]): List of milestone IDs to retrieve data for.
            data_types (Optional[list[str]]): List of data types to filter by (e.g., ["election", "votes"]).
        
        Returns:
            Dict[str, Any]: The JSON response from the API containing batch live data.
        """
        params = {}
        if milestone_ids:
            params['milestone_ids'] = ','.join(milestone_ids)
        if data_types:
            params['data_types'] = ','.join(data_types)
        
        return self.get('/trade-api/v2/live_data/batch', params=params)

    
    # ==================== Helpers ====================
    def plot_market_candlesticks(
        self,
        ticker: str,
        days: int = 7,
        chart_type: str = 'mid_price',
        period_interval: int = 60,
        show: bool = False,
        save_path: Optional[str] = None
    ) -> Optional[Any]:
        """
        Fetches and plots candlestick data for a market.
        
        Args:
            ticker (str): Market ticker to plot.
            days (int): Number of days of historical data to fetch.
            chart_type (str): Type of chart - 'mid_price', 'bid_ask', 'spread', 'volume', 'candlestick'.
            period_interval (int): Interval in minutes for each candlestick (default 60).
            show (bool): Whether to display the chart in browser.
            save_path (Optional[str]): Path to save HTML file. If None, doesn't save.
        
        Returns:
            plotly.graph_objects.Figure: The plotly figure object, or None if error.
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            print("Plotly is required for plotting. Install with: pip install plotly")
            return None
        
        # Extract series ticker
        ticker_parts = ticker.split('-')
        series_ticker = '-'.join(ticker_parts[:-1]) if len(ticker_parts) > 1 else ticker
        
        # Calculate time range
        from datetime import datetime, timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        
        # Fetch candlestick data
        try:
            response = self.get_market_candlesticks(
                series_ticker=series_ticker,
                ticker=ticker,
                start_ts=start_ts,
                end_ts=end_ts,
                period_interval=period_interval
            )
            candlesticks = response.get('candlesticks', [])
        except Exception as e:
            print(f"Error fetching candlestick data: {e}")
            return None
        
        if not candlesticks:
            print(f"No candlestick data available for {ticker}")
            return None
        
        # Process data
        processed = []
        for candle in candlesticks:
            ts = candle.get('end_period_ts')
            if not ts:
                continue
                
            yes_bid = candle.get('yes_bid') or {}
            yes_ask = candle.get('yes_ask') or {}
            
            # Convert cents to dollars
            bid_open = yes_bid.get('open', 0) / 100 if yes_bid.get('open') else None
            bid_high = yes_bid.get('high', 0) / 100 if yes_bid.get('high') else None
            bid_low = yes_bid.get('low', 0) / 100 if yes_bid.get('low') else None
            bid_close = yes_bid.get('close', 0) / 100 if yes_bid.get('close') else None
            
            ask_open = yes_ask.get('open', 0) / 100 if yes_ask.get('open') else None
            ask_high = yes_ask.get('high', 0) / 100 if yes_ask.get('high') else None
            ask_low = yes_ask.get('low', 0) / 100 if yes_ask.get('low') else None
            ask_close = yes_ask.get('close', 0) / 100 if yes_ask.get('close') else None
            
            if bid_close is not None and ask_close is not None:
                mid_open = (bid_open + ask_open) / 2 if bid_open and ask_open else None
                mid_high = (bid_high + ask_high) / 2 if bid_high and ask_high else None
                mid_low = (bid_low + ask_low) / 2 if bid_low and ask_low else None
                mid_close = (bid_close + ask_close) / 2
                
                processed.append({
                    'timestamp': datetime.fromtimestamp(ts),
                    'bid_open': bid_open, 'bid_high': bid_high, 'bid_low': bid_low, 'bid_close': bid_close,
                    'ask_open': ask_open, 'ask_high': ask_high, 'ask_low': ask_low, 'ask_close': ask_close,
                    'mid_open': mid_open, 'mid_high': mid_high, 'mid_low': mid_low, 'mid_close': mid_close,
                    'spread': ask_close - bid_close,
                    'volume': candle.get('volume', 0),
                    'open_interest': candle.get('open_interest', 0)
                })
        
        if not processed:
            print(f"No valid data points for {ticker}")
            return None
        
        # Create figure based on chart type
        timestamps = [d['timestamp'] for d in processed]
        
        if chart_type == 'candlestick':
            fig = go.Figure(data=[go.Candlestick(
                x=timestamps,
                open=[d['mid_open'] * 100 for d in processed],
                high=[d['mid_high'] * 100 for d in processed],
                low=[d['mid_low'] * 100 for d in processed],
                close=[d['mid_close'] * 100 for d in processed],
                name='Mid Price'
            )])
            fig.update_layout(yaxis_title='Price (cents)')
            
        elif chart_type == 'mid_price':
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=[d['mid_close'] * 100 for d in processed],
                mode='lines+markers',
                name='Mid Price',
                line=dict(color='#4299e1', width=2),
                marker=dict(size=4)
            ))
            fig.update_layout(yaxis_title='Price (cents)')
            
        elif chart_type == 'bid_ask':
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=[d['bid_close'] * 100 for d in processed],
                mode='lines',
                name='Bid',
                line=dict(color='#68d391', width=2),
                fill='tonexty'
            ))
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=[d['ask_close'] * 100 for d in processed],
                mode='lines',
                name='Ask',
                line=dict(color='#fc8181', width=2),
                fill='tonexty'
            ))
            fig.update_layout(yaxis_title='Price (cents)')
            
        elif chart_type == 'spread':
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=[d['spread'] * 100 for d in processed],
                mode='lines+markers',
                name='Bid-Ask Spread',
                line=dict(color='#f6ad55', width=2),
                marker=dict(size=4),
                fill='tozeroy'
            ))
            fig.update_layout(yaxis_title='Spread (cents)')
            
        elif chart_type == 'volume':
            fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], 
                            vertical_spacing=0.03, shared_xaxes=True)
            
            # Price subplot
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=[d['mid_close'] * 100 for d in processed],
                mode='lines',
                name='Mid Price',
                line=dict(color='#4299e1', width=2)
            ), row=1, col=1)
            
            # Volume subplot
            fig.add_trace(go.Bar(
                x=timestamps,
                y=[d['volume'] for d in processed],
                name='Volume',
                marker_color='#b794f6',
                opacity=0.7
            ), row=2, col=1)
            
            fig.update_yaxes(title_text='Price (cents)', row=1, col=1)
            fig.update_yaxes(title_text='Volume', row=2, col=1)
        
        else:
            print(f"Unknown chart type: {chart_type}")
            return None
        
        # Style the chart
        fig.update_layout(
            title=f'{ticker} - {chart_type.replace("_", " ").title()} ({days}d)',
            title_font=dict(size=20, color='#e2e8f0'),
            xaxis_title='Time',
            xaxis=dict(color='#a0aec0', gridcolor='#4a5568', showgrid=True),
            yaxis=dict(color='#a0aec0', gridcolor='#4a5568', showgrid=True),
            plot_bgcolor='#1a202c',
            paper_bgcolor='#2d3748',
            font=dict(color='#e2e8f0'),
            legend=dict(bgcolor='rgba(26, 32, 44, 0.8)', bordercolor='#4a5568', borderwidth=1),
            hovermode='x unified'
        )
        
        # Save if requested
        if save_path:
            fig.write_html(save_path)
            print(f"Chart saved to {save_path}")
        
        # Show if requested
        if show:
            fig.show()
        
        return fig    
    
    def calculate_expected_value(
        self,
        yes_price: int,
        true_probability: float,
        contract_count: int = 1
    ) -> float:
        """
        Calculate expected value of a position.
        
        Args:
            yes_price (int): Price in cents you're buying/selling at.
            true_probability (float): Your estimated true probability (0.0-1.0).
            contract_count (int): Number of contracts.
        
        Returns:
            float: Expected value in cents.
        """
        cost = yes_price * contract_count
        expected_payout = 100 * contract_count * true_probability
        return expected_payout - cost

    def calculate_kelly_criterion(
        self,
        yes_price: int,
        true_probability: float,
        bankroll: int = None,
        adjustment_factor: float = 0.5

    ) -> int:
        """
        Calculate optimal bet size using Kelly Criterion.
        
        Args:
            yes_price (int): Current market price in cents.
            true_probability (float): Your estimated probability (0.0-1.0).
            bankroll (int): Your total bankroll in cents.
            adjustment_factor (float): Fraction of Kelly to use for safety (default 0.5 for half-Kelly).
        
        Returns:
            int: Recommended bet size in cents.
        """
        if bankroll is None:
            portfolio_data = self.get_portfolio()
            bankroll = portfolio_data.get("cash_balance", 0)

        if bankroll <= 0:
            return 0
        
        if yes_price <= 0 or yes_price >= 100:
            return 0
        
        b = (100 - yes_price) / yes_price
        q = 1 - true_probability
        
        kelly_fraction = (b * true_probability - q) / b
        kelly_fraction = max(0, min(kelly_fraction, 1))  # Clamp between 0 and 1
        
        # Use fractional Kelly (e.g., half Kelly) for safety
        fractional_kelly = kelly_fraction * adjustment_factor
        
        return int(bankroll * fractional_kelly)


class KalshiWebSocketClient(KalshiBaseClient):
    """Client for handling WebSocket connections to the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ):
        super().__init__(key_id, private_key, environment)
        self.ws = None
        self.url_suffix = "/trade-api/ws/v2"
        self.message_id = 1

    async def connect(self):
        """Establishes a WebSocket connection using authentication."""
        host = self.WS_BASE_URL + self.url_suffix
        auth_headers = self.request_headers("GET", self.url_suffix)
        async with websockets.connect(host, additional_headers=auth_headers) as websocket:
            self.ws = websocket
            await self.on_open()
            await self.handler()

    async def on_open(self):
        """Callback when WebSocket connection is opened."""
        print("WebSocket connection opened.")
        await self.subscribe_to_tickers()

    async def subscribe_to_tickers(self):
        """Subscribe to ticker updates for all markets."""
        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"]
            }
        }
        await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1

    async def subscribe_to_specific_tickers(self, tickers: list):
        """Subscribe to ticker updates for specific markets."""
        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {
                "channels": [f"ticker:{ticker}" for ticker in tickers]
            }
        }
        await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1

    async def subscribe_to_orderbook(self, ticker: str):
        """Subscribe to orderbook updates for a specific market."""
        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {
                "channels": [f"orderbook_delta:{ticker}"]
            }
        }
        await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1

    async def subscribe_to_trades(self, ticker: str = None):
        """Subscribe to trade updates for all markets or a specific market."""
        if ticker:
            channel = f"trade:{ticker}"
        else:
            channel = "trade"
        
        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {
                "channels": [channel]
            }
        }
        await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1

    async def unsubscribe_from_channel(self, channel: str):
        """Unsubscribe from a specific channel."""
        unsubscribe_message = {
            "id": self.message_id,
            "cmd": "unsubscribe",
            "params": {
                "channels": [channel]
            }
        }
        await self.ws.send(json.dumps(unsubscribe_message))
        self.message_id += 1

    async def send_custom_message(self, message: dict):
        """Send a custom message through the WebSocket connection."""
        message["id"] = self.message_id
        await self.ws.send(json.dumps(message))
        self.message_id += 1

    async def handler(self):
        """Handle incoming messages."""
        try:
            async for message in self.ws:
                await self.on_message(message)
        except websockets.ConnectionClosed as e:
            await self.on_close(e.code, e.reason)
        except Exception as e:
            await self.on_error(e)

    async def on_message(self, message):
        """Callback for handling incoming messages."""
        print("Received message:", message)

    async def on_error(self, error):
        """Callback for handling errors."""
        print("WebSocket error:", error)

    async def on_close(self, close_status_code, close_msg):
        """Callback when WebSocket connection is closed."""
        print("WebSocket connection closed with code:", close_status_code, "and message:", close_msg)