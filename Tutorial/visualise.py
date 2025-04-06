import matplotlib.pyplot as plt
import pandas as pd

data = pd.read_csv("tutorial_data.csv", sep=';')
data = pd.DataFrame(data)

kelp_data = data.loc[data["product"] == "KELP", ["timestamp", "mid_price"]]

plt.plot(kelp_data['timestamp'], kelp_data['mid_price'], 'b-', label='Mid Price', linewidth=2)

# Customize
plt.title('KELP vs RESIN: Order Book Prices Over Time', fontsize=14)
plt.xlabel('Timestamp (ms)', fontsize=12)
plt.ylabel('Price', fontsize=12)
plt.legend()
plt.grid(alpha=0.3)
plt.show()


print(kelp_data)