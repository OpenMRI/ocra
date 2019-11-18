import matplotlib.pyplot as plt
import numpy as np
import time

x = np.linspace(1,50,10)
y = np.exp(-x*0.1)

plt.show()

ax = plt.gca()
ax.plot([], [])

for n in range(len(x)-1):
    print("x: ", x[n], " y: ", y[n])
    ax.clear()
    ax.plot(x[0:n+1], y[0:n+1])
    plt.draw()
    plt.pause(0.00001)
    time.sleep(1)
