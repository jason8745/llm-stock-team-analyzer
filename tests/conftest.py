"""
Test configuration and shared fixtures.
"""
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_stock_data():
    """
    Create sample stock data for testing technical indicators.
    """
    np.random.seed(42)  # For reproducible tests
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    
    # Generate realistic stock data
    close_prices = 100 + np.cumsum(np.random.randn(50) * 0.5)
    high_prices = close_prices + np.random.uniform(0, 2, 50)
    low_prices = close_prices - np.random.uniform(0, 2, 50)
    volumes = np.random.randint(1000, 10000, 50)
    
    df = pd.DataFrame({
        'Date': dates,
        'Close': close_prices,
        'High': high_prices,
        'Low': low_prices,
        'Volume': volumes
    })
    
    return df
