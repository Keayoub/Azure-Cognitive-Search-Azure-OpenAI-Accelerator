# Setup

Note: Python 3.10+ is required.

A simple way to set up the environment is to use `venv`:

```sh
# Initializes the virtual environment
$ cd common
$ python3 -m venv venv
$ source venv/bin/activate

# Checks that the virtual environment is activated
$ which python # Should return the path to a binary in the venv folder
$ which pip    # Should return the path to a binary in the venv folder

# Installing the requirements
$ pip install -r requirements.txt

# Deactivating the virtual environment
$ deactivate
```
