"""
    Sportbet API console client.
    
    At start, goes automatically to API entry-point /api/.
    
    Then shows to the user the resources (actions, URLs) which
    API returned. User selects the next resource, and gives 
    schema-required parameters. New request is then sent to API.
    
    This is continued until the user stops the program 
    (via KeyboardInterrupt).
"""

import requests
import json
import sys
import os

# Constant definitions
JSON = "application/json"
MASON = "application/vnd.mason+json"
# update to your actual server
SERVER_NAME = "http://127.0.0.1:5000"
API_ENTRY_URL = SERVER_NAME + "/api/"
SPORTBET_API_KEY_NAME = "Sportbet-API-Key"
# update if API-server admin changes this
SPORTBET_API_KEY_VALUE = "xPMNOg98xOd8PmSGuRo9ygExpOOaebyDnLuRNCBxssQ"

# Development time debug print - comment return to enable debug
def debug_print(stuff):
    return
    print(stuff)
    
# Exit with error message
def error_exit(stuff):
    print(stuff + "\n")
    sys.exit(0)
    
# Obtain API-key for the API - simple skeleton only
def get_API_key():
    return SPORTBET_API_KEY_VALUE
    
# Prompt user for selection from the available controls
# Return the next target action (href, method, data)    
def select_control_by_user(controls):

    tmp_ctrls = []
    print("\nSELECT ACTION NUMBER")
    
    # Gather all possible controls (link-relations)
    idx = 1
    for ctrl in controls:
        title = "no-title"
        if "title" in controls[ctrl]:
            title = controls[ctrl]["title"]
        # print(str(idx) + " = " + title + " --> " + ctrl + ": " + controls[ctrl]["href"])
        print(str(idx) + " = " + title + " --> " + controls[ctrl]["href"])
        tmp_ctrls.append(controls[ctrl])
        idx += 1
    
    # Get user selection
    nbr = -1
    user_input = ""
    while nbr < 1 or nbr > (idx-1):
        user_input = input("Choose number (CTRL+C = exit): ")
        if user_input == "":
            continue
        try:
            nbr = int(user_input)
        except ValueError:
            continue
    print("")
    ctrl = tmp_ctrls[nbr-1]
    
    # Get all required schema-attributes from the user
    data = {}
    if "schema" in ctrl:
        for item in ctrl["schema"]["required"]:
            value = ""
            while value == "":
                value = input(ctrl["schema"]["properties"][item]["description"] + ": ")
                if value == "":
                    print("Empty input not allowed")
            try:
                if ctrl["schema"]["properties"][item]["type"] == "integer":
                   value = int(value)
                elif ctrl["schema"]["properties"][item]["type"] == "number":
                   value = float(value)
            except ValueError:
                print("Invalid value " + str(value) + " given\n")
                return {}
            data[item] = value
        print("")
        debug_print("SCHEMA INPUT")
        debug_print(data)
    
    # Get required method for the control
    method = "GET"
    if "method" in ctrl:
        method = ctrl["method"]
    
    # Return next API action to be taken
    return {
        "href": SERVER_NAME + ctrl["href"], 
        "method": method, 
        "data":data
    }    

# Handle API server response - redirect, text/html, MASON
# Return the next action to be taken (if none, previous action is repeated)
def handle_response(resp):

    debug_print("RESPONSE HEADERS")
    debug_print(resp.headers)
    
    # Handle redirect from server
    if "Location" in resp.headers:
        action = {"method": "GET", "href": SERVER_NAME + resp.headers["Location"], "data":[]}
        
    # Handle different content types
    elif "Content-type" in resp.headers:
    
        # E.g profile files
        if "text/" in resp.headers["Content-type"]:
            content = str(resp.content)
            import re
            re.sub('<[^<]+?>', '', content)
            print("CONTENT-TYPE = " + 
                  resp.headers["Content-type"] + "\n\n" + 
                  content.replace("\\n", "\n") + "\n")
            return {}
            
        # MASON responses
        elif resp.headers["Content-type"] == MASON:
            body = resp.json()
            debug_print("RESPONSE BODY")
            debug_print(body)
            # Print collection items' data
            if "items" in body:
                print("COLLECTION ITEMS\n")
                idx=0
                for item in body["items"]:
                    item_info = ""
                    idx += 1
                    for key in item:
                        if key != "@controls":
                            item_info += key + ": " + str(item[key]) + "\n"
                        else:
                            for item_ctrl in item["@controls"]:
                                if item_ctrl != "profile":
                                    item_ctrl_id = item_ctrl
                                    if item_ctrl == "self":
                                        item_ctrl_id = item_ctrl + str(idx)
                                    body["@controls"]["sportbet:" + item_ctrl_id] = item["@controls"][item_ctrl]
                    print(item_info)
            # Print item (body) data
            else:
                print("ITEM DATA\n")
                item_info = ""
                for key in body:
                    if key != "@namespaces" and key != "@controls" and key != "profile":
                        item_info += key + ": " + str(body[key]) + "\n"
                print(item_info)
            if "@error" in body:
                print("\nERROR RESPONSE, code = " + str(resp.status_code))
                print(body["@error"]["@message"] + "\n")
                return {}
            if "@controls" in body:
                # Add all item 'self' controls to body controls for user selection
                # Not required now
                """if "items" in body:
                    for item in body["items"]:
                        if "@controls" in item:
                            if "self" in item["@controls"]:
                                body["@controls"]["sportbet:" + item["@controls"]["self"]["title"]] = item["@controls"]["self"]"""
                action = select_control_by_user(body["@controls"])
            else:
                print("No controls in MASON response")
                print(resp)
                return {}
                
        # JSON responses (errors mainly)
        elif resp.headers["Content-type"] == JSON:
            print("Unexpected JSON response: " + str(resp.status_code))
            print(resp.reason)
            print("")
            sys.exit(0)
        
        # This should not happen
        else:
            error_exit("Unknown content-type " + resp.headers["Content-type"])
    
    # No redirect or valid content found in response (should never happen)
    else:
        error_exit("No 'Location' or 'Content-type' in response")
    
    debug_print("\nNext action:")
    debug_print(action)
    debug_print("\n")
    return action
    
def main():

    # Start from API entry point
    with requests.Session() as s:
        href = API_ENTRY_URL
        print("\nENTRY " + href + "\n")
        response = s.get(href)
    
    # Handle API responses until user (keyboard) interrupts program
    while True:
    
        # Get next action (href, method, data) from the server response
        action = handle_response(response)
        
        # Handle previous response when no actions available in response
        if "method" not in action:
            response = prev_response
            continue
        prev_response = response
        
        # Perform the next action (call API)
        with requests.Session() as s:
            s.headers.update({SPORTBET_API_KEY_NAME: get_API_key()})
            if action["method"] == "GET":
                response = s.get(action["href"])
            elif action["method"] == "POST":
                s.headers.update({"Content-type": JSON})
                response = s.post(action["href"], json=action["data"])
            elif action["method"] == "PUT":
                s.headers.update({"Content-type": JSON})
                response = s.put(action["href"], json=action["data"])
            elif action["method"] == "DELETE":
                response = s.delete(action["href"])
            else:
                error_exit("Undefined method " + action["method"])

# Handle user actions until program terminate            
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
