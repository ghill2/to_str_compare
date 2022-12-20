# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2022 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------
import pandas as pd
import os
from pathlib import Path
from decimal import Decimal
import pandas as pd
import gc
import time
import sys

def _create_engine():
    from nautilus_trader.backtest.data.providers import TestInstrumentProvider
    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.backtest.engine import BacktestEngineConfig
    from nautilus_trader.backtest.models import FillModel
    from nautilus_trader.examples.strategies.ema_cross import EMACross
    from nautilus_trader.examples.strategies.ema_cross import EMACrossConfig
    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.data.bar import BarType
    from nautilus_trader.model.enums import AccountType
    from nautilus_trader.model.enums import OMSType
    from nautilus_trader.model.identifiers import Venue
    from nautilus_trader.model.objects import Money
    from nautilus_trader.backtest.data.providers import TestInstrumentProvider
    from nautilus_trader.model.currencies import USD
    
    from nautilus_trader.model.identifiers import Venue
    
    from nautilus_trader.model.data.tick import QuoteTick
    from nautilus_trader.config import BacktestEngineConfig
    from nautilus_trader.config import CacheConfig
    from nautilus_trader.config import RiskEngineConfig
    instrument = TestInstrumentProvider.default_fx_ccy("EUR/USD", venue=Venue("SIM"))

    engine_config = BacktestEngineConfig(
                    risk_engine=RiskEngineConfig(bypass=True),
                    cache=CacheConfig(bar_capacity=1, tick_capacity=1),
                    log_level="WRN"
                )
    engine = BacktestEngine(config=engine_config)
    
    strategy_config = EMACrossConfig(
                        instrument_id=str(instrument.id),
                        bar_type=str(BarType.from_str("EUR/USD.SIM-1-HOUR-ASK-EXTERNAL")),
                        trade_size=Decimal(100_000),
                        fast_ema_period=10,
                        slow_ema_period=20,
        )
    strategy = EMACross(strategy_config)

    engine.add_strategy(strategy)
    engine.add_venue(
        venue=Venue("SIM"),
        oms_type=OMSType.HEDGING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(1_000_000, USD)],
        fill_model=FillModel(),
    )
    engine.add_instrument(instrument)
    return engine

def _get_memory_usage_gb():
    import psutil
    import os
    BYTES_IN_GIGABYTE = 1e9
    return psutil.Process(os.getpid()).memory_info().rss / BYTES_IN_GIGABYTE

def _add_nautilus_to_path(test_name):
    # Add nautilus to path
    path = str(Path(__file__).parent / f"nautilus_trader_{test_name}")
    sys.path.insert(0, path)
    from nautilus_trader import PACKAGE_ROOT
    assert PACKAGE_ROOT == path

def run_memory_test(test_name):

    """
    Process 10 years of ticks through the engine.
     to introduce memory leaks.
    Measure the memory usage after each
    """

    _add_nautilus_to_path(test_name)

    from nautilus_trader.model.data.tick import QuoteTick
    from nautilus_trader.model.identifiers import InstrumentId
    from nautilus_trader.model.objects import Price
    from nautilus_trader.model.objects import Quantity

    # EURUSD 2010 to 2020
    # TICK_COUNT = 162156800 # 10 years
    TICK_COUNT = (162156800 / 10) * 2 # 1 year
    # TICK_COUNT = (162156800 / 10) / 4 # 3 months
    # TICK_COUNT = (162156800 / 10) / 12 # 1 month
    # TICK_COUNT = ((162156800 / 10) / 12) / 30 # 1 day
    

    batch_count = 50 # split the TICK_COUNT over n batches
    batch_size = int(TICK_COUNT / batch_count)
    
    processed = 0
    elapsed = 0

    measurements = pd.DataFrame()

    path = Path(__file__).parent / f"{test_name}.csv"
    if path.exists():
        path.unlink()

    for _ in range(batch_count):
        
        quotes = [
            QuoteTick(
                InstrumentId.from_str("EUR/USD.SIM"),
                Price(1.234, 4),
                Price(1.234, 4),
                Quantity(5, 0),
                Quantity(5, 0),
                i,
                i,
            )
            for i in range(batch_size)
        ]

        engine = _create_engine()
        engine.add_data(quotes)

        start = time.perf_counter()
        engine.run()
        stop = time.perf_counter()

        del engine
        del quotes
        gc.collect()
        processed += batch_size

        memory_usage = _get_memory_usage_gb()

        elapsed += stop - start

        row = {
            "processed": processed,
            "memory_usage_gb": memory_usage,
            "elapsed_secs": elapsed,
        }
        measurements = measurements.append(row, ignore_index=True)
    
    print(measurements)
    measurements.to_csv(path)
        
    
