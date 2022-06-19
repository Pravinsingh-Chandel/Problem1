import pandas as pd

storage = {
    "socLow": 1,
    "socHigh": 1,
    "powerRating": 1,
    "chargeEff": 1,
    "dChargeEff": 1
}

operateData = {
            "Price": [],
            "Target": []
}
modelData = {
            "hstart": "01-01-2020  00:00:00",
            "hend": "06-01-2020  23:45:00",
            "customModelInterval(min)": "custom_model_interval",
            "solverPlatform": "Platform",
            "solverName": "sName"
}


def getInput():
    fileName = 'Input.xlsx'
    plantinputDF = pd.read_excel(fileName, sheet_name='Schematic', index_col='Equipment')
    modelinputDF = pd.read_excel(fileName, sheet_name='modelData', index_col='horizon')
    operateinputDF = pd.read_excel(fileName, sheet_name='Operation')

    # creating model data
    modelData['hStart'] = str(modelinputDF.loc['horizon1', 'hstart'])
    modelData['hEnd'] = str(modelinputDF.loc['horizon1', 'hend'])
    modelData['customModelInterval(min)'] = (modelinputDF.loc['horizon1', 'customModelInterval(min)']).item()
    modelData['solverName'] = (modelinputDF.loc['horizon1', 'solverName'])
    modelData['solverPlatform'] = (modelinputDF.loc['horizon1', 'solverPlatform'])

    # creating plant data
    storage['powerRating'] = (plantinputDF.loc['Storage', 'Rated Power']).item()
    storage['chargeEff'] = (plantinputDF.loc['Storage', 'Charge Efficiency']).item()
    storage['dChargeEff'] = (plantinputDF.loc['Storage', 'Discharge Efficiency']).item()
    storage['socLow'] = (plantinputDF.loc['Storage', 'socLow']).item()
    storage['socHigh'] = (plantinputDF.loc['Storage', 'socHigh']).item()

    # Creating operation data
    operateData['price'] = operateinputDF['price']
    operateData['actLoad'] = operateinputDF['load']

    # Combining all inputs in one dictionary 'modelInput'
    modelInput = {
        'storage': storage, 'modelData': modelData, 'operateData': operateData
    }
    return modelInput
