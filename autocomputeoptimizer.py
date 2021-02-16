# igarcia 2021-02
# Version 2.1.0
# Automation for Compute Optimizer Recommendations
# It will change the EC2 Instance Type to a Recommendation of the AWS Compute Optimizer Service and send an email about it
# It won't do anything to AutoScaling Group's Instances
# You can set a TAG Value for the instances that this Lambda can manage
# IMPORTANT: your EC2 instance should endure a restart!

# UPDATE
# Now you can override the behaviour per instance with TAGBUSQUEDA's values of ACOO-OVER, ACOO-UNDER, ACOO-BOTH

import os
import json
import boto3

RISK = os.environ['RISK'] #de 0 a 5, 0 es sin riesgo y 5 es mucho riesgo (No Risk, Very Low, Low, Medium, High, Very High)
TYPE = os.environ['TYPE'] # Overprovisioned, Underprovisioned or Both
TAGBUSQUEDA = os.environ['TAGBUSQUEDA']
TAGVALOR = os.environ['TAGVALOR']
TOPIC = os.environ['TOPIC']
CORREO = os.environ['CORREO']
MENSAJE = ""
OVERRIDES = ("ACOO-OVER","ACOO-UNDER","ACOO-BOTH")
risk_text = {"0":"No Risk", "1":"Very Low Risk", "2":"Low Risk", "3":"Medium Risk", "4":"High Risk", "5":"Very High Risk"}

ec2 = boto3.resource('ec2')
co_client = boto3.client('compute-optimizer')
sns = boto3.resource('sns')

def review_compute_optimizer_recos(instance):
	global MENSAJE
	cambio = 0
	response = ""
	ec2_id = instance['instanceArn'].split('/')[1] #Instance ID
	ec2_name = instance['instanceName']
	to_do = False # Flag to determine if Instance will be examined
	tag_value = "" # To check for overrides

	ec2_instance = ec2.Instance(ec2_id)
	ec2_prev_type = ec2_instance.instance_type
	ec2_tags = ec2_instance.tags
	for tag in ec2_tags:
		if tag['Key'] == TAGBUSQUEDA:
			if tag['Value'] == TAGVALOR:
				tag_value = TYPE			# The type on Recommendation to apply
			elif tag['Value'] in OVERRIDES:
				tag_value = tag['Value']	# The override Recommendation to apply	

	# Revision sobre los OVERRIDES
	# TYPE = ['Underprovisioned','Overprovisioned', 'Both']
	# OVERRIDES = ACOO-OVER, ACOO-UNDER, ACOO-BOTH
	# instance['finding'] = 'OVER_PROVISIONED'
	if tag_value[0:4].upper() == instance['finding'][0:4].upper() or tag_value[0:4].upper() == "BOTH":
		to_do = True
	else:
		to_do = False

	if tag_value in OVERRIDES:
		if tag_value[5:9].upper() == instance['finding'][0:4].upper() or tag_value[5:9].upper()  == "BOTH":
			to_do = True
		else:
			to_do = False

	if to_do:
		for option in instance['recommendationOptions']:
			ec2_new_type = option['instanceType']
			if (int(option['performanceRisk']) <= int(RISK)) and (ec2_prev_type != ec2_new_type): # El riesgo debe ser aceptable y el tipo de Instancia debe cambiar
			    #Hacer Cambio Tipo de Instancia
				if ec2_instance.state['Name'] == 'stopped':
					try:
						response = ec2_instance.modify_attribute(InstanceType={'Value':ec2_new_type})
						response = ec2_instance.start()
						response = ec2_instance.wait_until_running()
						cambio = 1
						MENSAJE = MENSAJE + "Info:   Instance " + ec2_name + " changed to " + ec2_new_type + "\n"
						print("Se modificó Instancia {} - {} de {} a tipo {} ".format(ec2_id, ec2_name, ec2_prev_type, ec2_new_type))
						break
					except:
						ec2_instance.stop()
						ec2_instance.wait_until_stopped()
						ec2_instance.modify_attribute(InstanceType={'Value':ec2_prev_type})
						ec2_instance.start()
						cambio = 0
						MENSAJE = MENSAJE + "Error:  Instance " + ec2_name + " NOT changed to " + ec2_new_type + "\n"
						print(response)
						print("No se puedo modificar Instancia {} - {} a tipo {} ".format(ec2_id, ec2_name, ec2_new_type))
						break
				elif ec2_instance.state['Name'] == 'running':
					try:
						response = ec2_instance.stop()
						response = ec2_instance.wait_until_stopped()
						response = ec2_instance.modify_attribute(InstanceType={'Value':ec2_new_type})
						response = ec2_instance.start()
						response = ec2_instance.wait_until_running()
						cambio = 1
						MENSAJE = MENSAJE + "Info:   Instance " + ec2_name + " changed to " + ec2_new_type + "\n"
						print("Se modificó Instancia {} - {} de {} a tipo {} ".format(ec2_id, ec2_name, ec2_prev_type, ec2_new_type))
						break
					except:
						ec2_instance.stop()
						ec2_instance.wait_until_stopped()
						ec2_instance.modify_attribute(InstanceType={'Value':ec2_prev_type})
						ec2_instance.start()
						cambio = 0
						MENSAJE = MENSAJE + "Error:  Instance " + ec2_name + " NOT changed to " + ec2_new_type + "\n"
						print(response)
						print("No se puedo modificar Instancia {} - {} a tipo {} ".format(ec2_id, ec2_name, ec2_new_type))
						break
			else:
				print("Opción {} recomendada no viable para instancia {} - {} ".format(ec2_new_type, ec2_id, ec2_name))

		if response == "":
			MENSAJE = MENSAJE + "Info:   Instance " + ec2_name + " with no viable options. \n"
	else:
		MENSAJE = MENSAJE + "Info:   Nothing to do for Instance " + ec2_name + "\n"
		print("No se modificó Instancia {} - {}.".format(ec2_id, ec2_name))

	return cambio

def lambda_handler(event, context):
	total = 0
	cambios = 0
	global MENSAJE

	#if TYPE == "Both":
	#	R_TYPE = ['Underprovisioned','Overprovisioned']
	#else:
	#	R_TYPE = [TYPE]
	R_TYPE = ['Underprovisioned','Overprovisioned']

	MENSAJE = ""
	co_recos = co_client.get_ec2_instance_recommendations(filters=[{'name':'Finding','values':R_TYPE}])
	for instance in co_recos['instanceRecommendations']:
		total+=1
		cambios = cambios + review_compute_optimizer_recos(instance)

	while 'nextToken' in co_recos: #Pagineo
		co_recos = co_client.get_ec2_instance_recommendations(
			nextToken=co_recos['nextToken'],
			filters=[{'name':'Finding','values':R_TYPE}]
		)
		for instance in co_recos['instanceRecommendations']:
			total+=1
			cambios = cambios + review_compute_optimizer_recos(instance)

	the_message = "EC2 Instances updated "+str(cambios)+" of "+str(total)+" total recommendations:\n"
	print("Se realizaron {} cambios con éxito de un total de {} sugeridos.".format(cambios,total))
	print("Limite indicador de Riesgo: {}".format(risk_text[RISK]))
	try:
		if CORREO != "not@notify.me":
			the_topic = sns.Topic(TOPIC)
			the_message = the_message + MENSAJE
			the_message = the_message + "\nDefined risk threshold to change instance type: " + risk_text[RISK] + "." + "\nMore information on Lambda log."
			response = the_topic.publish(Subject="AutoComputeOptimizer Notification", Message=the_message)
	except:
		print(response)
		print("Fallo al enviar mensaje por SNS.")
	return {
		'statusCode': 200,
		'body': json.dumps(
			'Lambda finalizada exitosamente.'
		)
	}