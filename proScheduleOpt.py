import pandas as pd
import numpy as np
import json
import time
from pyomo.environ import *
from datetime import datetime, timedelta
from pandas.tseries.offsets import Day, Hour, Minute
from pyomo.opt import SolverStatus, TerminationCondition
from math import isnan
from pyomo.util.infeasible import log_infeasible_constraints


# Optimal dispatch function
def getOptimalDispatch(modelInput):
    # Defining the model type
    model = ConcreteModel()
    # Taking the custom interval provided by the user.
    interval = modelInput['modelData']['customModelInterval(min)']

    # Defining the indices set for the model
    modelStartHour = datetime.strptime(modelInput['modelData']['hStart'], '%Y-%m-%d %H:%M:%S')
    modelEndHour = datetime.strptime(modelInput['modelData']['hEnd'], '%Y-%m-%d %H:%M:%S')
    dateTime = pd.date_range(modelStartHour, modelEndHour, freq='5min')

    # Setting the model parameters
    model.mIndex = Set(initialize=list(range(0, len(dateTime))))
    model.interval = Param(initialize=interval)
    model.solverPlatform = Param(initialize=modelInput['modelData']['solverPlatform'])
    model.solverName = Param(initialize=modelInput['modelData']['solverName'])
    model.TStamps = Param(model.mIndex, initialize=dict(zip(model.mIndex, dateTime)))

    # Setting the Storage Parameters
    model.socLow = Param(initialize=modelInput['storage']['socLow'])
    model.socHigh = Param(initialize=modelInput['storage']['socHigh'])
    model.powerRating = Param(initialize=modelInput['storage']['powerRating'])
    model.chargeEff = Param(initialize=modelInput['storage']['chargeEff'])
    model.dChargeEff = Param(initialize=modelInput['storage']['dChargeEff'])
    model.actPrice = Param(model.mIndex, initialize=dict(zip(model.mIndex, modelInput['operateData']['price'])))
    model.actLoad = Param(model.mIndex, initialize=dict(zip(model.mIndex, modelInput['operateData']['actLoad'])))

    # Logical constraints constants
    model.LogicalConstant = Param(initialize=100 * model.powerRating)
    model.LogicalConstant2 = Param(initialize=-100 * model.powerRating)

    # Defining the decision variables
    model.soc = Var(model.mIndex, within=NonNegativeReals)
    model.EIn = Var(model.mIndex, within=NonNegativeReals)
    model.EOut = Var(model.mIndex, within=NonNegativeReals)

    model.modeESS = Var(model.mIndex, within=Binary)
    model.modeESS2 = Var(model.mIndex, within=Binary)

    # Defining the objective function
    def maxRevRule(model):
        Revenue = sum(model.actPrice[idx] * (model.EOut[idx] - model.EIn[idx]) for idx in model.mIndex)
        return Revenue
    model.obj = Objective(rule=maxRevRule, sense=maximize)

    # Incoming energy constraint
    def EInRule(model, m):
        if model.modeESS[m] == 0:
            expr = model.EIn[m] == model.EGrid[m]
        else:
            Constraint.Skip
        return expr
    model.EinConstraint = Constraint(model.mIndex, rule=EInRule)

    # Outgoing energy constraint
    def EOutRule(model, m):
        if model.modeESS[m] == 1:
            expr = model.EOut[m] == model.EGrid[m]
        else:
            Constraint.Skip
        return expr
    model.EOutConstraint = Constraint(model.mIndex, rule=EOutRule)

    # Battery operation constraint
    def socRule(model, m):
        if (m == 0):
            expr = model.soc[m] == model.chargeEff * model.EIn[m] - model.EOut[m] / model.dChargeEff
        else:
            expr = model.soc[m] == model.soc[m - 1] + model.chargeEff * model.EIn[m] - model.EOut[m] / model.dChargeEff
        return expr

    model.socConstraint = Constraint(model.mIndex, rule=socRule)

    # SoC Limit Constraint.
    def socLimitRuleLow(model, m):
        expr = model.socLow * model.energyRating <= model.soc[m]
        return expr

    model.socLimitRuleLow = Constraint(model.mIndex, rule=socLimitRuleLow)

    def socLimitRuleHigh(model, m):
        expr = model.soc[m] <= model.socHigh * model.energyRating
        return expr

    model.socLimitRuleHigh = Constraint(model.mIndex, rule=socLimitRuleHigh)

    # Max charging power constraint
    def MaxChargingPowerRule(model, m):
        expr = model.EIn[m] * (60 / model.interval) <= model.powerRating
        return expr

    model.PMaxCh = Constraint(model.mIndex, rule=MaxChargingPowerRule)

    # Max Discharging power constraint
    def MaxDischargingPowerRule(model, m):
        expr = model.EOut[m] * (60 / model.interval) <= model.powerRating
        return expr

    model.PMaxDCh = Constraint(model.mIndex, rule=MaxDischargingPowerRule)

    # No simultaneous charging and discharging constraint for the ESS
    def CXD_ESSRule1(model, m):
        expr = model.EIn[m] + (1 - model.modeESS[m]) * model.LogicalConstant >= 0
        return expr

    model.CXD_ESS1 = Constraint(model.mIndex, rule=CXD_ESSRule1)

    def CXD_ESSRule2(model, m):
        expr = model.EOut[m] + (1 - model.modeESS[m]) * model.LogicalConstant2 <= 0
        return expr

    model.CXD_ESS2 = Constraint(model.mIndex, rule=CXD_ESSRule2)

    def CXD_ESSRule4(model, m):
        expr = model.EOut[m] + (1 - model.modeESS2[m]) * model.LogicalConstant >= 0
        return expr

    model.CXD_ESS4 = Constraint(model.mIndex, rule=CXD_ESSRule4)

    def CXD_ESSRule5(model, m):
        expr = model.EIn[m] + (1 - model.modeESS2[m]) * model.LogicalConstant2 <= 0
        return expr

    model.CXD_ESS5 = Constraint(model.mIndex, rule=CXD_ESSRule5)

    def modeESSVarExclusivityRule(model, m):
        expr = model.modeESS[m] + model.modeESS2[m] == 1
        return expr

    model.modeESSVarExclusivityConstraint = Constraint(model.mIndex, rule=modeESSVarExclusivityRule)

    # Solving the model
    if (value(model.solverPlatform) == 'NEOS'):
        # Solving the model using NEOS
        solver_manager = SolverManagerFactory('neos')
        opt = SolverFactory(value(model.solverName))
        opt.options['integrality'] = 5 * 10 ** (-8)
        start = time.clock()
        print('\nWaiting for the solution from the solver...')
        results = solver_manager.solve(model, opt=opt, tee=True)
    elif (value(model.solverPlatform) == 'Local'):
        # Solving the model using local solvers
        Solver = SolverFactory(value(model.solverName))
        start = time.clock()
        print('\nWaiting for the solution from the solver...')
        results = Solver.solve(model)
    if (results.solver.status == SolverStatus.ok):
        if (results.solver.termination_condition == TerminationCondition.optimal):
            print("\n\n***Optimal solution found***")
            print('maxRevenue:', round(value(model.obj), 2))
            print("Solver processing time(min) :", round((time.clock() - start) / 60, 2))
        else:
            print("\n\n***No optimal solution found***")
            if (results.solver.termination_condition == TerminationCondition.infeasible):
                print("Infeasible solution")
                print("Solver processing time(min) :", round((time.clock() - start) / 60, 2))
                exit()
    else:
        print("\n\n***Solver terminated abnormally***")
        print("Solver processing time(min) :", round((time.clock() - start) / 60, 2))
        exit()

    return model


def runHorizonModel(modelInput):
    solvedModel = getOptimalDispatch(modelInput)
    return solvedModel