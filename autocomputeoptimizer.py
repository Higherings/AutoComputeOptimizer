# igarcia 2020-02
# Version 0.7
# Automation for Compute Optimizer Recommendations
# It will change the EC2 Instance Type to a Recommendation of the AWS Compute Optimizer Service and send an email about it
# It won't do anything to AutoScaling Group's Instances
# You can set a TAG Value for the instances that this Lambda can manage
# IMPORTANT: your EC2 instance should endure a restart!

import os
import json
import boto3

RISK = os.environ['RISK'] #de 0 a 5, 0 es sin riesgo y 5 es mucho riesgo (No Risk, Very Low, Low, Medium, High, Very High)
TYPE = os.environ['TYPE'] # Overprovisioned, Underprovisioned or Both
TAGBUSQUEDA = os.environ['TAGBUSQUEDA']
TAGVALOR = os.environ['TAGVALOR']
TOPIC = os.environ['TOPIC']

ec2 = boto3.resource('ec2')
co_client = boto3.client('compute-optimizer')
sns = boto3.resource('sns')

def review_compute_optimizer_recos(instance):
	cambio = 0
	response = ""
	ec2_id = instance['instanceArn'].split('/')[1] #Instance ID
	ec2_name = instance['instanceName']
	to_do = False # Flag to determine if Instance will be examined

	ec2_instance = ec2.Instance(ec2_id)
	ec2_prev_type = ec2_instance.instance_type
	ec2_tags = ec2_instance.tags
	for tag in ec2_tags:
		if tag['Key'] == TAGBUSQUEDA and tag['Value'] == TAGVALOR:
			to_do = True
	
	if to_do:
		for option in instance['recommendationOptions']:
			ec2_new_type = option['instanceType']
			if (option['rank'] == 1) and (int(option['performanceRisk']) <= int(RISK)) and (ec2_prev_type != ec2_new_type): # Debe ser la 1ra opcion, el riesgo debe ser aceptable y el tipo de Instancia debe cambiar
				    #Hacer Cambio Tipo de Instancia
					if ec2_instance.state['Name'] == 'stopped':
						try:
							response = ec2_instance.modify_attribute(InstanceType={'Value':ec2_new_type})
							response = ec2_instance.start()
							response = ec2_instance.wait_until_running()
							cambio = 1
							print("Se modificó Instancia {} - {} de {} a tipo {} ".format(ec2_id, ec2_name, ec2_prev_type, ec2_new_type))
						except:
							ec2_instance.stop()
							ec2_instance.wait_until_stopped()
							ec2_instance.modify_attribute(InstanceType={'Value':ec2_prev_type})
							ec2_instance.start()
							cambio = 0
							print(response)
							print("No se puedo modificar Instancia {} - {} a tipo {} ".format(ec2_id, ec2_name, ec2_new_type))
					elif ec2_instance.state['Name'] == 'running':
						try:
							response = ec2_instance.stop()
							response = ec2_instance.wait_until_stopped()
							response = ec2_instance.modify_attribute(InstanceType={'Value':ec2_new_type})
							response = ec2_instance.start()
							response = ec2_instance.wait_until_running()
							cambio = 1
							print("Se modificó Instancia {} - {} de {} a tipo {} ".format(ec2_id, ec2_name, ec2_prev_type, ec2_new_type))
						except:
							ec2_instance.stop()
							ec2_instance.wait_until_stopped()
							ec2_instance.modify_attribute(InstanceType={'Value':ec2_prev_type})
							ec2_instance.start()
							cambio = 0
							print(response)
							print("No se puedo modificar Instancia {} - {} a tipo {} ".format(ec2_id, ec2_name, ec2_new_type))
					break #Salgo del ciclo de OPCIONES
	else:
		print("No se modificó Instancia {} - {} debido a que no tiene el TAG necesario.".format(ec2_id, ec2_name))

	return cambio

def lambda_handler(event, context):
	total = 0
	cambios = 0

	if TYPE == "Both":
		R_TYPE = ['Underprovisioned','Overprovisioned']
	else:
		R_TYPE = [TYPE]

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

	the_topic = sns.Topic(TOPIC)
	the_message = "Se realizaron "+cambios+" cambios con éxito de un total de "+total+" sugeridos.\nRevise el log de la Lambda para conocer las instancias afectadas."
	print("Se realizaron {} cambios con éxito de un total de {} sugeridos.".format(cambios,total))
	try:
		response = the_topic.publish(Subject="AutoComputeOptimizer Notification", Message=the_message)
	except:
		print("Fallo al enviar mensaje por SNS.")
	return {
		'statusCode': 200,
		'body': json.dumps(
			'Lambda finalizada exitosamente.'
		)
	}