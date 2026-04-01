import requests
from pprint import pprint

def test_comparison_via_rest_api():
  uids_fw = ['8bf0a97817b41cdf9b541692405067e25747128ae9cecb102b1fadedcca623b8_87296559', '5ee712f300ee10f0d03393b34dd8f44f3bf3669d4849d13ee92bfd47e5e795df_88085627'] #actual fw
  uids_test = ['57a12723727334077e0d6786357c529a5b8a185f3efe70877d584fc640da1097_1859', '59a9265181ab70ee42523b15cccc109a8d2d53cb45d5af0e99e7487582bf6dcb_1982'] #test fw
  send_comparison_request(uids_test)
  # send_comparison_request(uids_fw)

def send_comparison_request(uids_test):
    fact_ip = '127.0.0.1'
    fact_port = '5000'
    endpoint = 'rest/compare' 
    url = f'http://{fact_ip}:{fact_port}/{endpoint}'
    payload = {
    "redo": True,
    "uid_list": uids_test
  }
    print("Sending request to FACT REST API...")
    response = requests.put(url, json=payload)
    print(f'Status code: {response.status_code}')
    pprint("Response from FACT REST API:")
    pprint(response.json())
  
if __name__ == '__main__':
  test_comparison_via_rest_api()