# LoDESS: Locust-Driven Performance Evaluation of Storage Systems

The provided code utilizes the [Locust](https://locust.io/) load testing tool to assess the performance of three distinct storage systems: [MinIO](https://min.io/), [BigchainDB](), and [IPFS](https://ipfs.tech/). 

Specifically, it orchestrates simulated user behavior to conduct performance tests focusing on read and write operations. Through custom Locust scripts, the code generates realistic workloads to stress the systems under evaluation, recording various performance metrics.

**Metrics**:
-  **Duration**: The duration of each test scenario, indicating the time taken to complete the simulated workload.
    
- **Size**: The size of data transferred or processed during the test, reflecting the volume of data involved in read and write operations.
    
- **CPU**: The CPU utilization, indicating the extent to which the CPU is utilized during the test, providing insights into system processing capabilities.
    
- **RAM**: The RAM (memory) utilization, showcasing the amount of memory consumed during the test, crucial for evaluating memory-intensive operations and potential bottlenecks.
    
- **Disk Usage Percent**: The percentage of disk space in use, offering insights into storage system capacity and potential constraints.
    
- **Network_sent/recv**: The number of bytes sent and received over the network interface, indicating network activity during the test and assessing network performance.
    
- **Network_sent/recv**: The number of packets sent and received over the network interface, providing finer-grained details about network traffic.
    
- **DiskMetrics_sda_write_time**: The time taken for disk write operations, reflecting the efficiency of write operations and disk performance.
    
- **DiskMetrics_sda_busy_time**: The amount of time the disk is busy processing requests, indicating disk utilization and potential performance bottlenecks related to disk access.

## Installation  
  
Install locust: `python3 -m pip install locust`

## MinIO

```docker pull minio/minio:latest```

Setup the endpoint and credentials in ```minioTester.py```

```python
aces = Minio(  
  'IP:PORT',  
  access_key='youraccesskey',  
  secret_key='yoursecretkey',  
  secure=False,  
)
```

## BigchainDB

```  
docker pull bigchaindb/bigchaindb:all-in-one  
```  

For more info, please have a look [here](https://docs.bigchaindb.com/en/latest/installation/node-setup/all-in-one-bigchaindb.html ) .
  
```
docker run \
  --detach \
  --name bigchaindb \
  --publish 9984:9984 \
  --publish 9985:9985 \
  --publish 27017:27017 \
  --publish 26657:26657 \
  --volume $HOME/bigchaindb_docker/mongodb/data/db:/data/db \
  --volume $HOME/bigchaindb_docker/mongodb/data/configdb:/data/configdb \
  --volume $HOME/bigchaindb_docker/tendermint:/tendermint \
  bigchaindb/bigchaindb:all-in-one
```

Install BigchainDB Python [drivers](https://docs.bigchaindb.com/projects/py-driver/en/latest/quickstart.html) .

Setup the `bdb_root_url` in `bigchainTester.py`.

## IPFS

```  
docker pull ipfs/go-ipfs:v0.7.0-rc1  
```  
  
Create two folders and assign them to arbitrary locations:  
  
```  
export ipfs_staging=</absolute/path/to/somewhere/>  
export ipfs_data=</absolute/path/to/somewhere_else/>  
```  

```  
docker run -d --name ipfs_host -v $ipfs_staging:/export -v $ipfs_data:/data/ipfs -p 4001:4001 -p 4001:4001/udp -p 127.0.0.1:8080:8080 -p 127.0.0.1:5001:5001 ipfs/go-ipfs:v0.7.0-rc1  
```

    host: 127.0.0.1:8080

## Locust

### Single node
`locust -f ./[file].python`

### Distributed load generation

Start one instance of Locust in master mode using the `--master` flag and multiple worker instances using the `--worker` flag. 

If the workers are not on the same machine as the master you have to use `--master-host` to point them to the IP/hostname of the machine running  the master.

**Example**:

Start locust in master mode:
`locust -f [file].py --master`

And then on each worker (replace 192.168.0.14 with the IP of the master machine, or leave out the parameter altogether if your workers are on the same machine as the master):

`locust -f [file].py --worker --master-host=192.168.0.14`

For optimal performance, the number of slaves on the local machine should not exceed the number of CPU cores.

See [this](https://docs.locust.io/en/stable/running-distributed.html) for more options.


### Running Locust without the web UI

Example: 
`locust -f locust_files/[file].py --headless -u 20 -r 20`

- -u specifies the number of Users to spawn, and
- -r specifies the spawn rate (number of users to start per second).

## Example Usage

**MinIO**

- Open a terminal and start Locust using the following command: ```locust -f ./minioTester.py```
- Locust will initiate a web interface accessible at http://0.0.0.0:8089
- In the Locust GUI, specify the desired parameters:: Number of users (peak concurrency), Spawn rate (users started/second) and Host of minio
- Click the "Start swarming" button to commence the load testing process
- Once the testing process is complete, a file named `records_minio.json` will be generated
- Execute`python3 dataAnalysis.py records_minio.json`  to analyze the gathered data and obtain statistics regarding the operations

## Note
  
`dataAnalysis.py` provides some statistics in the terminal and takes as input the `.json` file generated after the completion of Locust tester. 

Based on the OS, the `columnsOfInterest` is possible to change. 

```python
columnsOfInterest = ['duration', 'size', 'cpu', 'ram',
'diskUsage_percent','network_veth37502bed_bytes_sent','network_veth37502bed_bytes_recv',  
'network_vethde200747_packets_sent', 'network_vethde200747_packets_recv',
'diskMetrics_sda_write_time', 'diskMetrics_sda_busy_time']
  ```

If you encounter any errors during the execution of `python3 dataAnalysis.py [file].json` please review the generated .json file and check the `keys` to match with the `keys` on the `columnsOfInterest` list.

