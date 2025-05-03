import matplotlib.pyplot as plt
import pandas as pd

data = pd.read_csv("tutorial_data.csv", sep=';')
data = pd.DataFrame(data)

#Select KELP data
kelp_data = data.loc[data["product"] == "KELP", ["timestamp", "mid_price"]]
#Select RESIN data
resin_data = data.loc[data["product"] == "RAINFOREST_RESIN", ["timestamp", "mid_price"]]

#Display data as table
#print(resin_data)

#Plot data
plt.plot(kelp_data['timestamp'], kelp_data['mid_price'], 'b-', label='Kelp Mid Price', linewidth=0.5)
#plt.plot(resin_data['timestamp'], resin_data['mid_price'], 'g-', label='Resin Mid Price', linewidth=0.5)




# Customize
plt.title('KELP vs RESIN: Order Book Prices Over Time', fontsize=14)
plt.xlabel('Timestamp (ms)', fontsize=12)
plt.ylabel('Price', fontsize=12)
plt.legend()
plt.grid(alpha=0.3)
plt.show()


