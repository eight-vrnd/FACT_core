import argparse
import requests
from pprint import pprint


def send_comparison_request(uid_list):
  fact_ip = '127.0.0.1'
  fact_port = '5000'
  endpoint = 'rest/compare'
  url = f'http://{fact_ip}:{fact_port}/{endpoint}'
  payload = {
    "redo": True,
    "uid_list": uid_list
  }
  print("Sending request to FACT REST API...")
  response = requests.put(url, json=payload)
  print(f'Status code: {response.status_code}')
  pprint("Response from FACT REST API:")
  try:
    pprint(response.json())
  except ValueError:
    print(response.text)

def main():
  
  firmware_image_uids = {
    'GL-iNet GL-BE3600 Slate 7 v. 4.8.1': '5ee712f300ee10f0d03393b34dd8f44f3bf3669d4849d13ee92bfd47e5e795df_88085627',
    'GL-iNet GL-BE3600 Slate 7 v. 4.7.3': '8bf0a97817b41cdf9b541692405067e25747128ae9cecb102b1fadedcca623b8_87296559',
    'GL-iNet GL-BE3600 Slate 7 v. 4.8.3': '90b34ad1c74b666c545b75b372b35429cf594e5b270eee5cfdecd3e865177d8f_97260680',
    'AVM FRITZ.Box 7360 v. 06.36': '16f6e136a32db51c1e20f66813d4b119de51de3174a06ee0c17de8f07d576af3_16619520',
    'AVM FRITZ.Box 7360 v. 06.88': 'c680fb3cfc55559a57ad0aab35602766dd3de6eead1b3a796563398e129bda7e_20613120',
    'Test Test 2 - 1 (Test)': '57a12723727334077e0d6786357c529a5b8a185f3efe70877d584fc640da1097_1859',
    'Test Test 2 - 2 (Test)': '59a9265181ab70ee42523b15cccc109a8d2d53cb45d5af0e99e7487582bf6dcb_1982',
    
  }
  
  comparison_pairs = [
    ('GL-iNet GL-BE3600 Slate 7 v. 4.8.1', 'GL-iNet GL-BE3600 Slate 7 v. 4.7.3'),
    ('GL-iNet GL-BE3600 Slate 7 v. 4.8.1', 'GL-iNet GL-BE3600 Slate 7 v. 4.8.3'),
    ('AVM FRITZ.Box 7360 v. 06.36', 'AVM FRITZ.Box 7360 v. 06.88')
  ]
  
  test_pairs = [
    ('Test Test 2 - 1 (Test)', 'Test Test 2 - 2 (Test)')
  ]

  parser = argparse.ArgumentParser(description='Send comparison requests to FACT REST API')
  parser.add_argument('--test', action='store_true', help='Test firmware comparison')
  # allow one argument for each comparison pair, e.g. --compare1, --compare2, etc.
  for i, _ in enumerate(comparison_pairs, start=1):
    parser.add_argument(f'--compare{i}', action='store_true', help=f'Compare {comparison_pairs[i-1][0]} vs {comparison_pairs[i-1][1]}')
  
  args = parser.parse_args()
  if args.test:
    uid_list = [firmware_image_uids[fw] for fw in test_pairs[0]]
    send_comparison_request(uid_list)
  elif args.compare1:
    uid_list = [firmware_image_uids[fw] for fw in comparison_pairs[0]]
    send_comparison_request(uid_list)
  elif args.compare2:
    uid_list = [firmware_image_uids[fw] for fw in comparison_pairs[1]]
    send_comparison_request(uid_list)
  elif args.compare3:
    uid_list = [firmware_image_uids[fw] for fw in comparison_pairs[2]]
    send_comparison_request(uid_list)
  else:
    print("No comparison specified. Use --test or --compare1, --compare2, etc. to specify comparisons.")


if __name__ == '__main__':
  main()