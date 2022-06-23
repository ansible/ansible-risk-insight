Sanity check
============

A role that performs basic health checks for your instance and if they fail sends you an email, optionally 
if they pass it will notify Dead Man's snitch.

Example configuration:

    SANITY_CHECK_DISK_SPACE_PERCENTAGE: 20
    
    SANITY_CHECK_LIVE_PORTS:
      - host: localhost
        port: 80
        message: "Oh no! Http is down"
        retries: 5
        retry_delay: 2
      - host: localhost
        port: 443
        message: "Oh no! Https is down"
    
    # If any of these return non-zero exit code whole check will fail
    SANITY_CHECK_COMMANDS:
      - command: echo 1
        message: "Echo broke, we are doomed!"


SANITY_CHECK_LIVE_PORTS
-----------------------

This section specifies which ports should be opened. Each record 
contain the following parameters (**bold** are mandatory parameters) 
 
* **host** (string) - hostname
* **port** (int) - port number
* **message** (string) - message to be shown if port is closed
* retries (int) - number of retry attempts, defaults to 2. Setting
  `retries` to zero or negative number will cause the port to be 
  accessed just once.
* retry_delay (float) - delay between retries (in seconds)
  
Note that port will be accessed `retries+1` times in the worst case, so 
time interval when the port should go opened is `retries*retry_delay`
seconds from first attempt.
