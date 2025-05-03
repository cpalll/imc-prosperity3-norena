import matplotlib.pyplot as plt
import pandas as pd
import random

# Aggregate price data
prices_day_1 = pd.read_csv("round-1-island-data-bottle/prices_round_1_day_-2.csv", sep=';')
prices_day_1 = pd.DataFrame(prices_day_1)
prices_day_2 = pd.read_csv("round-1-island-data-bottle/prices_round_1_day_-1.csv", sep=';')
prices_day_2 = pd.DataFrame(prices_day_2)
prices_day_2.timestamp = prices_day_2.timestamp + 1000000
prices_day_3 = pd.read_csv("round-1-island-data-bottle/prices_round_1_day_0.csv", sep=';')
prices_day_3 = pd.DataFrame(prices_day_3)
prices_day_3.timestamp = prices_day_3.timestamp + 2000000

prices = pd.concat([prices_day_1, prices_day_2, prices_day_3])


# Aggregate trade data
# Aggregate price data
trades_day_1 = pd.read_csv("round-1-island-data-bottle/trades_round_1_day_-2.csv", sep=';')
trades_day_1 = pd.DataFrame(trades_day_1)
trades_day_2 = pd.read_csv("round-1-island-data-bottle/trades_round_1_day_-1.csv", sep=';')
trades_day_2 = pd.DataFrame(trades_day_2)
trades_day_2.timestamp = trades_day_2.timestamp + 1000000
trades_day_3 = pd.read_csv("round-1-island-data-bottle/trades_round_1_day_0.csv", sep=';')
trades_day_3 = pd.DataFrame(trades_day_3)
trades_day_3.timestamp = trades_day_3.timestamp + 2000000
trades = pd.concat([trades_day_1, trades_day_2, trades_day_3])

start_ms = random.randint(0, 2900000)
end_ms = start_ms + 10000

#Select KELP data
kelp_data = prices.loc[(prices["product"] == "KELP") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]
#Select RESIN data
resin_data = prices.loc[(prices["product"] == "RAINFOREST_RESIN") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]
#Select INK data
ink_data = prices.loc[(prices["product"] == "SQUID_INK") & (prices["timestamp"] > start_ms) & (prices["timestamp"] < end_ms)]

#Display data as table
print(ink_data)
product = "INK"
data = pd.DataFrame()

if product == "KELP":
    data = kelp_data
elif product == "RESIN":
    data = resin_data
elif product == "INK":
    data = ink_data


#Visualise
plt.plot((data['timestamp']), data['mid_price'], 'b-', linewidth=0.5)
plt.plot((data['timestamp']), data['bid_price_1'], 'g-', linewidth=0.5)
plt.plot((data['timestamp']), data['ask_price_1'], 'r-', linewidth=0.5)


#plt.plot(ink_data['timestamp'], ink_data['mid_price'], 'b-', label='Ink Mid Price', linewidth=0.5)



plt.title('Order Book Prices Over Time', fontsize=14)
plt.xlabel('Timestamp (ms)', fontsize=12)
plt.ylabel('Price', fontsize=12)
plt.legend()
plt.grid(alpha=0.3)
plt.show()