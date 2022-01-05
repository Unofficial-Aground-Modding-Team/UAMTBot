# UAMTBot
A bot with utility features, made for the Aground Modding discord server

# How to host locally
You would have to setup a Postgres Database, run the setup scripts, then possibly run some of the stuff in `src/utils/config.py` or `src/utils/database.py` to generate the users database.

# Disclaimer
The code is very, very quirky and unsafe in some places (more specifically, when it comes to SQL injection). 
**Do not use as a reference for other projects.**
By the way, yes, I am using json, sqlite and postgres all in one project.
