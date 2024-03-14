from minio import Minio
from pymongo import MongoClient
import os
from locust import User, task, between, Locust, TaskSet, events
import random, inspect, time, datetime, psutil, json

# Configuration for Minio installation.
aces = Minio(
    '10.100.54.154:9011',
    access_key='chesAccesskeyMinio',
    secret_key='chesSecretkey',
    secure=False,
)


# Configuration for filesystem logging.
records_file = "./records_minio.json"
save_to_file = True


# Function that creates a new log metric and stores it in MongoDB and/or the specified logging file.
def logMetric(operation, duration, size, bucketID, users, storageType, files=1):
    # Get the current process in order to isolate the CPU and RAM ussage of this client.
    currentProcess = psutil.Process(os.getpid())
    # Get the network adapters in order to measure network statistics.
    netAdapters = psutil.net_io_counters(pernic=True).keys()
    # Get the list of HDD and SSD drivers in order to measure storage statistics.
    diskDrives = psutil.disk_io_counters(perdisk=True).keys()

    # Get the readings of the network adapters (Full documentation here: https://psutil.readthedocs.io/en/latest/#psutil.net_io_counters).
    network = {k: psutil.net_io_counters(pernic=True)[k]._asdict() for k in netAdapters}
    # Get the readings of the CPU monitors (Full documentation here: https://psutil.readthedocs.io/en/latest/#psutil.cpu_percent).
    cpu = currentProcess.cpu_percent() / psutil.cpu_count()
    # Get the readings of the RAM monitors (Full documentation here: https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_percent).
    ram = currentProcess.memory_percent()
    # Get the readings of the HDD and SSD adapter monitors (Full documentation here: https://psutil.readthedocs.io/en/latest/#disks).
    diskUsage = psutil.disk_usage('/')
    diskMetrics = {k: psutil.disk_io_counters(perdisk=True)[k]._asdict() for k in diskDrives}

    # Create a new record of all metrics in JSON format.
    logDict = {"operation": operation, "duration": duration, "size": size, "bucketID": bucketID, "users": users,
               "network": network, "cpu": cpu, "ram": ram, "diskUsage": diskUsage, "diskMetrics": diskMetrics,
               "storage": storageType, "files": files,
               "timestamp": int(datetime.datetime.timestamp(datetime.datetime.now()))}

    if save_to_file:
        with open(records_file, 'a+') as logFile:
            logFile.write(json.dumps(logDict) + "\n")


# Function required by Locust. It handles the event of recording task completions and failures and sending metrics to the Locust service.
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
            # Event that handles the failure of a task.
            events.request_failure.fire(request_type="MINIO",  # request_type: The "family" of the task.
                                        name=task_name,  # name: The name of the task.
                                        response_time=total,  # response_time: The total time elapsed for this task.
                                        exception=e,
                                        # exception: The exception that is associated with the failure of this task.
                                        response_length=0)  # response_length: The result of this task.
        else:
            total = int((time.time() - start) * 1000)
            # Event that handles the success of a task.
            events.request_success.fire(request_type="MINIO",  # request_type: The "family" of the task.
                                        name=task_name,  # name: The name of the task.
                                        response_time=total,  # response_time: The total time elapsed for this task.
                                        response_length=(
                                            result if result is not None else 0))  # response_length: The result of this task.
        return result

    return wrapper


# A client is required by the Locust and it is a collection of tasks that a simulated user must perform during her lifecycle.
class LocustClient ():
    # A client must contain a host that is defined in the GUI provided by the Locust web interface on runtime.
    def __init__(self, host):
        try:
            host = host.split(':')
            self.host = str(host[0])
            self.port = int(host[1])
        except:
            self.host = None
            self.port = None

    # This function creates a new bucket in the Minio installation provided.
    def create_bucket(self, user):
        if not aces.bucket_exists(user.bucket_id):
            aces.make_bucket(user.bucket_id)
        return None

    #The tag stopwatch is used to define a task that we want to measure and record its activity.
    @stopwatch
    def write_small_files_aces(self, user):
        writeClockStart = datetime.datetime.now()
        filesSuccessCount = 0
        filesSuccessSize = 0
        # The set of test files is created during the user creation and is associated with each specific user object.
        for file in user.test_files:
            try:
                startClock = datetime.datetime.now()
                with open(file, 'rb') as data:
                    aces.put_object(user.bucket_id, file.split('/')[-1], data, os.stat(file).st_size, get_type(file))
                endClock = datetime.datetime.now()

                logMetric('write', int((endClock - startClock).total_seconds() * 1000), os.stat(file).st_size,
                          user.bucket_id, user.environment.runner.user_count, 'aces')
                filesSuccessCount += 1
                filesSuccessSize += os.stat(file).st_size
            except Exception as minExe:
                print(minExe)
                continue
        writeClockEnd = datetime.datetime.now()

        logMetric('writeMany', int((writeClockEnd - writeClockStart).total_seconds() * 1000),
                  filesSuccessSize, user.bucket_id, user.environment.runner.user_count, 'aces', filesSuccessCount)
        # After the new record is logged we return the total filesize in bytes that was processed in this task in order to be displayed in the Locust GUI.
        return filesSuccessSize

    # The tag stopwatch is used to define a task that we want to measure and record its activity.
    @stopwatch
    def read_small_files_aces(self, user):
        readClockStart = datetime.datetime.now()
        filesSuccessCount = 0
        filesSuccessSize = 0
        for file in user.test_files:
            try:
                response = None
                try:
                    startClock = datetime.datetime.now()
                    response = aces.get_object(user.bucket_id, file.split('/')[-1])
                    tempbytes = response.read()
                    endClock = datetime.datetime.now()
                    logMetric('read', int((endClock - startClock).total_seconds() * 1000),
                              os.stat(file).st_size, user.bucket_id, user.environment.runner.user_count, 'aces')
                    filesSuccessCount += 1
                    filesSuccessSize += os.stat(file).st_size
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
        logMetric('readMany', int((readClockEnd - readClockStart).total_seconds() * 1000),
                  filesSuccessSize, user.bucket_id, user.environment.runner.user_count, 'aces', filesSuccessCount)
        # After the new record is logged we return the total filesize in bytes that was processed in this task in order to be displayed in the Locust GUI.
        return filesSuccessSize

    # This function is performing clean up by deleting the bucket created during this task.
    def close_bucket(self, user):
        if aces.bucket_exists(user.bucket_id):
            objects = aces.list_objects(user.bucket_id, recursive=True)
            for obj in objects:
                aces.remove_object(user.bucket_id, obj.object_name)
            aces.remove_bucket(user.bucket_id)
        return None

# A function that retrieves a list of test files from the pre-defined folder.
def get_test_files(filepath, num_of_files):
    return random.sample(
        [os.path.join(filepath, f) for f in os.listdir(filepath) if os.path.isfile(os.path.join(filepath, f))],
        num_of_files)


# A function that retrieves the type of file in order to better process the associated request.
def get_type(file):
    end = file.split('.')[-1].lower()
    if end == 'gif':
        return "image/gif"
    elif end in ['jpg', 'jpeg']:
        return "image/jpeg"
    else:
        return "text/plain"


# Locust requires the definition of a simulated User that it can spawn according to our settings.
# This User is associated with a client and starts performing all specified tasks.
class ComparisorUser(User):
    # During the User's creation we are setting up some aspects that will follow her during her lifetime.
    def __init__(self, env):
        super(ComparisorUser, self).__init__(env)
        self.client = LocustClient(self.host)
        self.bucket_id = str(random.randint(0, 9999)) + "user" + str(random.randint(0, 9999))
        self.test_files = get_test_files('testImages/', 10)

    # Before starting her tasks, the bucket associated with this specific User needs to be created.
    def on_start(self):
        self.client.create_bucket(self)

    # The tag task defines a task that this user needs to perform.
    @task
    def write_small_files(self):
        self.client.write_small_files_aces(self)

    # The tag task defines a task that this user needs to perform.
    @task
    def read_small_files(self):
        self.client.read_small_files_aces(self)


    # When the User reaches the end of her lifecycle this function is called in order to perform clean up.
    def on_stop(self):
        self.client.close_bucket(self)

    # This is the time that this User needs to stay active, prohibiting the creation of a new User, after the end of her lifecycle.
    wait_time = between(0.5, 5)