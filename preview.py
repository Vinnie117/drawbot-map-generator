from pyaxidraw import axidraw 

# Estimate how long the plot will take to draw

file = "maps/koeln_overlay.svg"
print("PLOTTING: " + file)

ad = axidraw.AxiDraw()
ad.plot_setup(file)

ad.options.speed_pendown = 50
ad.options.preview = True
ad.options.report_time = True
ad.options.reordering = 2

ad.plot_run()
