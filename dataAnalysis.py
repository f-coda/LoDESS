#from pymongo import MongoClient
import json, pandas as pd
#import minioTester, ipfsTester, bigchainTester
import sys


pd.set_option("display.max_columns", None)

print()
print("------------------------------------------ Data Analysis ------------------------------------------")
print()

#
# # Parent class for tester configurations.
# class testerConfig:
#     def __init__(self):
#         self.client = None
#         self.mongoURI = None
#         self.mongoDB = None
#         self.mongoCol = None
#         self.save_to_mongo = None
#         self.records_file = None
#         self.save_to_file = None
#
#
# # Class for the MinIO configuration.
# class minioConfig(testerConfig):
#     def __init__(self):
#         super().__init__()
#         self.client = minioTester.aces
#         self.mongoURI = minioTester.mongoURI
#         self.mongoDB = minioTester.mongoDB
#         self.mongoCol = minioTester.mongoCol
#         self.save_to_mongo = minioTester.save_to_mongo
#         self.records_file = minioTester.records_file
#         self.save_to_file = minioTester.save_to_file
#
#
# # Class for the IPFS configuration.
# class ipfsConfig(testerConfig):
#     def __init__(self):
#         super().__init__()
#         self.client = ipfsTester.client
#         # self.mongoURI = ipfsTester.mongoURI
#         # self.mongoDB = ipfsTester.mongoDB
#         # self.mongoCol = ipfsTester.mongoCol
#         # self.save_to_mongo = ipfsTester.save_to_mongo
#         self.records_file = ipfsTester.records_file
#         self.save_to_file = ipfsTester.save_to_file
#
#
# # Class for the BigChain configuration.
# class bigchainConfig(testerConfig):
#     def __init__(self):
#         super().__init__()
#         self.client = bigchainTester.bdb
#         # self.mongoURI = bigchainTester.mongoURI
#         # self.mongoDB = bigchainTester.mongoDB
#         # self.mongoCol = bigchainTester.mongoCol
#         # self.save_to_mongo = bigchainTester.save_to_mongo
#         self.records_file = bigchainTester.records_file
#         self.save_to_file = bigchainTester.save_to_file


# Function that flattens a multilevel dictionary, converting it into a singular level dictionary
# for better dataframe representation.
def flattenDict(complexDict):
    flatDict = {}
    for key in complexDict:
        if key == 'diskUsage':
            flatDict[key + '_total'] = complexDict[key][0]
            flatDict[key + '_used'] = complexDict[key][1]
            flatDict[key + '_free'] = complexDict[key][2]
            flatDict[key + '_percent'] = complexDict[key][3]
        elif type(complexDict[key]) is dict:
            for innerKey in complexDict[key]:
                if type(complexDict[key][innerKey]) is dict:
                    for innerKey2 in complexDict[key][innerKey]:
                        flatDict[key + '_' + innerKey + '_' + innerKey2] = complexDict[key][innerKey][innerKey2]
                else:
                    flatDict[key + '_' + innerKey] = complexDict[key][innerKey]
        else:
            flatDict[key] = complexDict[key]
    return flatDict


# Convert the JSON logging file into a pandas dataframe.
def logfileToPandas(filename):
    data = []
    try:
        with open(filename, 'r') as logfile:
            for line in logfile:
                try:
                    data.append(flattenDict(json.loads(line)))
                except Exception as readExe:
                    print(readExe)
    except Exception as fileExe:
        print(fileExe)
    #print (pd.DataFrame(data))
    return pd.DataFrame(data)

# Perform the analysis of data and print the output.
def analysis(dataframe, columnsOfInterest=None):
    if columnsOfInterest is None:
        # columnsOfInterest = ['duration', 'size', 'cpu', 'ram', 'diskUsage', 'network_eth0_bytes_sent',
        #                      'network_eth0_bytes_recv', 'network_eth0_packets_sent', 'network_eth0_packets_recv']
        columnsOfInterest = ['duration', 'size', 'cpu', 'ram', 'diskUsage_percent','network_veth37502bed_bytes_sent','network_veth37502bed_bytes_recv',
                             'network_vethde200747_packets_sent', 'network_vethde200747_packets_recv', 'diskMetrics_sda_write_time', 'diskMetrics_sda_busy_time']
    print(f'Stats for all operations:')
    print(dataframe[columnsOfInterest].describe())
    print()
    # sys.exit()
    for operation in dataframe['operation'].unique():
        print(f'Stats for "{operation}" operation:')
        print(dataframe.loc[dataframe['operation'] == operation][columnsOfInterest].describe())
        print()
    print()

#records_file= 'results/bigchaindb/distributed/records_bigchaindb.json'
records_file= sys.argv[1]
# A configuration needs to be initiated in order to get the correct logging file.
#mc = minioConfig()
# The analysis method takes a logging file as first argument and a list of columns to include in the analysis as a second argument.
analysis(logfileToPandas(records_file), None)

print()
print("--------------------------------------- End Of Data Analysis --------------------------------------")
print()