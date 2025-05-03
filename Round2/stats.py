import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller
from scipy.stats import pearsonr

# Load data (replace with your file path)
data = pd.read_csv('your_data.csv', delimiter=';')

# Extract mid-prices for DJEMBES and CROISSANTS
djembes = data[data['product'] == 'DJEMBES'][['timestamp', 'mid_price']].rename(columns={'mid_price': 'djembes'})
croissants = data[data['product'] == 'CROISSANTS'][['timestamp', 'mid_price']].rename(columns={'mid_price': 'croissants'})

# Merge on timestamp
merged = pd.merge(djembes, croissants, on='timestamp', how='inner')