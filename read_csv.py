import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("game_stats.csv", encoding="utf-8-sig", header=None)
df.columns = ["Distance (m)", "Time (sec)", "Avg Speed", "Nitros Used", "Police Spawned"]
df["Session"] = [f"Session {i+1}" for i in range(len(df))]

mean_dist   = df["Distance (m)"].mean()
median_dist = df["Distance (m)"].median()

df_sorted = df.sort_values(by="Distance (m)", ascending=False)

plt.figure(figsize=(10, 6))

bars = plt.bar(df_sorted["Session"], df_sorted["Distance (m)"])

for bar in bars:
    y = bar.get_height()
    plt.text(bar.get_x() + bar.get_width() / 2,
             y + 10,
             f"{y:.0f}",
             ha="center",
             fontsize=9)

plt.axhline(mean_dist,
            linestyle="--",
            linewidth=2,
            label=f"Mean = {mean_dist:.0f} m")
plt.axhline(median_dist,
            linestyle=":",
            linewidth=2,
            label=f"Median = {median_dist:.0f} m")

plt.xlabel("Session")
plt.ylabel("Distance (m)")
plt.title("Top Distances by Game Session\nwith Mean & Median Lines")
plt.xticks(rotation=45)
plt.grid(axis="y", linestyle="--", alpha=0.4)
plt.legend()
plt.tight_layout()
plt.show()
