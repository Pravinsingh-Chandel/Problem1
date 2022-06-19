# import numpy as np
# import pandas as pd
# import json
from inputDataStr import getInput, modelData
from proScheduleOpt import runHorizonModel
from outputData import getSolution
# from plotData import plotDispatchData

# Defining the function to run the model
def runModel():

    # Getting the input for running the horizon model
    rawInput = getInput()
    # Running the horizon model
    solvedModel = runHorizonModel(rawInput)
    # Printing the solution to excel
    # dispatchDF = getSolution(solvedModel, modelData['hstart'], modelData['hend'])
    # Plotting the dispatch data
    # plotDispatchData(dispatchDF,modelData['hStart'], modelData['hEnd'])


# Calling the function to run the model
runModel()
