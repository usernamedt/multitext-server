Daniil Zakhlystov

**Multi-user text editor - server app.**

Launch the server on ip address and port specified in launch parameters.
Requires python 3.7 or higher. Cross-platform.

Each user has its own directory in the users files directory. On startup
, server removes non-existing files and assigns non-indexed files in folders
 to to the corresponding users in database. So you can create a document in
  user folder and it will appear in the menu when user will login to the
   client application.


**Usage:**

launch.py [-h] [-i IP] [-p PORT] [-d DIR]

Optional arguments:

  -h, --help            show help message
  
  -i IP, --ip IP        ip address for server to listen
  
  -p PORT, --port PORT  port for server to listen
  
  -d DIR, --dir DIR     users files directory (relative path)


**Launch sample:**

python launch.py -i 127.0.0.1 -p 8080
