
<h1 align="center">
  <br>
  Multitext Server
  <br>
</h1>

<h4 align="center">CRDT-based multi-user collaborative console text editor written in Python.</h4>

<p align="center">
  <img src="./resources/demo.gif" alt="Demonstration">
</p>

## How To Use

To clone and run this application, you'll need Git and Python 3.7+ installed on your computer. From your command line:

```bash
# Clone this repository
$ git clone https://github.com/usernamedt/multitext-server

# Go into the repository
$ cd multitext-server

# Install dependencies
$ pip3 install -r requirements.txt

# Run the app
$ python3 launch.py -i this.server.ip.address -p port
```

Each user has its own directory in the users files directory. On startup
, server removes non-existing files and assigns non-indexed files in folders
 to to the corresponding users in database. So you can create a document in
  user folder and it will appear in the menu when user will login to the
   client application.
   
After successfull server setup, setup and use [multitext-client](https://github.com/usernamedt/multitext-client) on each client instance.

## License

MIT
