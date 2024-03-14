#Requirements

#3. Host 127.0.0.1:9984

#BigchainDB imports
from bigchaindb_driver import BigchainDB
from bigchaindb_driver.crypto import generate_keypair
import time
#end

import os
from locust import User, task, between, Locust, TaskSet, events
import random, inspect, time, datetime, psutil, json

#Configuration for BigchainDB installation
bdb_root_url = '127.0.0.1:9984'
bdb = BigchainDB(bdb_root_url)

#Configuration for filesystem logging.
records_file = "./records_bigchaindb.json"
save_to_file = True
    
#Function that creates a new log metric and stores it in MongoDB and/or the specified logging file.
def logMetric(file, operation,duration,size,users,storageType,files=1):
    #Get the current process in order to isolate the CPU and RAM ussage of this client.
    currentProcess = psutil.Process(os.getpid())
    #Get the network adapters in order to measure network statistics.
    netAdapters = psutil.net_io_counters(pernic=True).keys()
    #Get the list of HDD and SSD drivers in order to measure storage statistics. 
    diskDrives = psutil.disk_io_counters(perdisk=True).keys()
    
    #Get the readings of the network adapters (Full documentation here: https://psutil.readthedocs.io/en/latest/#psutil.net_io_counters).
    network = {k: psutil.net_io_counters(pernic=True)[k]._asdict() for k in netAdapters}
    #Get the readings of the CPU monitors (Full documentation here: https://psutil.readthedocs.io/en/latest/#psutil.cpu_percent).
    cpu = currentProcess.cpu_percent()/psutil.cpu_count()
    #Get the readings of the RAM monitors (Full documentation here: https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_percent).
    ram = currentProcess.memory_percent()
    #Get the readings of the HDD and SSD adapter monitors (Full documentation here: https://psutil.readthedocs.io/en/latest/#disks).
    diskUsage = psutil.disk_usage('/')
    diskMetrics = {k: psutil.disk_io_counters(perdisk=True)[k]._asdict() for k in diskDrives}
    
    #Create a new record of all metrics in JSON format.
    logDict = {"operation":operation,"duration":duration,"size":size,"users":users,"network":network,"cpu":cpu,"ram":ram,"diskUsage":diskUsage,"diskMetrics":diskMetrics,"storage":storageType,"files":files,"timestamp":int(datetime.datetime.timestamp(datetime.datetime.now()))}
    
    if save_to_file:
        with open(records_file,'a+') as logFile:
            logFile.write(json.dumps(logDict)+"\n")
            
#Function required by Locust. It handles the event of recording task completions and failures and sending metrics to the Locust service.
def stopwatch(func):
    def wrapper(*args, **kwargs):
        # get task's function name
        previous_frame = inspect.currentframe().f_back
        _, _, task_name, _, _ = inspect.getframeinfo(previous_frame)

        start = time.time()
        result = None
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            total = int((time.time() - start) * 1000)
            #Event that handles the failure of a task.
            events.request_failure.fire(request_type="BDB", #request_type: The "family" of the task.
                                        name=task_name, #name: The name of the task.
                                        response_time=total, #response_time: The total time elapsed for this task.
                                        exception=e, #exception: The exception that is associated with the failure of this task.
                                        response_length=0) #response_length: The result of this task.
        else:
            total = int((time.time() - start) * 1000)
            #Event that handles the success of a task.
            events.request_success.fire(request_type="BDB", #request_type: The "family" of the task.
                                        name=task_name, #name: The name of the task.
                                        response_time=total, #response_time: The total time elapsed for this task.
                                        response_length=(result if result is not None else 0)) #response_length: The result of this task.
        return result

    return wrapper

class ACESClient:
    #A client must contain a host that is defined in the GUI provided by the Locust web interface on runtime.
    def __init__(self, host):
        try:
            host = host.split(':')
            self.host = str(host[0])
            self.port = int(host[1])
        except:
            self.host = None
            self.port = None

    #The tag stopwatch is used to define a task that we want to measure and record its activity.
    @stopwatch
    def write_small_files_aces(self,user):
        writeClockStart = datetime.datetime.now()
        filesSuccessCount = 0
        filesSuccessSize = 0
        #The set of test files is created during the user creation and is associated with each specific user object.
        for file in user.test_files:
            try:
                startClock = datetime.datetime.now()
                with open(file, 'rb') as data:

                    #Create the object
                    image_object = {
                        'data': {
                            'bucketid': user.bucket_id,
                            'filesplit_res': file.split('/')[-1],
                            'data_data': str(data.read()),
                            'st_size': os.stat(file).st_size,
                            'type': get_type(file)
                        }
                    }

                    #Create the metadata of the object
                    metadata = {'ftype': get_type(file)}

                    #Create the asset
                    prepared_creation_tx = bdb.transactions.prepare(
                        operation='CREATE',
                        signers=user.public_key,
                        asset=image_object,
                        metadata=metadata,
                    )

                    #Fullfilled transaction (sign to the object)
                    fulfilled_creation_tx = bdb.transactions.fulfill(prepared_creation_tx, private_keys=user.private_key)

                    #Send transaction to the node
                    sent_creation_tx = bdb.transactions.send_commit(fulfilled_creation_tx)

                endClock = datetime.datetime.now()
                logMetric('metrics.log', 'write', int((endClock - startClock).total_seconds()*1000),os.stat(file).st_size,user.environment.runner.user_count,'aces')
                filesSuccessCount+=1
                filesSuccessSize+=os.stat(file).st_size
            except Exception as minExe:
                print(minExe)
                continue
        writeClockEnd = datetime.datetime.now()

        logMetric('metrics.log','writeMany',int((writeClockEnd - writeClockStart).total_seconds()*1000),filesSuccessSize,user.environment.runner.user_count,'aces',filesSuccessCount)
        #After the new record is logged we return the total filesize in bytes that was processed in this task in order to be displayed in the Locust GUI.
        return filesSuccessSize
    

    #The tag stopwatch is used to define a task that we want to measure and record its activity.    
    @stopwatch
    def read_small_files_aces(self,user):
        readClockStart = datetime.datetime.now()
        filesSuccessCount = 0
        filesSuccessSize = 0
        for file in user.test_files:
            try:
                response = None
                try:
                    startClock = datetime.datetime.now()

                    tmp = file.split('/')[-1]
                    response = bdb.assets.get(search=tmp)
                    #response = aces.get_object(user.bucket_id, file.split('/')[-1])
                    #do we use tempbytes?
                    #tempbytes = response.read()
                    endClock = datetime.datetime.now()
                    logMetric('metrics.log','read',int((endClock - startClock).total_seconds()*1000),os.stat(file).st_size,user.environment.runner.user_count,'aces')
                    filesSuccessCount+=1
                    filesSuccessSize+=os.stat(file).st_size
                finally:
                    try:
                        response.close()
                        response.release_conn()
                    except:
                        None
            except Exception as minExe:
                print(minExe)
                continue
        readClockEnd = datetime.datetime.now()
        logMetric('metrics.log','readMany',int((readClockEnd - readClockStart).total_seconds()*1000),filesSuccessSize,user.environment.runner.user_count,'aces',filesSuccessCount)
        #After the new record is logged we return the total filesize in bytes that was processed in this task in order to be displayed in the Locust GUI.
        return filesSuccessSize

#TODO BigchaindDB user
class ACESUser(User):
    #During the User's creation we are setting up some aspects that will follow her during her lifetime.
    def __init__(self,env):
        super(ACESUser, self).__init__(env)
        self.client = ACESClient(self.host) 
        self.bucket_id = str(random.randint(0,9999))+"user"+str(random.randint(0,9999))
        self.test_files = get_test_files('testImages/', 10)
        #BigchainDB user keys
        bdb_keys = generate_keypair()
        self.public_key= bdb_keys.public_key
        self.private_key=bdb_keys.private_key

    
    #The tag task defines a task that this user needs to perform.
    @task
    def write_small_files(self):
        self.client.write_small_files_aces(self)
    
    #The tag task defines a task that this user needs to perform.
    @task
    def read_small_files(self):
        self.client.read_small_files_aces(self)
    
    #This is the time that this User needs to stay active, prohibiting the creation of a new User, after the end of her lifecycle.
    wait_time = between(0.5, 5) 

#A function that retrieves a list of test files from the pre-defined folder.
def get_test_files(filepath, num_of_files):
    return random.sample([os.path.join(filepath, f) for f in os.listdir(filepath) if os.path.isfile(os.path.join(filepath, f))],num_of_files)

#A function that retrieves the type of file in order to better process the associated request.
def get_type(file):
    end = file.split('.')[-1].lower()
    if end == 'gif':
        return "image/gif"
    elif end in ['jpg','jpeg']:
        return "image/jpeg"
    else:
        return "text/plain"
