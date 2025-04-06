import matplotlib as plt
import pandas as pd

data = pd.read_csv("tutorial_data.csv", sep=';')
data = pd.DataFrame(data)

kelp_data = data[data["product"] == "KELP"]
kelp_data = kelp_data["timestamp", ]


print(kelp_data)