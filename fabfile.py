#!/usr/bin/env python
from __future__ import with_statement
import os
from fabric.api import settings, local
from fabric.api import env, lcd
from fabric.api import task, prefix
from ConfigParser import ConfigParser

BASE_PATH = os.path.dirname(__file__)

ZIP_FILE = 'trail_log.zip'
ZIP_PATH = os.path.join(BASE_PATH, ZIP_FILE)

config = ConfigParser()
config.read('config.cfg')
AWS_REGION = config.get('aws', 'region')
AWS_ROLE = config.get('aws', 'role')
AWS_SOURCE_ARN = config.get('aws', 'source_arn')
AWS_SOURCE_ACCOUNT = config.get('aws', 'source_account')
PROFILE = config.get('aws', 'profile')
LAMBDA_FUNCTION = 'trail_log'
LAMBDA_HANDLER = 'lambda_handler'
LAMBDA_FILE = 'trail_log.py'

env.source_virtualenvwrapper = 'source /usr/local/bin/virtualenvwrapper.sh'
VENV_NAME = "lambdaenv"


class FabricException(Exception):
    pass


@task
def pre_venv():
    with prefix(env.source_virtualenvwrapper):
        with settings(abort_exception=FabricException):
            try:
                local('workon {}'.format(VENV_NAME))
            except FabricException:
                local('mkvirtualenv {}'.format(VENV_NAME))
            with prefix('workon {}'.format(VENV_NAME)):
                local('pip install -r req.txt')


@task
def clean():
    for target in [ZIP_FILE]:
        local('rm -rf {}'.format(target))


@task(alias='zip')
def make_zip():
    clean()
    local('zip -9 {} {}'.format(
        ZIP_PATH,
        ' '.join([LAMBDA_FILE, 'config.cfg']),
        )
    )
    with prefix(env.source_virtualenvwrapper):
        with prefix('workon {}'.format(VENV_NAME)):
            virtualenv_libpath = local("echo $VIRTUAL_ENV", capture=True)
            with lcd(os.path.join(
                virtualenv_libpath,
                'lib/python2.7/site-packages'
                )
            ):
                local('zip -r9 {} *'.format(ZIP_PATH))


@task
def lambda_create():
    make_zip()
    local('aws lambda create-function --function-name {} '
          '--region {} --role {} --handler {} --runtime python2.7 '
          '--profile {} --timeout {} --memory-size {} '
          '--zip-file fileb://{}'.format(
              LAMBDA_FUNCTION,
              AWS_REGION,
              AWS_ROLE,
              LAMBDA_HANDLER,
              PROFILE,
              30, 256,
              ZIP_FILE))


@task
def lambda_add_perm():
    local('aws lambda add-permission --function-name {} '
          '--region {} --source-arn {} '
          '--source-account {} '
          '--action "lambda:InvokeFunction" '
          '--profile {}'.format(
              LAMBDA_FUNCTION,
              AWS_REGION,
              AWS_SOURCE_ARN,
              AWS_SOURCE_ACCOUNT,
              PROFILE))


@task(alias='deploy')
def lambda_update():
    make_zip()
    local('aws lambda update-function-code --function-name {} '
          '--zip-file fileb://{}'.format(LAMBDA_FUNCTION, ZIP_FILE))


@task
def lambda_test():
    local('aws lambda invoke --invocation-type RequestResponse '
          '--function-name {} '
          '--region {} '
          '--payload file://{} '
          '--profile {} response.txt'.format(
              LAMBDA_FUNCTION,
              AWS_REGION,
              'event.json',
              PROFILE,
          ))
