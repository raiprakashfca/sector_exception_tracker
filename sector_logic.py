# sector_logic.py
import pandas as pd

def identify_exceptions(df, threshold=1.0):
    df = df.copy()

    def is_exception(row):
        stock_chg = row['Stock % Change']
        sector_chg = row['Sector % Change']
        # Check if they are moving in opposite directions and exceed the threshold
        return (stock_chg * sector_chg < 0) and (abs(stock_chg - sector_chg) > threshold)

    df['Exception'] = df.apply(is_exception, axis=1)
    return df
