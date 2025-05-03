import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller
from scipy.stats import pearsonr

# Aggregate price data
prices_day_1 = pd.read_csv("round-2-island-data-bottle/prices_round_2_day_-1.csv", sep=';')
prices_day_1 = pd.DataFrame(prices_day_1)
prices_day_2 = pd.read_csv("round-2-island-data-bottle/prices_round_2_day_0.csv", sep=';')
prices_day_2 = pd.DataFrame(prices_day_2)
prices_day_2.timestamp = prices_day_2.timestamp + 1000000
prices_day_3 = pd.read_csv("round-2-island-data-bottle/prices_round_2_day_1.csv", sep=';')
prices_day_3 = pd.DataFrame(prices_day_3)
prices_day_3.timestamp = prices_day_3.timestamp + 2000000

prices = pd.concat([prices_day_1, prices_day_2, prices_day_3])


# Aggregate trade data
"""trades_day_1 = pd.read_csv("round-1-island-data-bottle/trades_round_1_day_-2.csv", sep=';')
trades_day_1 = pd.DataFrame(trades_day_1)
trades_day_2 = pd.read_csv("round-1-island-data-bottle/trades_round_1_day_-1.csv", sep=';')
trades_day_2 = pd.DataFrame(trades_day_2)
trades_day_2.timestamp = trades_day_2.timestamp + 1000000
trades_day_3 = pd.read_csv("round-1-island-data-bottle/trades_round_1_day_0.csv", sep=';')
trades_day_3 = pd.DataFrame(trades_day_3)
trades_day_3.timestamp = trades_day_3.timestamp + 2000000
trades = pd.concat([trades_day_1, trades_day_2, trades_day_3])"""

start_ms = 100000# random.randint(0, 2900000)
end_ms = 200000 #start_ms + 100000

#Select KELP data
kelp_data = prices.loc[(prices["product"] == "KELP") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]
#Select RESIN data
resin_data = prices.loc[(prices["product"] == "RAINFOREST_RESIN") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]
#Select INK data
ink_data = prices.loc[(prices["product"] == "SQUID_INK") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]
#Select DJEMBES data
djembes_data = prices.loc[(prices["product"] == "DJEMBES") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]
#Select CROISSANTS data
croissants_data = prices.loc[(prices["product"] == "CROISSANTS") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]
#Select JAMS data
jams_data = prices.loc[(prices["product"] == "JAMS") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]
#Select PICNIC_BASKET1 data
basket1_data = prices.loc[(prices["product"] == "PICNIC_BASKET1") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]
#Select PICNIC_BASKET2 data
basket2_data = prices.loc[(prices["product"] == "PICNIC_BASKET2") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]

# Load data (replace with your file path)
data = prices

# Extract mid-prices for DJEMBES and CROISSANTS
djembes = data[data['product'] == 'PICNIC_BASKET2'][['timestamp', 'mid_price']].rename(columns={'mid_price': 'djembes'})
croissants = data[data['product'] == 'PICNIC_BASKET1'][['timestamp', 'mid_price']].rename(columns={'mid_price': 'croissants'})

# Merge on timestamp
merged = pd.merge(djembes, croissants, on='timestamp', how='inner')

corr, p_value = pearsonr(merged['djembes'], merged['croissants'])
print(f"Pearson Correlation: {corr:.3f} (p-value: {p_value:.3f})")

# Calculate spread (log difference)
merged['spread'] = np.log(merged['djembes']) - np.log(merged['croissants'])

# ADF test for stationarity
adf_result = adfuller(merged['spread'].dropna())
print(f"ADF Statistic: {adf_result[0]:.3f}")
print(f"p-value: {adf_result[1]:.3f}")
print("Critical Values:", {k: round(v, 3) for k, v in adf_result[4].items()})

"""#Display data as table
print(ink_data)
product = "INK"
data = pd.DataFrame()

if product == "KELP":
    data = kelp_data
elif product == "RESIN":
    data = resin_data
elif product == "INK":
    data = ink_data
elif product == "DJEMBES":
    data = djembes_data
elif product == "CROISSANTS":
    data = croissants_data
elif product == "PICNIC_BASKET1":
    data = basket1_data
elif product == "PICNIC_BASKET2":
    data = basket2_data


#Visualise
#plt.plot((data['timestamp']), data['mid_price'], 'b-', linewidth=0.5)
#plt.plot((data['timestamp']), data['bid_price_1'], 'g-', linewidth=0.5)
#plt.plot((data['timestamp']), data['ask_price_1'], 'r-', linewidth=0.5)

plt.plot((djembes_data['timestamp']), djembes_data['bid_price_1'], 'b-', linewidth=0.5)
plt.plot((croissants_data['timestamp']), croissants_data['bid_price_1'], 'g-', linewidth=0.5)
plt.plot((jams_data['timestamp']), jams_data['bid_price_1'], 'g-', linewidth=0.5)




# Create figure and primary axis
fig, ax1 = plt.subplots(figsize=(10, 6))

# Plot Djembes (left y-axis, blue)
color_djembes = 'tab:blue'
ax1.set_xlabel('Timestamp (ms)', fontsize=12)
ax1.set_ylabel('Djembes Price', color=color_djembes, fontsize=12)
ax1.plot(djembes_data['timestamp'], djembes_data['bid_price_1'],
         color=color_djembes, linestyle='-', linewidth=0.5, label='Djembes')
ax1.tick_params(axis='y', labelcolor=color_djembes)

# Create secondary y-axis for Croissants
ax2 = ax1.twinx()

# Plot Croissants (right y-axis, green)
color_croissants = 'tab:green'
ax2.set_ylabel('Croissants Price', color=color_croissants, fontsize=12)
ax2.plot(croissants_data['timestamp'], croissants_data['bid_price_1'],
         color=color_croissants, linestyle='-', linewidth=0.5, label='Croissants')
ax2.tick_params(axis='y', labelcolor=color_croissants)

# Title, legend, and grid
plt.title('Djembes vs. Croissants Prices Over Time', fontsize=14)

# Combine legends from both axes
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

plt.grid(alpha=0.3)
fig.tight_layout()
plt.show()"""


"""plt.title('Order Book Prices Over Time', fontsize=14)
plt.xlabel('Timestamp (ms)', fontsize=12)
plt.ylabel('Price', fontsize=12)
plt.legend()
plt.grid(alpha=0.3)
plt.show()"""