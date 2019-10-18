import numpy as np

class myFunctions:

    def mySin(x):
        return 5*np.sin(12*np.pi*x)
    
    def myCos(x):
        return 5*np.cos(12*np.pi*x)
    
    def myJump(x):
        if x<2 or x>3:
            return 0
        else:
            return 1
    
    def mySinJump(x):
        if x<2 or x>3:
            return 0
        else:
            return 5*np.sin(12*np.pi*x)
        
    def mySinc(x):
        return 5*np.sinc(12*np.pi*x)