import numpy as np
import pandas as pd
from pyomo.environ import *
from datetime import datetime
from inputDataStr import storage


def getSolution(solvedModel, horizonStartDate, horizonEndDate):
    # Storing the model solution in an numpy array
    solArray = np.zeros((len(solvedModel.TStamps), 10))
    for i in range(0, solArray.shape[0]):
        solArray[i][0] = value(solvedModel.P1aPow[i] * 10)
        solArray[i][1] = value(solvedModel.P1bPow[i] * 10)
        solArray[i][2] = value(solvedModel.renProd[i])
        solArray[i][3] = value(solvedModel.gridPow[i])
        solArray[i][4] = value(solvedModel.energyRate[i])
        solArray[i][5] = value(solvedModel.gridPow[i]) * value(solvedModel.energyRate[i])
        solArray[i][6] = value(solvedModel.T1Level[i])
        solArray[i][7] = value(solvedModel.P1aFlow[i] * 10)
        solArray[i][8] = value(solvedModel.P1bFlow[i] * 10)
        solArray[0][9] = value(solvedModel.pGridMax)
    solDF = pd.DataFrame(solArray, columns=['P1a Power', 'P1b Power', 'RE_Production', 'Grid Power', 'Energy Rate',
                                            'Energy Cost', 'T1Level', 'P1a Flow', 'P1b Flow',
                                            'pGridMAx Value'])

    # Inserting datetime stamps into starting of the dispatch dataframe
    modelStartHour = datetime.strptime(horizonStartDate, '%d-%m-%Y %H:%M:%S')
    modelEndHour = datetime.strptime(horizonEndDate, '%d-%m-%Y %H:%M:%S')

    # Generating the timestamps for the model interval
    intervalDateTime = pd.date_range(modelStartHour, modelEndHour, freq='15min')
    solDF.insert(0, 'Time', intervalDateTime)

    # Suppress warning - "A value is trying to be set on a copy of a slice from a DataFrame" Or use 'loc' method to
    # store the data into the dataframe
    pd.options.mode.chained_assignment = None

    ActOpDF = pd.DataFrame(np.zeros((5, 2)), columns=['Equipment', 'Running Hours'])
    # P1a Output
    ActOpDF['Equipment'][0] = 'Pump P1a'
    ActOpDF['Running Hours'][0] = sum(solDF['P1a Power']) / (4 * equipInputs['ratPowP1'])

    # P1b Output
    ActOpDF['Equipment'][1] = 'Pump P1b'
    ActOpDF['Running Hours'][1] = sum(solDF['P1b Power']) / (4 * equipInputs['ratPowP1'])

    # Exporting data to an excel workbook
    with pd.ExcelWriter('outputData.xlsx') as writer:
        solDF.round(2).to_excel(writer, sheet_name='Dispatch')
        ActOpDF.round(2).to_excel(writer, sheet_name='Operation Data')

    # Returning the dispatch dataframe
    return solDF
