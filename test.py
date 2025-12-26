import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

fig, ax = plt.subplots()
t = ax.text(
    0.5, 0.5, "Berlin ÄÄÖÜÜÜ??ßßß",
    ha="center", va="center",
    fontsize=60,
    fontfamily="Times New Roman",
    color="none",  # no fill
)

t.set_path_effects([
    pe.Stroke(linewidth=2, foreground="black"),
    pe.Normal(),
])

ax.set_axis_off()
plt.show()