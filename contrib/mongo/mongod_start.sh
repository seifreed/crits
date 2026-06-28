#!/bin/sh
# Very basic script showing how to fork mongod.
# This also sets up a custom log file and sets the directory where the DB
# should be written to. The HTTP interface is disabled by default in modern
# MongoDB, and --nohttpinterface/--smallfiles were removed (3.6/4.2), so they
# are no longer passed here.
if [ -f /usr/local/bin/mongod ]; then
  /usr/local/bin/mongod --fork --logpath /data/logs/mongodb.log --logappend --dbpath /data/db
else
  mongod --fork --logpath /data/logs/mongodb.log --logappend --dbpath /data/db
fi
