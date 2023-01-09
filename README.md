# Installation

To run this inside of a Docker container the following steps need to be executed.

* Clone the repository by executing `git clone https://github.com/sm48337/wargame.git`
* Run this command inside of the directory to build the image `docker build -t wargame .`
* Run this command to run the server `docker run -p 5000:5000 wargame`

The application should be available on `http://127.0.0.1:5000/`.
