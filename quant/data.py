# -*- coding:utf-8 -*-

"""
Data to db.

Author: HuangTao
Date:   2018/05/17
Email:  huangtao@ifclover.com
"""

from quant.utils import tools
from quant.utils.mongo import MongoDBBase


class KLineData(MongoDBBase):
    """ Save or fetch kline data via MongoDB.

    Data struct:
        {
            "o": open, # Open price
            "h": high, # Highest price
            "l": low, # Lowest price
            "c": close, # Close price
            "t": timestamp # Millisecond timestamp
        }

    Attributes:
        platform: Exchange platform name.
    """

    def __init__(self, platform):
        """ Initialize object.
        """
        self._db = platform  # Db name. => MongoDB db name.
        self._collection = "kline"  # Table name. => MongoDB collection name.
        self._platform = platform
        self._k_to_c = {}   # Kline types cursor for db. e.g. {"BTC/USD": "kline_btc_usd"}
        super(KLineData, self).__init__(self._db, self._collection)

    async def create_new_kline(self, symbol, open, high, low, close, timestamp):
        """ Insert kline data to db.

        Args:
            symbol: Symbol pair, e.g. ETH/BTC.
            open: Open price.
            high: Highest price.
            low: Lowest price.
            close: Close price.
            timestamp: Millisecond timestamp.

        Returns:
            kline_id: Kline id, it's a MongoDB document _id.
        """
        cursor = self._get_kline_cursor_by_symbol(symbol)
        data = {
            "o": open,
            "h": high,
            "l": low,
            "c": close,
            "t": timestamp
        }
        kline_id = await self.insert(data, cursor=cursor)
        return kline_id

    async def get_kline_at_ts(self, symbol, ts=None):
        """ Get a kline data, you can specific symbol and timestamp.

        Args:
            symbol: Symbol pair, e.g. ETH/BTC.
            ts: Millisecond timestamp. If this param is None, ts will be specific current timestamp.

        Returns:
            result: kline data, dict format. If no any data in db, result is None.
        """
        cursor = self._get_kline_cursor_by_symbol(symbol)
        if ts:
            spec = {"t": {"$lte": ts}}
        else:
            spec = {}
        _sort = [("t", -1)]
        result = await self.find_one(spec, sort=_sort, cursor=cursor)
        return result

    async def get_latest_kline_by_symbol(self, symbol):
        """ Get latest kline data by symbol.

        Args:
            symbol: Symbol pair, e.g. ETH/BTC.

        Returns:
            result: kline data, dict format. If no any data in db, result is None.
        """
        cursor = self._get_kline_cursor_by_symbol(symbol)
        sort = [("create_time", -1)]
        result = await self.find_one(sort=sort, cursor=cursor)
        return result

    async def get_kline_between_ts(self, symbol, start, end):
        """ Get some kline data between two timestamps.

        Args:
            symbol: Symbol pair, e.g. ETH/BTC.
            start: Millisecond timestamp, the start time you want to specific.
            end: Millisecond timestamp, the end time you want to specific.

        Returns:
            result: kline data, list format. If no any data in db, result is a empty list.
        """
        cursor = self._get_kline_cursor_by_symbol(symbol)
        spec = {
            "t": {
                "$gte": start,
                "$lte": end
            }
        }
        fields = {
            "create_time": 0,
            "update_time": 0
        }
        _sort = [("t", 1)]
        datas = await self.get_list(spec, fields=fields, sort=_sort, cursor=cursor)
        return datas

    def _get_kline_cursor_by_symbol(self, symbol):
        """ Get a cursor name by symbol, we will convert a symbol name to a collection name.
            e.g. ETH/BTC => kline_eth_btc

        Args:
            symbol: Symbol pair, e.g. ETH/BTC.

        Returns:
            cursor: DB query cursor name.
        """
        cursor = self._k_to_c.get(symbol)
        if not cursor:
            x, y = symbol.split("/")
            collection = "kline_{x}_{y}".format(x=x.lower(), y=y.lower())
            cursor = self._conn[self._db][collection]
            self._k_to_c[symbol] = cursor
        return cursor


class AssetData(MongoDBBase):
    """ Save or fetch asset data via MongoDB.

    Data struct:
        {
            "platform": "binance", # Exchange platform name.
            "account": "test@gmail.com", # Account name.
            "timestamp": 1234567890, # Millisecond timestamp.
            "BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"},  # Currency details for BTC.
            "ETH": { ... },
            ...
        }
    """

    def __init__(self):
        """Initialize object."""
        self._db = "asset"  # db name
        self._collection = "asset"  # collection name
        super(AssetData, self).__init__(self._db, self._collection)

    async def create_new_asset(self, platform, account, asset, timestamp):
        """ Insert asset data to db.

        Args:
            platform: Exchange platform name. e.g. binance/bitmex/okex
            account: Account name. e.g. test@gmail.com
            asset: Asset data, dict format. e.g. {"BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"}, ... }
            timestamp: Millisecond timestamp.

        Returns:
            asset_id: Asset id, it's a MongoDB document _id.
        """
        d = {
            "platform": platform,
            "account": account,
            "timestamp": timestamp
        }
        for key, value in asset.items():
            d[key] = value
        asset_id = await self.insert(d)
        return asset_id

    async def update_asset(self, platform, account, asset, timestamp, delete=None):
        """ Update asset data.

        Args:
            platform: Exchange platform name. e.g. binance/bitmex/okex
            account: Account name. e.g. test@gmail.com
            asset: Asset data, dict format. e.g. {"BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"}, ... }
            timestamp: Millisecond timestamp.
            delete: Currency name list for delete.

        Returns:
            count: How many documents have been updated.
        """
        spec = {
            "platform": platform,
            "account": account,
            "timestamp": timestamp
        }
        update_fields = {"$set": asset}
        if delete:
            d = {}
            for key in delete:
                d[key] = 1
            update_fields["$unset"] = d
        count = await self.update(spec, update_fields=update_fields, upsert=True)
        return count

    async def get_latest_asset(self, platform, account):
        """ Get latest asset data.

        Args:
            platform: Exchange platform name. e.g. binance/bitmex/okex
            account: Account name. e.g. test@gmail.com

        Returns:
            asset: Asset data, e.g. {"BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"}, ... }
        """
        spec = {
            "platform": platform,
            "account": account
        }
        _sort = [("timestamp", -1)]
        fields = {
            "create_time": 0,
            "update_time": 0
        }
        asset = await self.find_one(spec, sort=_sort, fields=fields)
        if asset:
            del asset["_id"]
        return asset


class AssetSnapshotData(MongoDBBase):
    """ Save or fetch asset snapshot data via MongoDB.

    Data struct:
        {
            "platform": "binance", # Exchange platform name.
            "account": "test@gmail.com", # Account name.
            "timestamp": 1234567890, # Millisecond timestamp.
            "BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"},  # Currency details for BTC.
            "ETH": { ... },
            ...
        }
    """

    def __init__(self):
        """Initialize object."""
        self._db = "asset"  # db name
        self._collection = "snapshot"  # collection name
        super(AssetSnapshotData, self).__init__(self._db, self._collection)

    async def create_new_asset(self, platform, account, asset, timestamp):
        """ Insert asset snapshot data to db.

        Args:
            platform: Exchange platform name. e.g. binance/bitmex/okex
            account: Account name. e.g. test@gmail.com
            timestamp: Millisecond timestamp.
            asset: Asset data, dict format. e.g. {"BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"}, ... }

        Returns:
            asset_id: Asset id, it's a MongoDB document _id.
        """
        d = {
            "platform": platform,
            "account": account,
            "timestamp": timestamp
        }
        for key, value in asset.items():
            d[key] = value
        asset_id = await self.insert(d)
        return asset_id

    async def get_asset_snapshot(self, platform, account, start=None, end=None):
        """ Get asset snapshot data from db.

        Args:
            platform: Exchange platform name. e.g. binance/bitmex/okex
            account: Account name. e.g. test@gmail.com
            start: Start time, Millisecond timestamp, default is a day ago.
            end: End time, Millisecond timestamp, default is current timestamp.

        Returns:
            datas: Asset data list. e.g. [{"BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"}, ... }, ... ]
        """
        if not end:
            end = tools.get_cur_timestamp()  # Current timestamp
        if not start:
            start = end - 60 * 60 * 24  # A day ago.
        spec = {
            "platform": platform,
            "account": account,
            "timestamp": {
                "$gte": start,
                "$lte": end
            }
        }
        fields = {
            "platform": 0,
            "account": 0,
            "update_time": 0
        }
        datas = await self.get_list(spec, fields=fields)
        return datas

    async def get_latest_asset_snapshot(self, platform, account):
        """ Get latest asset snapshot data.

        Args:
            platform: Exchange platform name. e.g. binance/bitmex/okex
            account: Account name. e.g. test@gmail.com

        Returns:
            asset: Asset data, e.g. {"BTC": {"free": "1.1", "locked": "2.2", "total": "3.3"}, ... }
        """
        spec = {
            "platform": platform,
            "account": account
        }
        _sort = [("timestamp", -1)]
        asset = await self.find_one(spec, sort=_sort)
        if asset:
            del asset["_id"]
        return asset


class OrderData(MongoDBBase):
    """ Save or fetch order data via MongoDB.

    Data struct:
        {
            "p": order.platform,
            "a": order.account,
            "s": order.strategy,
            "S": order.symbol,
            "n": order.order_no,
            "A": order.action,
            "t": order.order_type,
            "st": order.status,
            "pr": order.price,
            "ap": order.avg_price,
            "q": order.quantity,
            "r": order.remain,
            "T": order.trade_type,
            "ct": order.ctime,
            "ut": order.utime
        }
        All the fields are defined in Order module.
    """

    def __init__(self):
        """Initialize object."""
        self._db = "strategy"  # db name
        self._collection = "order"  # collection name
        super(OrderData, self).__init__(self._db, self._collection)

    async def create_new_order(self, order):
        """ Insert order data to db.

        Args:
            order: Order object.

        Returns:
            order_id: order data id, it's a MongoDB document _id.
        """
        data = {
            "p": order.platform,
            "a": order.account,
            "s": order.strategy,
            "S": order.symbol,
            "n": order.order_no,
            "A": order.action,
            "t": order.order_type,
            "st": order.status,
            "pr": order.price,
            "ap": order.avg_price,
            "q": order.quantity,
            "r": order.remain,
            "T": order.trade_type,
            "ct": order.ctime,
            "ut": order.utime
        }
        order_id = await self.insert(data)
        return order_id

    async def get_order_by_no(self, platform, order_no):
        """ Get a order by order no.

        Args:
            platform: Exchange platform name.
            order_no: order no.

        Returns:
            data: order data, dict format.
        """
        spec = {
            "p": platform,
            "n": order_no
        }
        data = await self.find_one(spec)
        return data

    async def update_order_infos(self, order):
        """ Update order information.

        Args:
            order: Order object.

        Returns:
            count: How many documents have been updated.
        """
        spec = {
            "p": order.platform,
            "n": order.order_no
        }
        update_fields = {
            "s": order.status,
            "r": order.remain
        }
        count = await self.update(spec, update_fields={"$set": update_fields})
        return count

    async def get_latest_order(self, platform, symbol):
        """ Get a latest order data.

        Args:
            platform: Exchange platform name.
            symbol: Symbol name.

        Return:
            data: order data, dict format.
        """
        spec = {
            "p": platform,
            "S": symbol
        }
        _sort = [("ut", -1)]
        data = await self.find_one(spec, sort=_sort)
        return data
