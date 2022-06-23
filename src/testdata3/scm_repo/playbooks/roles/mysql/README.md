Mysql
=====

A role that deploys fully-working mysql server on OpenStack; it: 

* Opens `3306` port 
* Copies `pre` and `post` backup scripts. 

Role Variables
--------------

``MYSQL_SERVER_BACKUP_DIR`` --- a directory where database dumps temporarily stored. Please note that it will need to 
have enough free space to hold dumps of all databases on the server.
