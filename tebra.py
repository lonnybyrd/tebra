import pandas as pd
from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os
import time
import json
import re
import json
import ast


load_dotenv()

username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
customer_key = os.getenv("CUSTOMER_KEY")
practice_name = "Neighborhood Urgent Care"

# Replace with your credentials and WSDL URL
wsdl = 'https://webservice.kareo.com/services/soap/2.1/KareoServices.svc?singleWsdl'
session = Session()
session.verify = True
transport = Transport(session=session)
settings = Settings(strict=False, xml_huge_tree=True)
client = Client(wsdl=wsdl, transport=transport, settings=settings)

# Optional: Configure session for authentication
session = Session()
session.auth = HTTPBasicAuth(username, password)

# Set up the transport and client
transport = Transport(session=session)
client = Client(wsdl=wsdl, transport=transport)

# Define the request payload
request_header = {
    "User": username,
    "Password": password,
    "CustomerKey": customer_key,
}
request_payload = {
    "RequestHeader": request_header,
    # Add other fields as needed
    "Filter": {"FromLastModifiedDate": "2025-02-14"}, # not used
    # "Fields": {"PatientFullName": True}
}

#print(client.service.UpdatePatient.__signature__)

def Appointments():
# Make the SOAP call
	try:
	    response = client.service.GetAppointments(request=request_payload)
	
	    # Print the raw response
	    print("Response:")
	    print(response)
	except Exception as e:
	    print("Error:", e)
		
def Charges():
# Make the SOAP call
	request_payload = {
	    "RequestHeader": request_header,
	    # Add other fields as needed
	    "Filter": {"FromLastModifiedDate": "2025-02-16", "IncludeUnapprovedCharges": True },
#	    "Fields": {"PatientFullName": True}
#		"PracticeName": practice_name,
#		"Fields": {
#			"EncounterID": "27",
#			"PracticeName": practice_name
#		}
	}
	try:
		response = client.service.GetCharges(request=request_payload)
	
	    # Print the raw response
#	    print("Response:")
#	    print(response)
		return response
	except Exception as e:
	    print("Error:", e)
		
def hl7():
	# Load JSON data
	input_file = "tebra_response_fixed.json"
	output_file = "tebra_output.hl7"
		
	with open(input_file, "r", encoding="utf-8") as file:
	    data = json.load(file)
	
	hl7_messages = []
	
	for charge in data.get("Charges", {}).get("ChargeData", []):
		hl7_message = []
		
		# MSH - Message Header
		# old
		#    hl7_message.append(f"MSH|^~\&|NeighborhoodUC|VelocityMedical||Tebra|{charge['PostingDate'].replace('/', '')}||DFT^P03|123456|P|2.3")
		#new
		hl7_message.append(f"MSH|^~\\&|NeighborhoodUC|VelocityMedical||Tebra|{charge['PostingDate'].replace('/', '')}||DFT^P03|123456|P|2.3")
		
		# EVN - Event Type
		hl7_message.append(f"EVN|P03|{charge['PostingDate'].replace('/', '')}")
		
		# PID - Patient Identification
		patient_name = f"{charge['PatientLastName']}^{charge['PatientFirstName']}"
		hl7_message.append(f"PID|||{charge['PatientID']}||{patient_name}||{charge['PatientDateOfBirth'].replace('/', '')}|M|||{charge['ServiceLocationNameAddressLine1']}^^{charge['ServiceLocationNameCity']}^{charge['ServiceLocationNameState']}^{charge['ServiceLocationNameZipCode']}^USA")
		
		# PV1 - Patient Visit
		provider_name = charge['RenderingProviderName'].strip()
		hl7_message.append(f"PV1||O|NeighborhoodUC||||{provider_name}||||||||||{charge['CasePayerScenario']}||||||||||||||||||{charge['ServiceStartDate'].replace('/', '')}")
		
		# FT1 - Financial Transaction
		hl7_message.append(f"FT1|1|{charge['EncounterID']}|{charge['PostingDate'].replace('/', '')}||{charge['ProcedureCode']}|{charge['ProcedureName']}|{charge['TotalCharges']}|{charge['Units']}||||||||||||||")
		
		# IN1 - Insurance Information (if available)
		if charge['PrimaryInsuranceCompanyName']:
		    hl7_message.append(f"IN1|1|{charge['PrimaryInsuranceCompanyName']}|{charge['PrimaryInsuranceCompanyName']}|{charge['PrimaryInsuranceAddressLine1']}^^{charge['PrimaryInsuranceCity']}^{charge['PrimaryInsuranceState']}^{charge['PrimaryInsuranceZipCode']}|USA|||||||{charge['PrimaryInsuranceZipCode']}")
		
		# DG1 - Diagnosis Information
		if charge['EncounterDiagnosisID1']:
		    hl7_message.append(f"DG1|1||{charge['EncounterDiagnosisID1']}||Diagnosis code available")
		
		hl7_messages.append("\n".join(hl7_message))

	# Save HL7 file
	with open(output_file, "w", encoding="utf-8") as file:
		file.write("\n\n".join(hl7_messages))
	
		print(f"HL7 file saved as {output_file}")
			
content = Charges()
output_file = "tebra_response.json"
with open(output_file, "w", encoding="utf-8") as file:
	file.write(str(content))
file.close()

input_file = "tebra_response.json"
output_file = "tebra_response_fixed.json"

with open(input_file, "r", encoding="utf-8") as file:
    content = file.read()

try:
    # Convert invalid JSON (single quotes, None) to a Python dictionary
    data_dict = ast.literal_eval(content)  # Safe evaluation

    # Convert the dictionary back to properly formatted JSON
    fixed_json = json.dumps(data_dict, indent=4)  # Ensures double quotes and null values

    # Save the corrected JSON file
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(fixed_json)

#    print(f"Fixed JSON saved as {output_file}")

except Exception as e:
    print(f"Error while fixing JSON: {e}")

	
hl7()

