# trailchat
Cloudtrail to Hipchat

TrailChat is a python AWS Lambda function that notifies a HipChat room if an S3 putobject event is triggered via CloudTrail. It is meant as
a simple monitoring mechanizm to see if there's any suspicious activity.

## Setup

You just need to copy `config.cfg.dist` to `config.cfg`. Also you need to have virtualenvwrapper installed.

`pip install -U virtualenvwrapper`

### IAM Role

The function will need an IAM Role with the default lambda permissions . The simplest approach is to create a new role and attach the following managed policy:

* AWSLambdaBasicExecutionRole

`fab lambda_add_perm`

### HipChat Integration

1. Sign into your HipChat account and navigate to "Integrations". 
1. Choose the room the nag messages should appear in
1. Click "Build your own"
1. Name the integration whatever, e.g. "Trailer", and click "Create".
The name you choose is what will identify the source of the messages in the HipChat room.
1. Copy the generated URL into config.cfg as the `notify_url` value.

### Create

`fab lambda_create`

### Update

`fab deploy`
