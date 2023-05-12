# NDN Peer-to-Peer Network
This project aims to develop a NDN peer-to-peer network. The network architecture proposed in this project provides a scalable and reliable solution for the communication among self-driving vehicles.  Itconsists of a base layer using TCP sockets for reliable communication and an upper layer using NDN for information-centric communication.

**Base Layer – TCP Socket**

We use the TCP socket programming to realize the base layer connections. Each socket uniquely identifies one peer-to-peer connection. A single socket pool is used to manage all sockets to avoid collisions and facilitate management. Each time a node attempts to access the network, it broadcasts its IP address and port number to other nodes.
For each node, there are 6 slots used for different connections, which can be defined as 3 WAN slot and 3 LAN slots from concept aspects. A thread pool is used to manage these threads, synchronously or asynchronously. In addition, exception handling is set up for some cases, such as connection timeouts or disconnections.
All the steps and elements mentioned above are encapsulated underneath the upper NDN layer.

**Upper Layer – NDN**

The upper layer of the network is an NDN, the Named Data Networking. NDN breaks the host-centric connection mode of TCP/IP and becomes information-centric, by defining names for each piece of data. With NDN, the data will be independent of the physical location.
There are 2 types of packets during the transmission: interest packets and data packets. Each node has the function of sending, receiving, and routing. If one node tries to request data from another node, which is a consumer, it will send an interest packet and will receive a data packet in return. For the destination node, which is a producer, it will receive the interest packet and will send the data packet. For the nodes during the forwarding process, the router of each have to decide whether they need to receive the data or just forward it.

In NDN network, each router needs to maintain 3 tables: CS, PIT, and FIB.
•	CS (Content Store) – A cache table to store the data packets the router have already encountered.
•	PIT (Pending Interest Table) – This table holds the requests of the pending interest packet waiting for their corresponding data packet.
•	FIB (Forward Information Base) – This table manages the name of the data that can be reached along with the routing path that can be useful for transmission of interest packet forward.

If a consumer tries to request some data from a producer, the first thing to do is to send an interest packet, then search the CS table of its router to see if the name was stored in the CS before. If yes, directly return the content of data; if no, move to the next step. The next step is to record in the PIT which interface this interest packet enters, and at the same time, look up the FIB to decide who will this interest packet be forwarded to next.

**Sensors and Use Case**

The use case for this project is a network consisting of self-driving vehicles. There are 8 sensors in the network, including GPS, accelerometer, gyroscope, magnetometer, lidar, camera, ultrasonic, and radar. The sensors provide real-time data for the self-driving vehicles to communicate with each other and make decisions in real-time.

