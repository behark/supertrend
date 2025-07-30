# tests/supertrend_deep_tests.py
import os
import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Core imports
from src.indicators import calculate_supertrend, calculate_adx, calculate_atr, detect_inside_bar
from src.strategies import SuperTrendStrategy, InsideBarStrategy
from src.market_data import fetch_raw_data, parse_raw_market_data, validate_ohlcv_df
from src.bot import TradingBot
from src.paper_trading import PaperTradingSimulator

# Analytics & models
from src.analytics.pattern_matcher import PatternMatcher
from src.analytics.regime_logger import RegimeLogger
from src.models.regime_performance import RegimePerformance

# Integrations
from src.integrations.bidget import BidgetClient
from src.integrations.binance_futures import BinanceFuturesClient
from src.integrations.order_manager import OrderManager
from src.integrations.telegram import TelegramNotifier
from src.integrations.telegram_commands import TelegramCommands

# Utilities
from src.utils.config import load_config, validate_config
from src.utils.parameter_manager import ParameterManager
from src.utils.playbook_manager import PlaybookManager
from src.utils.notification_cache import NotificationCache
from src.utils.analytics_logger import AnalyticsLogger
from src.utils.market_analyzer import MarketAnalyzer
from src.utils.logger import get_logger
from src.utils.daemon import Daemon
from src.utils.health_check import HealthCheck

# Dashboard
from src.dashboard.app import create_app

# Process management
import watchdog
from watchdog import monitor_process

# Helpers

def make_sample_ohlcv(n=100):
    now = datetime.utcnow()
    times = [now + timedelta(minutes=i) for i in range(n)]
    price = np.linspace(100,200,n) + np.random.randn(n)
    df = pd.DataFrame({
        'timestamp': times,
        'open': price,
        'high': price + np.abs(np.random.randn(n)),
        'low': price - np.abs(np.random.randn(n)),
        'close': price + np.random.randn(n),
        'volume': np.random.rand(n)*1000
    })
    df.set_index('timestamp', inplace=True)
    return df

# ------------------------ UNIT TESTS ------------------------
class TestIndicators:
    def test_supertrend_output(self):
        df = make_sample_ohlcv()
        st = calculate_supertrend(df['high'], df['low'], df['close'], period=10, multiplier=3)
        assert isinstance(st, pd.Series)
        assert len(st) == len(df)
        assert st.dropna().dtype == float

    def test_adx_bounds(self):
        df = make_sample_ohlcv(200)
        adx = calculate_adx(df['high'], df['low'], df['close'], period=14)
        assert adx.between(0,100).all()

    def test_atr_positive(self):
        df = make_sample_ohlcv(50)
        atr = calculate_atr(df['high'], df['low'], df['close'], period=14)
        assert (atr >= 0).all()

    def test_inside_bar_flag(self):
        data = pd.DataFrame({
            'high':[5,6,5.5], 'low':[1,2,1.8], 'open':[2,3,2.5], 'close':[4,5,4.5]
        })
        flags = detect_inside_bar(data)
        assert flags.tolist() == [False, True, False]

class TestStrategies:
    def test_supertrend_signals(self):
        df = make_sample_ohlcv()
        strat = SuperTrendStrategy(period=10, multiplier=2)
        signals = strat.generate_signals(df)
        assert set(signals['signal'].unique()).issubset({-1,0,1})

    def test_insidebar_signals(self):
        df = make_sample_ohlcv(30)
        strat = InsideBarStrategy()
        sig = strat.generate_signals(df)
        assert 'signal' in sig.columns and len(sig)==len(df)

class TestMarketData:
    def test_fetch_and_parse(self, monkeypatch):
        raw = [{'time':1,'open':1,'high':2,'low':0.5,'close':1.5,'volume':10}]
        monkeypatch.setattr('src.market_data.fetch_raw_data', lambda *args,**k: raw)
        df = parse_raw_market_data(raw)
        assert 'timestamp' in df.columns and df.volume.iloc[0]==10

    def test_validate_ohlcv(self):
        df = make_sample_ohlcv()
        assert validate_ohlcv_df(df) is True
        df2 = df.drop(columns=['volume'])
        with pytest.raises(ValueError): validate_ohlcv_df(df2)

class TestConfigUtilities:
    def test_load_and_validate(self, tmp_path):
        cfg = {'symbols':['BTC/USDT'], 'strategy':'supertrend'}
        p = tmp_path/'cfg.json'
        p.write_text(json.dumps(cfg))
        loaded = load_config(str(p))
        assert validate_config(loaded) is None
    def test_validate_missing_key(self):
        with pytest.raises(KeyError): validate_config({'symbols':[]})

class TestUtilityModules:
    def test_parameter_manager(self):
        pm=ParameterManager(); params=pm.get_parameters(); assert isinstance(params,dict)
    def test_playbook_manager(self, tmp_path):
        pm=PlaybookManager(storage_dir=str(tmp_path)); pm.save_playbook('x',{'a':1}); assert pm.load_playbook('x')['a']==1
    def test_notification_cache(self, tmp_path):
        nc=NotificationCache(str(tmp_path/'cache.db')); nc.set('k','v'); assert nc.get('k')=='v'
    def test_analytics_logger(self, tmp_path):
        al=AnalyticsLogger(str(tmp_path/'log.txt')); al.log({'e':1}); assert os.path.exists(str(tmp_path/'log.txt'))
    def test_market_analyzer(self):
        ma=MarketAnalyzer(); assert hasattr(ma,'analyze_trend')
    def test_logger_factory(self):
        log=get_logger('test'); log.info('hi')

# -------------------- ANALYTICS & MODELS --------------------
class TestPatternMatcher:
    def test_pattern_detection(self):
        pm=PatternMatcher(); df=make_sample_ohlcv(); res=pm.match(df); assert isinstance(res,list)

class TestRegimeLoggerAndPerformance:
    def test_regime_logger(self, tmp_path):
        rl=RegimeLogger(log_dir=str(tmp_path)); rl.log_regime({'regime':'up'});
        files=os.listdir(str(tmp_path)); assert files
    def test_performance_model(self):
        rp=RegimePerformance(); df=pd.DataFrame({'profit':[1,2,-1]}); stats=rp.calculate(df); assert 'total_return' in stats

# ---------------------- INTEGRATION TESTS ----------------------
class TestExchangeIntegrations:
    @pytest.fixture(autouse=True)
    def fake_post(self, monkeypatch):
        class R: 
            def json(self): return {'orderId':'foo'}
        monkeypatch.setattr('requests.post', lambda *a,**k: R())
    def test_bidget(self): assert BidgetClient('k','s').place_order('X','BUY',1)['orderId']=='foo'
    def test_binance(self): assert BinanceFuturesClient('k','s').place_order('Y','SELL',2)['orderId']=='foo'

class TestOrderManagerAndTelegram:
    def test_order_manager(self):
        om=OrderManager(); om.exchange=BidgetClient('k','s'); r=om.execute_order('X','BUY',1); assert r['orderId']=='foo'
    def test_telegram_notifier(self):
        sent={}
        tn=TelegramNotifier('t','c')
        tn.send_message=lambda m: sent.setdefault('msg',m)
        tn.notify('hello'); assert 'hello' in sent['msg']
    def test_telegram_commands(self):
        tc=TelegramCommands('t','c'); methods=[m for m in dir(tc) if not m.startswith('_')]; assert 'start' in methods

class TestDashboardAPI:
    @pytest.fixture
    def client(self):
        app = create_app(testing=True)
        return app.test_client()
    
    def test_health(self, client):
        assert client.get('/health').status_code == 200
    
    def test_performance_routes(self, client):
        rv = client.get('/performance')
        assert rv.status_code in (200, 401)

class TestProcessAndHealth:
    def test_watchdog(self): assert not monitor_process('nope')
    def test_daemon_start_stop(self):
        d=Daemon(); pid=d.start(); assert isinstance(pid,int); d.stop()
    def test_health_check(self): assert isinstance(HealthCheck().check_all(),dict)

# ---------------------- END-TO-END SMOKE ----------------------
def test_full_trading_cycle(monkeypatch):
    # simulate data and execution
    monkeypatch.setattr('src.market_data.fetch_raw_data', lambda *a,**k: [])
    monkeypatch.setattr('src.integrations.bidget.BidgetClient.place_order', lambda *a,**k: {'orderId':'ok'})
    bot = TradingBot({'symbols':['X'],'strategy':'supertrend'})
    result = bot.run_once()
    assert 'executed' in result
