# AutoComputeOptimizer
Easy to configure automation to automatically apply AWS Compute Optimizer recommendations on EC2 instances
It uses CloudFormation, Lambda (Python 3.9), CloudWatch Events and AWS Compute Optimizer (Compute Optimizer should be already working on the account)

You can select the day to check the recommendatios, set the time when should be apply and the type of recommendations: Overprovisioned, Underprovisioned or Both.

You can add Exceptions to never change an EC2 to a specific type, you can mark exceptions of family and size, Ex:  t3, small, m4.large

You have to define a TAG to select the EC2 Instances affected by the Automation. You can set SNS Notifications for this automation.

If it's not working on your Region create an Issue and I will fix it.

> Version 2.2.0

### Files:
- autoComputeOptimizer-template.yml, CloudFormation template to Run in your account, it is already in a public S3 bucket

- autocomputeoptimizer.py, Lambda code that actually do the job of implementing the recommendations, source code only for reviewing

- autocomputeoptimizer.zip, Zip file used by the template to deploy de Lambda, it is already in a public S3 Bucket

## How To Deploy
Use AWS CloudFormation to deploy the following template:

https://higher-artifacts.s3.amazonaws.com/solutions/autoComputeOptimizer-template.yml

### Parameters:
- *Env Tag*, use to identified the components of the template

- *Selection Tag Key*, sets the Tag used to identify the EC2 Instances

- *Selection Tag Value*, sets the Value of the Tag to identify the EC2 Instances

- *Day*, specify the day of the week the recommendations will be applied (Mon-Sun)

- *Time*, specify at what time the changes to the EC2 Instances will occur (downtime requiered) (UTC 24 hours syntax)

- *Default Recommendation Type*, specify which kind of recommendations to apply: Underprovisioned, Overprovisioned, Both

- *Tolerable Risk*, select the maximum tolerable Risk of the recommendation to apply

- *Exceptions*, you can add instance types, families or sizes to NOT use, for example: t2.nano, small, t3 

- *Email Address*, e-mail address to receive notifications of the implemmented recommendations

`If you edit the template remember to use LF end of lines.`

`Update KMS user policy if you find troubles starting again the instances.`

#### Notes:

- Function DOES modify EC2 Instances types (this will require a reboot) 

- Function DOES NOT modify EC2 Instances of an AutoScaling Group

- You can set a Tag Key and Value to select the group of EC2 Instances to be evaluated

- UPDATE: Now you can override the behaviour per instance with:
-- Selection Tag Values of ACOO-OVER to apply Oversized recomendations, ACOO-UNDER to apply Undersized recomendations, ACOO-BOTH to apply both recommendations

## To-Do
- Make a more restrict EC2 and KMS policy for the Lambda

- A better error management

- Evaluate the AutoScaling Group Recommendations

- Improve SNS Notifications
